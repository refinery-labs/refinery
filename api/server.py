#!/usr/bin/env python
# coding=utf8
# -*- coding: utf8 -*-
# vim: set fileencoding=utf8 :
import tornado.escape
import tornado.ioloop
import tornado.web
import functools
import datetime
import stripe
import sys

import unicodecsv as csv

from assistants.aws_account_management.preterraform import PreTerraformManager
from assistants.billing.billing_assistant import BillingSpawner
from assistants.deployments.api_gateway import APIGatewayManager
from assistants.deployments.awslambda import LambdaManager
from assistants.deployments.schedule_trigger import ScheduleTriggerManager
from assistants.deployments.sns import SNSManager
from assistants.deployments.sqs import SQSManager
from assistants.user_creation_assistant import UserCreationAssistant
from config.app_config import load_app_config

from controller.auth import *
from controller.auth.github import *
from controller.aws import *
from controller.billing import *
from controller.deployments import *
from controller.health import *
from controller.internal import *
from controller.lambdas import *
from controller.logs import *
from controller.projects import *
from controller.saved_blocks import *
from controller.services import *
from controller.websocket import *

from services.auth.oauth_service import OAuthService
from services.project_inventory.project_inventory_service import ProjectInventoryService
from services.stripe.stripe_service import StripeService
from services.user_management.user_management_service import UserManagementService
from services.aws.clients import new_aws_cost_explorer, new_aws_organization_client
from utils.dependency_injection import inject_handler_dependencies
from utils.general import logit
from utils.ngrok import set_up_ngrok_websocket_tunnel, NgrokSpawner
from utils.ip_lookup import get_external_ipv4_address
from assistants.deployments.ecs_builders import BuilderManager

from services.websocket_router import WebSocketRouter, run_scheduled_heartbeat

from models.initiate_database import *

try:
	# for Python 2.x
	from StringIO import StringIO
except ImportError:
	# for Python 3.x
	from io import StringIO

import zipfile

# noinspection PyBroadException
try:
	# for Python 2.x
	# noinspection PyCompatibility
	reload( sys )
except Exception:
	# for Python 3.4+
	# noinspection PyUnresolvedReferences
	from importlib import reload
	reload( sys )

sys.setdefaultencoding( "utf8" )

# Increase CSV field size to be the max
csv.field_size_limit( sys.maxsize )


def get_tornado_app_config( app_config ):
	return {
		"debug": app_config.get( "debug" ),
		"ngrok_enabled": app_config.get( "ngrok_enabled" ),
		"cookie_secret": app_config.get( "cookie_secret_value" ),
		"compress_response": True,
		"websocket_router": WebSocketRouter()
	}


def make_websocket_server( tornado_config ):
	return tornado.web.Application([
		# WebSocket callback endpoint for live debugging Lambdas
		( r"/ws/v1/lambdas/connectback", LambdaConnectBackServer, {
			"websocket_router": tornado_config[ "websocket_router" ]
		}),
	], **tornado_config)


def make_app( app_config, tornado_config, mocked_deps=dict() ):
	def should_mock(name, dep):
		return dep if not mocked_deps.get(name) else mocked_deps.get(name)

	# TODO figure out a better way to mock dependencies than this
	engine = get_refinery_engine( app_config )
	db_session_maker = should_mock("db_session_maker", create_scoped_db_session_maker(engine))

	# AWS Clients
	aws_cost_explorer = new_aws_cost_explorer( app_config )
	aws_organization_client = new_aws_organization_client( app_config )
	api_gateway_manager = APIGatewayManager()
	lambda_manager = LambdaManager()
	schedule_trigger_manager = ScheduleTriggerManager()
	sns_manager = SNSManager()
	sqs_manager = SQSManager()
	builder_manager = BuilderManager()

	preterraform_manager = PreTerraformManager()

	# Sets up dependencies
	logger = logit
	local_tasks = TaskSpawner(
		app_config,
		db_session_maker,
		aws_cost_explorer,
		aws_organization_client,
		api_gateway_manager,
		lambda_manager,
		schedule_trigger_manager,
		sns_manager,
		preterraform_manager
	)

	# Standalone dependencies that just rely on configuration
	github_oauth_provider = GithubOAuthProvider(
		app_config.get( "github_client_id" ),
		app_config.get( "github_client_secret" ),
		app_config.get( "cookie_expire_days" ),
		logger
	)

	# Service Instantiation:
	# Services only take in a logger instance or configuration.
	# They do not depend on each other.
	oauth_service = OAuthService( logger )
	user_service = UserManagementService( logger )
	project_inventory_service = ProjectInventoryService( logger )
	stripe_service = StripeService( local_tasks.executor, logger )

	# Assistant Instantiation:
	# Assistants rely on Services and are basically business logic + glue code between them.
	# These exist to keep logic outside of HTTP Controllers (and DRY).
	user_creation_assistant = UserCreationAssistant(
		logger,
		oauth_service,
		github_oauth_provider,
		project_inventory_service,
		stripe_service,
		user_service
	)

	github_auth_deps = dict(
		github_oauth_provider=github_oauth_provider,
		project_inventory_service=project_inventory_service,
		stripe_service=stripe_service,
		oauth_service=oauth_service,
		user_creation_assistant=user_creation_assistant,
		user_service=user_service
	)

	executions_controller_deps = dict(
		websocket_router=tornado_config[ "websocket_router" ]
	)

	billing_spawner = BillingSpawner(app_config=app_config)
	clear_stripe_invoice_drafts_deps = dict(
		billing_spawner=billing_spawner
	)

	deploy_diagram_deps = dict(
		lambda_manager=lambda_manager,
		api_gateway_manager=api_gateway_manager,
		schedule_trigger_manager=schedule_trigger_manager,
		sns_manager=sns_manager
	)

	cleanup_dangling_resources_deps = dict(
		api_gateway_manager=api_gateway_manager,
		lambda_manager=lambda_manager,
		schedule_trigger_manager=schedule_trigger_manager,
		sns_manager=sns_manager,
		sqs_manager=sqs_manager
	)

	infra_tear_down_deps = dict(
		api_gateway_manager=api_gateway_manager,
		lambda_manager=lambda_manager,
		schedule_trigger_manager=schedule_trigger_manager,
		sns_manager=sns_manager,
		sqs_manager=sqs_manager
	)

	delete_saved_project_deps = dict(
		lambda_manager=lambda_manager,
		api_gateway_manager=api_gateway_manager,
		schedule_trigger_manager=schedule_trigger_manager,
		sns_manager=sns_manager,
		sqs_manager=sqs_manager
	)

	run_tmp_lambda_deps = dict(
		builder_manager=builder_manager
	)

	# Must have this because if Tornado tries to inject a dependency that the class doesn't ask for, it throws.
	common_dependencies = dict(
		app_config=app_config,
		logger=logger,
		db_session_maker=db_session_maker,
		local_tasks=local_tasks
	)

	handlers = [
		( r"/api/v1/health", HealthHandler ),

		( r"/authentication/email/([a-z0-9]+)", EmailLinkAuthentication ),
		( r"/api/v1/auth/me", GetAuthenticationStatus ),
		( r"/api/v1/auth/register", NewRegistration ),
		( r"/api/v1/auth/login", Authenticate ),
		( r"/api/v1/auth/github", AuthenticateWithGithub, github_auth_deps ),
		( r"/api/v1/auth/logout", Logout ),

		( r"/api/v1/logs/executions/get-logs", GetProjectExecutionLogObjects ),
		( r"/api/v1/logs/executions/get-contents", GetProjectExecutionLogsPage ),
		( r"/api/v1/logs/executions/get", GetProjectExecutionLogs ),
		( r"/api/v1/logs/executions", GetProjectExecutions ),

		( r"/api/v1/saved_blocks/create", SavedBlocksCreate ),
		( r"/api/v1/saved_blocks/search", SavedBlockSearch ),
		( r"/api/v1/saved_blocks/status_check", SavedBlockStatusCheck ),
		( r"/api/v1/saved_blocks/delete", SavedBlockDelete ),

		( r"/api/v1/lambdas/run", RunLambda ),
		( r"/api/v1/lambdas/logs", GetCloudWatchLogsForLambda ),
		( r"/api/v1/lambdas/env_vars/update", UpdateEnvironmentVariables ),
		( r"/api/v1/lambdas/build_libraries", BuildLibrariesPackage ),
		( r"/api/v1/lambdas/libraries_cache_check", CheckIfLibrariesCached ),

		( r"/api/v1/aws/run_tmp_lambda", RunTmpLambda, run_tmp_lambda_deps ),
		( r"/api/v1/aws/infra_tear_down", InfraTearDown, infra_tear_down_deps ),
		( r"/api/v1/aws/infra_collision_check", InfraCollisionCheck ),
		( r"/api/v1/aws/deploy_diagram", DeployDiagram, deploy_diagram_deps ),

		( r"/api/v1/projects/config/save", SaveProjectConfig ),
		( r"/api/v1/projects/save", SaveProject ),
		( r"/api/v1/projects/search", SearchSavedProjects ),
		( r"/api/v1/projects/get", GetSavedProject ),
		( r"/api/v1/projects/delete", DeleteSavedProject, delete_saved_project_deps ),
		( r"/api/v1/projects/rename", RenameProject ),
		( r"/api/v1/projects/config/get", GetProjectConfig ),

		( r"/api/v1/deployments/get_latest", GetLatestProjectDeployment ),
		( r"/api/v1/deployments/delete_all_in_project", DeleteDeploymentsInProject ),

		( r"/api/v1/billing/get_month_totals", GetBillingMonthTotals ),
		( r"/api/v1/billing/creditcards/add", AddCreditCardToken ),
		( r"/api/v1/billing/creditcards/list", ListCreditCards ),
		( r"/api/v1/billing/creditcards/delete", DeleteCreditCard ),
		( r"/api/v1/billing/creditcards/make_primary", MakeCreditCardPrimary ),
		# Temporarily disabled since it doesn't cache the CostExplorer results
		#( r"/api/v1/billing/forecast_for_date_range", GetBillingDateRangeForecast ),

		( r"/api/v1/project_short_link/create", CreateProjectShortlink ),
		( r"/api/v1/project_short_link/get", GetProjectShortlink ),

		( r"/api/v1/iam/console_credentials", GetAWSConsoleCredentials ),
		( r"/api/v1/internal/log", StashStateLog ),

		# WebSocket endpoint for live debugging Lambdas
		( r"/ws/v1/lambdas/livedebug", ExecutionsControllerServer, executions_controller_deps),

		# These are "services" which are only called by external crons, etc.
		# External users are blocked from ever reaching these routes
		( r"/services/v1/assume_account_role/([a-f0-9\-]+)", AdministrativeAssumeAccount ),
		( r"/services/v1/maintain_aws_account_pool", MaintainAWSAccountReserves ),
		( r"/services/v1/billing_watchdog", RunBillingWatchdogJob ),
		( r"/services/v1/bill_customers", RunMonthlyStripeBillingJob ),
		( r"/services/v1/perform_terraform_plan_on_fleet", PerformTerraformPlanOnFleet ),
		( r"/services/v1/dangerously_terraform_update_fleet", PerformTerraformUpdateOnFleet ),
		( r"/services/v1/update_managed_console_users_iam", UpdateIAMConsoleUserIAM ),
		( r"/services/v1/onboard_third_party_aws_account_plan", OnboardThirdPartyAWSAccountPlan ),
		( r"/services/v1/dangerously_finalize_third_party_aws_onboarding", OnboardThirdPartyAWSAccountApply ),
		( r"/services/v1/clear_s3_build_packages", ClearAllS3BuildPackages ),
		( r"/services/v1/dangling_resources/([a-f0-9\-]+)", CleanupDanglingResources, cleanup_dangling_resources_deps ),
		( r"/services/v1/clear_stripe_invoice_drafts", ClearStripeInvoiceDrafts, clear_stripe_invoice_drafts_deps ),
	]

	# Sets up routes
	return tornado.web.Application(
		inject_handler_dependencies(common_dependencies, handlers),
		**tornado_config)


def get_lambda_callback_endpoint( app_config, tornado_config ):
	if tornado_config[ "ngrok_enabled" ] == "true":
		logit( "Setting up the ngrok tunnel to the local websocket server..." )

		def do_set_up_ngrok_websocket_tunnel():
			ngrok_tasks = NgrokSpawner( app_config )
			return set_up_ngrok_websocket_tunnel( ngrok_tasks )

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


if __name__ == "__main__":
	logit( "Starting the Refinery service...", "info" )

	app_config = load_app_config()

	# Initialize Stripe
	stripe.api_key = app_config.get( "stripe_api_key" )

	# This is purely for sending emails as part of Refinery's
	# regular operations (e.g. authentication via email code, etc).
	# This is Mailgun because SES is a huge PITA and is dragging their
	# feet on verifying.
	mailgun_api_key = app_config.get( "mailgun_api_key" )

	if mailgun_api_key is None:
		print( "Please configure a Mailgun API key, this is needed for authentication and regular operations." )
		exit()

	# Generate tornado config
	tornado_config = get_tornado_app_config(
		app_config
	)

	# Resolve what our callback endpoint is, this is different in DEV vs PROD
	# one assumes you have an external IP address and the other does not (and
	# fixes the situation for you with ngrok).
	app_config._config[ "LAMBDA_CALLBACK_ENDPOINT" ] = get_lambda_callback_endpoint(
		app_config,
		tornado_config
	)

	logit( "Lambda callback endpoint is " + app_config.get( "LAMBDA_CALLBACK_ENDPOINT" ) )

	# Start API server
	app = make_app(
		app_config,
		tornado_config
	)
	server = tornado.httpserver.HTTPServer(
		app
	)
	server.bind(
		7777
	)
	
	# Start websocket server
	websocket_app = make_websocket_server(
		tornado_config
	)
	
	websocket_server = tornado.httpserver.HTTPServer(
		websocket_app
	)
	websocket_server.bind(
		3333
	)

	# Start scheduled heartbeats for WebSocket server
	tornado.ioloop.IOLoop.instance().add_timeout(
		datetime.timedelta(
			seconds=5
		),
		functools.partial(
			run_scheduled_heartbeat,
			tornado_config[ "websocket_router" ]
		)
	)

	# Creates tables for any new models
	# This is commented out by default because it makes Alembic autogenerated migrations not work
	# (unless you drop the tables manually before you auto-generate)
	# Base.metadata.create_all( engine )

	server.start()
	websocket_server.start()
	tornado.ioloop.IOLoop.current().start()
