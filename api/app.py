import tornado.web
import tornado.ioloop
import tornado.httpserver

from controller.auth import *
from controller.auth.github import *
from controller.aws import *
from controller.billing import *
from controller.deployments import *
from controller.github.controllers import GithubUserRepos
from controller.github.controllers_github_proxy import GithubProxy
from controller.health import *
from controller.internal import *
from controller.lambdas import *
from controller.logs import *
from controller.projects import *
from controller.projects.controllers_short_links import GetProjectShortlink, CreateProjectShortlink
from controller.saved_blocks import *
from controller.services import *
from controller.websockets import *

from controller.websockets import LambdaConnectBackServer
from utils.ip_lookup import get_external_ipv4_address
from utils.ngrok import NgrokSpawner, set_up_ngrok_websocket_tunnel


class TornadoApp:
    tornado_config = None

    @pinject.copy_args_to_public_fields
    def __init__(self, logger, app_config, tornado_config, lambda_callback_endpoint):
        # Resolve what our callback endpoint is, this is different in DEV vs PROD
        # one assumes you have an external IP address and the other does not (and
        # fixes the situation for you with ngrok).
        # TODO verify that is this ok? seems a little sketchy to modify a dependency
        app_config._config["LAMBDA_CALLBACK_ENDPOINT"] = lambda_callback_endpoint

        # Initialize Stripe
        stripe.api_key = app_config.get("stripe_api_key")

        # This is purely for sending emails as part of Refinery's
        # regular operations (e.g. authentication via email code, etc).
        # This is Mailgun because SES is a huge PITA and is dragging their
        # feet on verifying.
        mailgun_api_key = app_config.get("mailgun_api_key")

        if mailgun_api_key is None:
            print("Please configure a Mailgun API key, this is needed for authentication and regular operations.")
            exit()

        logger("Lambda callback endpoint is " + app_config.get("LAMBDA_CALLBACK_ENDPOINT"))
        logger("Workflow manager is " + app_config.get("workflow_manager_api_url"))

    def new_server(self, object_graph):
        return tornado.httpserver.HTTPServer(
            self.make_app(object_graph)
        )

    @staticmethod
    def inject_object_graph(handlers, object_graph):
        inject_handlers = []
        object_graph_dep = dict(object_graph=object_graph)
        for handler in handlers:
            if len(handler) == 3:
                inject_handlers.append( (handler[0], handler[1], object_graph_dep, handler[2]) )
            else:
                inject_handlers.append( handler + (object_graph_dep,) )
        return inject_handlers

    def make_app(self, object_graph):
        handlers = [
            (r"/api/v1/health", HealthHandler),

            (r"/authentication/email/([a-z0-9]+)", EmailLinkAuthentication),
            (r"/api/v1/auth/me", GetAuthenticationStatus),
            (r"/api/v1/auth/register", NewRegistration),
            (r"/api/v1/auth/login", Authenticate),
            (r"/api/v1/auth/logout", Logout),
            ( r"/api/v1/auth/github", AuthenticateWithGithub, "auth_github" ),

            (r"/api/v1/logs/executions/get-logs", GetProjectExecutionLogObjects),
            (r"/api/v1/logs/executions/get-contents", GetProjectExecutionLogsPage),
            (r"/api/v1/logs/executions/get", GetProjectExecutionLogs),
            (r"/api/v1/logs/executions", GetProjectExecutions),

            (r"/api/v1/saved_blocks/create", SavedBlocksCreate),
            (r"/api/v1/saved_blocks/search", SavedBlockSearch),
            (r"/api/v1/saved_blocks/status_check", SavedBlockStatusCheck),
            (r"/api/v1/saved_blocks/delete", SavedBlockDelete),

            (r"/api/v1/lambdas/run", RunLambda),
            (r"/api/v1/lambdas/logs", GetCloudWatchLogsForLambda),
            (r"/api/v1/lambdas/env_vars/update", UpdateEnvironmentVariables),
            (r"/api/v1/lambdas/build_libraries", BuildLibrariesPackage),
            (r"/api/v1/lambdas/libraries_cache_check", CheckIfLibrariesCached),

            (r"/api/v1/aws/run_tmp_lambda", RunTmpLambda),
            (r"/api/v1/aws/infra_tear_down", InfraTearDown),
            (r"/api/v1/aws/infra_collision_check", InfraCollisionCheck),
            (r"/api/v1/aws/deploy_diagram", DeployDiagram),

            ( r"/api/v1/github/proxy/(.*)", GithubProxy ),
            ( r"/api/v1/github/repos", GithubUserRepos ),

            (r"/api/v1/projects/config/save", SaveProjectConfig),
            (r"/api/v1/projects/save", SaveProject),
            (r"/api/v1/projects/search", SearchSavedProjects),
            (r"/api/v1/projects/get", GetSavedProject),
            (r"/api/v1/projects/versions", GetProjectVersions),
            (r"/api/v1/projects/delete", DeleteSavedProject),
            (r"/api/v1/projects/rename", RenameProject),
            (r"/api/v1/projects/config/get", GetProjectConfig),

            (r"/api/v1/deployments/secure_resolver", SecureResolverDeployment),
            (r"/api/v1/deployments/get_latest", GetLatestProjectDeployment),
            (r"/api/v1/deployments/delete_all_in_project", DeleteDeploymentsInProject),

            (r"/api/v1/billing/get_month_totals", GetBillingMonthTotals),
            (r"/api/v1/billing/creditcards/add", AddCreditCardToken),
            (r"/api/v1/billing/creditcards/list", ListCreditCards),
            (r"/api/v1/billing/creditcards/delete", DeleteCreditCard),
            (r"/api/v1/billing/creditcards/make_primary", MakeCreditCardPrimary),
            # Temporarily disabled since it doesn't cache the CostExplorer results
            #( r"/api/v1/billing/forecast_for_date_range", GetBillingDateRangeForecast ),

            (r"/api/v1/project_short_link/create", CreateProjectShortlink),
            (r"/api/v1/project_short_link/get", GetProjectShortlink),

            (r"/api/v1/iam/console_credentials", GetAWSConsoleCredentials),
            (r"/api/v1/internal/log", StashStateLog),

            # WebSocket endpoint for live debugging Lambdas
            (r"/ws/v1/lambdas/livedebug", ExecutionsControllerServer),

            # These are "services" which are only called by external crons, etc.
            # External users are blocked from ever reaching these routes
            (r"/services/v1/generate_deployment_auth_secret/([a-f0-9\-]+)", GenerateDeploymentAuthSecret),
            (r"/services/v1/assume_account_role/([a-f0-9\-]+)", AdministrativeAssumeAccount),
            (r"/services/v1/assume_role_credentials/([a-f0-9\-]+)", AssumeRoleCredentials),
            (r"/services/v1/maintain_aws_account_pool", MaintainAWSAccountReserves),
            (r"/services/v1/billing_watchdog", RunBillingWatchdogJob),
            (r"/services/v1/bill_customers", RunMonthlyStripeBillingJob),
            (r"/services/v1/perform_terraform_plan_on_fleet", PerformTerraformPlanOnFleet),
            (r"/services/v1/dangerously_terraform_update_fleet", PerformTerraformUpdateOnFleet),
            (r"/services/v1/perform_terraform_plan_for_account/([a-f0-9\-]+)", PerformTerraformPlanForAccount),
            (r"/services/v1/dangerously_terraform_update_for_account/([a-f0-9\-]+)", PerformTerraformUpdateForAccount),
            (r"/services/v1/update_managed_console_users_iam", UpdateIAMConsoleUserIAM),
            (r"/services/v1/reset_iam_console_user_for_account/([a-f0-9\-]+)", ResetIAMConsoleUserIAMForAccount),
            (r"/services/v1/onboard_third_party_aws_account_plan", OnboardThirdPartyAWSAccountPlan),
            (r"/services/v1/dangerously_finalize_third_party_aws_onboarding", OnboardThirdPartyAWSAccountApply),
            (r"/services/v1/clear_s3_build_packages", ClearAllS3BuildPackages),
            (r"/services/v1/dangling_resources/([a-f0-9\-]+)", CleanupDanglingResources),
            (r"/services/v1/clear_stripe_invoice_drafts", ClearStripeInvoiceDrafts),
            (r"/services/v1/mark_account_needs_closing", MarkAccountNeedsClosing),
            (r"/services/v1/remove_needs_closing_accounts", RemoveNeedsClosingAccounts),
        ]

        # Sets up routes
        return tornado.web.Application(
            TornadoApp.inject_object_graph(handlers, object_graph),
            **self.tornado_config)


class TornadoBindingSpec(pinject.BindingSpec):
    @pinject.provides("tornado_config")
    def provide_torando_config(self, app_config):
        # Generate tornado config
        return {
            "debug": app_config.get("debug"),
            "ngrok_enabled": app_config.get("ngrok_enabled"),
            "cookie_secret": app_config.get("cookie_secret_value"),
            "compress_response": True
        }

    @pinject.provides("lambda_callback_endpoint")
    def provide_lambda_callback_endpoint(self, logger, app_config, tornado_config):
        if tornado_config["ngrok_enabled"] == "true":
            logger("Setting up the ngrok tunnel to the local websocket server...")

            def do_set_up_ngrok_websocket_tunnel():
                ngrok_tasks = NgrokSpawner(app_config)
                return set_up_ngrok_websocket_tunnel(ngrok_tasks)

            ngrok_http_endpoint = tornado.ioloop.IOLoop.current().run_sync(
                do_set_up_ngrok_websocket_tunnel
            )

            return ngrok_http_endpoint.replace(
                "https://",
                "ws://"
            ).replace(
                "http://",
                "ws://"
            ) + "/ws/v1/lambdas/connectback"

        remote_ipv4_address = tornado.ioloop.IOLoop.current().run_sync(
            get_external_ipv4_address
        )
        return "ws://" + remote_ipv4_address + ":3333/ws/v1/lambdas/connectback"


class WebsocketApp:
    tornado_config = None

    @pinject.copy_args_to_public_fields
    def __init__(self, tornado_config):
        pass

    def new_server(self, object_graph):
        object_graph_dep = dict(object_graph=object_graph)
        app = tornado.web.Application([
            # WebSocket callback endpoint for live debugging Lambdas
            (r"/ws/v1/lambdas/connectback", LambdaConnectBackServer, object_graph_dep),
        ], **self.tornado_config)
        return tornado.httpserver.HTTPServer(
            app
        )
