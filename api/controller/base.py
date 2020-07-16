from __future__ import annotations

import pinject
import tornado.web
import json
import time

from tornado import gen
from typing import Optional, TYPE_CHECKING

from models.users import User
from models.projects import Project
from models.aws_accounts import AWSAccount
from models.organizations import Organization

from utils.general import logit
from utils.locker import Locker

if TYPE_CHECKING:
    from assistants.task_spawner.task_spawner_assistant import TaskSpawner
    from config.app_config import AppConfig

CSRF_EXEMPT_ENDPOINTS = [
    "/services/v1/mark_account_needs_closing",
    "/api/v1/github/proxy",
    "/services/v1/store_lambda_execution_details"
]


class TornadoBaseHandlerInjectionMixin:
    dependencies = None

    @staticmethod
    def set_object_deps(object_graph, obj, dep_class):
        provided_deps = object_graph.provide(dep_class)
        for name, dep in provided_deps.__dict__.items():
            setattr(obj, name, dep)

    def initialize(self, **kwargs):
        object_graph = kwargs["object_graph"]

        if self.dependencies != BaseHandler.dependencies:
            self.set_object_deps(object_graph, self, BaseHandler.dependencies)
        self.set_object_deps(object_graph, self, self.dependencies)


class BaseHandlerDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, logger, db_session_maker, app_config, task_spawner):
        pass


class BaseHandler(TornadoBaseHandlerInjectionMixin, tornado.web.RequestHandler):
    authenticated_user: Optional[User]
    dependencies = BaseHandlerDependencies
    logger = None
    db_session_maker = None
    app_config: AppConfig = None
    task_spawner: TaskSpawner = None

    _dbsession = None
    json = None
    allowed_origins = None

    def __init__(self, *args, **kwargs):
        super(BaseHandler, self).__init__(*args, **kwargs)

        if self.initialize != BaseHandler.initialize:
            BaseHandler.initialize(self, **kwargs)

        self.set_header( "Access-Control-Allow-Headers", "Content-Type, X-CSRF-Validation-Header" )
        self.set_header( "Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS, HEAD" )
        self.set_header( "Access-Control-Allow-Credentials", "true" )
        self.set_header( "Access-Control-Max-Age", "600" )
        self.set_header( "X-Frame-Options", "deny" )
        self.set_header( "Content-Security-Policy", "default-src 'self'" )
        self.set_header( "X-XSS-Protection", "1; mode=block" )
        self.set_header( "X-Content-Type-Options", "nosniff" )
        self.set_header( "Cache-Control", "no-cache, no-store, must-revalidate" )
        self.set_header( "Pragma", "no-cache" )
        self.set_header( "Expires", "0" )

        # For caching the currently-authenticated user
        self.authenticated_user = None

        # For caching the user's aws credentials
        self.user_aws_credentials = None

        self._dbsession = None

        self.allowed_origins = json.loads(self.app_config.get("access_control_allow_origins"))

        self.task_locker = Locker("refinery")

    @property
    def dbsession(self):
        if self._dbsession is None:
            self._dbsession = self.db_session_maker()

        return self._dbsession

    def authenticate_user_id( self, user_id ):
        # Set authentication cookie
        self.set_secure_cookie(
            "session",
            json.dumps({
                "user_id": user_id,
                "created_at": int( time.time() ),
            }),
            expires_days=int( self.app_config.get( "cookie_expire_days" ) )
        )

    def is_owner_of_project( self, project_id ):
        # Check to ensure the user owns the project
        project = self.dbsession.query( Project ).filter_by(
            id=project_id
        ).first()

        # Iterate over project owners and see if one matches
        # the currently authenticated user
        is_owner = False

        for project_owner in project.users:
            if self.get_authenticated_user_id() == project_owner.id:
                is_owner = True

        return is_owner

    def get_authenticated_user_cloud_configuration( self ):
        """
        This just returns the first cloud configuration. Short term use since we'll
        eventually be moving to a multiple AWS account deploy system.
        """
        def raise_credential_error():
            self.write({
                "success": False,
                "code": "NO_CREDENTIALS",
                "msg": "No aws credentials are present for the current user.",
            })
            raise gen.Return()

        if self.user_aws_credentials is not None:
            return self.user_aws_credentials

        # Pull the authenticated user's organization
        user_organization = self.get_authenticated_user_org()

        if user_organization is None:
            logit("Account has no organization associated with it!")

            # credential error is raised, does not return
            raise_credential_error()

        aws_account = self.dbsession.query(AWSAccount).filter_by(
            organization_id=user_organization.id,
            aws_account_status="IN_USE"
        ).first()

        # We also pull their account because we want to include
        # What tier the user is at in the returned dict so we can
        # use it to make deploy-decisions/etc.
        # This access is for free since it's stored on the handler
        # due to the get_authenticated_user_org() call above.
        user = self.get_authenticated_user()

        if aws_account:
            self.user_aws_credentials = aws_account.to_dict()
            self.user_aws_credentials[ "tier" ] = user.tier
            return self.user_aws_credentials

        logit("Account has no AWS account associated with it!")

        # credential error is raised, does not return
        raise_credential_error()

    def get_authenticated_user_org( self ):
        # First we grab the organization ID
        authentication_user = self.get_authenticated_user()

        if authentication_user is None:
            return None

        # Get organization user is a part of
        user_org = self.dbsession.query( Organization ).filter_by(
            id=authentication_user.organization_id
        ).first()

        return user_org

    def get_authenticated_user_id( self ):
        session_data = self.get_secure_session_data(int( self.app_config.get( "cookie_expire_days" ) ))

        if not session_data or "user_id" not in session_data:
            return None

        # Hack to force these users to re-auth on a shorter timespan
        short_lifespan_users = [
            "7b0f7808-1d40-4da4-9a98-500956d517e3",
            "e89d2d4a-7d61-4dca-b1a0-3ba3cd9842c9"
        ]

        if session_data["user_id"] in short_lifespan_users:
            # Force check that the user re-auths within one day
            short_lifespan_session_data = self.get_secure_session_data(17)

            self.logger("User with manual shortened lifespan: " + session_data["user_id"])

            if not short_lifespan_session_data or "user_id" not in short_lifespan_session_data:
                return None

        return session_data["user_id"]

    def get_secure_session_data(self, cookie_expiration_days):
        # Retrieves data from the session cookie
        session_data = self.get_secure_cookie_data("session", cookie_expiration_days)
        if session_data is None:
            self.logger("Unable to get session data", "warning")
            return None

        try:
            return json.loads(
                session_data
            )
        except ValueError as e:
            self.logger("Unable to deserialize session data: " + repr(e), "warning")
            return None

    def get_secure_cookie_data(self, cookie_name, cookie_expiration_days):
        # Get secure cookie data
        return self.get_secure_cookie(
            cookie_name,
            max_age_days=cookie_expiration_days
        )

    def get_authenticated_user( self):
        """
        Grabs the currently authenticated user

        This will be cached after the first call of
        this method,
        """
        if self.authenticated_user is not None:
            return self.authenticated_user

        user_id = self.get_authenticated_user_id()

        if user_id is None:
            return None

        # Pull related user
        authenticated_user: User = self.dbsession.query( User ).filter_by(
            id=str( user_id )
        ).first()

        self.authenticated_user = authenticated_user

        return authenticated_user

    def prepare( self ):
        """
        For the health endpoint all of this should be skipped.
        """
        if self.request.path == "/api/v1/health":
            return

        """
        /service/ path protection requiring a shared-secret to access them.
        """
        if self.request.path.startswith( "/services/" ):
            services_auth_header = self.request.headers.get( "X-Service-Secret", None )
            services_auth_param = self.get_argument( "secret", None )

            service_secret = None
            if services_auth_header:
                service_secret = services_auth_header
            elif services_auth_param:
                service_secret = services_auth_param

            if self.app_config.get( "service_shared_secret" ) != service_secret:
                self.error(
                    "You are hitting a service URL, you MUST provide the shared secret in either a 'secret' parameter or the 'X-Service-Secret' header to use this.",
                    "ACCESS_DENIED_SHARED_SECRET_REQUIRED"
                )
                return

        csrf_validated = self.request.headers.get(
            "X-CSRF-Validation-Header",
            False
        )

        if not csrf_validated and self.request.method != "OPTIONS" and \
                self.request.method != "GET" and \
                not any([self.request.path.startswith(path) for path in CSRF_EXEMPT_ENDPOINTS]):
            self.error(
                "No CSRF validation header supplied!",
                "INVALID_CSRF"
            )
            raise gen.Return()

        # Logic for adding Cross-origin resource sharing (CORS) headers.
        if "Origin" in self.request.headers:
            host_header = self.request.headers["Origin"]

            # Identify if the request is coming from a domain that is in the whitelist
            # If it is, set the necessary CORS response header to allow the request to succeed.
            if host_header in self.allowed_origins:
                self.set_header("Access-Control-Allow-Origin", host_header)

        self.json = False

        if self.request.body:
            try:
                json_data = json.loads(self.request.body)
                self.json = json_data
            except ValueError:
                pass

    def options(self):
        pass

    # Hack to stop Tornado from sending the Etag header
    def compute_etag(self):
        return None

    def throw_404(self):
        self.set_status(404)
        self.write("Resource not found")

    def error( self, error_message, error_id ):
        self.set_status( 500 )
        logit(
            error_message,
            message_type="warn"
        )

        self.finish({
            "success": False,
            "msg": error_message,
            "code": error_id
        })

    def on_finish( self ):
        if self._dbsession is not None:
            self._dbsession.close()

    # Required to be implemented on abstract class
    # TODO: Figure out what to do with this
    def data_received(self, chunk):
        pass
