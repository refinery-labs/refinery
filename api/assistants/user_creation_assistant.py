import pinject
from tornado import gen

from models.users import User
from services.auth.oauth_service import OAuthService
from services.project_inventory.project_inventory_service import ProjectInventoryService
from services.stripe.stripe_service import StripeService
from services.user_management.user_management_service import UserManagementService
from utils.general import logit


class UserCreationAssistant:
    logger = None  # type: logit
    oauth_service = None  # type: OAuthService
    github_oauth_provider = None  # type: GithubOAuthProvider
    project_inventory_service = None  # type: ProjectInventoryService
    stripe_service = None  # type: StripeService
    user_management_service = None  # type: UserManagementService


    @pinject.copy_args_to_public_fields
    def __init__(
        self,
        logger,
        oauth_service,
        github_oauth_provider,
        project_inventory_service,
        stripe_service,
        user_management_service
    ):
        """
        This class contains logic for creating and managing User instances by utilizing many services.
        :type logger: logit
        :type oauth_service: OAuthService
        :type github_oauth_provider: GithubOAuthProvider
        :type project_inventory_service: ProductInventoryService
        :type stripe_service: StripeService
        :type user_management_service: UserManagementService
        """
        pass

    @gen.coroutine
    def setup_initial_user_state(self, dbsession, request, user):
        """
        Handles setting up the initial state for a new user.
        Should be called whenever a new user is created (sets up example projects, etc).
        :type dbsession: sqlalchemy.orm.Session
        :param request: Subset of the Tornado request object to pull headers from.
        :type user: User
        """
        customer_id = yield self.create_stripe_record_for_user(request, user)
        user.payment_id = customer_id

        example_projects = self.project_inventory_service.add_example_projects_user(user)

        for project in example_projects:
            dbsession.add(project)

    @gen.coroutine
    def find_or_create_user_via_oauth( self, dbsession, oauth_user_data, request ):
        """
        Finds or creates a user via OAuth.
        :type dbsession: sqlalchemy.orm.Session
        :param oauth_user_data: Instance of OAuthUserData that contains information to process the OAuth login.
        :type oauth_user_data: OAuthUserData
        :param request: Subset of the Tornado request object to pull headers from.
        :return: Found user or new user that was created
        """
        user = self.find_existing_user_via_oauth(dbsession, oauth_user_data)
        if not user:
            user = yield self.create_user_via_oauth(dbsession, oauth_user_data, request)

        raise gen.Return( user )

    def find_existing_user_via_oauth( self, dbsession, oauth_user_data ):
        return self.oauth_service.search_for_existing_user(dbsession, oauth_user_data)

    @gen.coroutine
    def create_user_via_oauth( self, dbsession, oauth_user_data, request ):
        """
        Creates a user via OAuth.
        :type dbsession: sqlalchemy.orm.Session
        :param oauth_user_data: Instance of OAuthUserData that contains information to process the OAuth login.
        :type oauth_user_data: OAuthUserData
        :param request: Subset of the Tornado request object to pull headers from.
        :return: New user that was created
        """

        user, organization = self.user_management_service.create_new_user_and_organization(
            dbsession,
            oauth_user_data.name,
            oauth_user_data.email,
            require_email_verification=False
        )

        yield self.setup_initial_user_state(dbsession, request, user)

        # This adds all of the different "relationships" of data in one step (organization, user, oauth, oauth data)
        dbsession.add(organization)

        self.logger("Wrote new user to the database: " + user.email)

        raise gen.Return(user)

    def update_user_oauth_record(self, dbsession, user, oauth_user_data):
        """
        Creates a user via OAuth.
        :type dbsession: sqlalchemy.orm.Session
        :param user: User instance to add OAuth record to
        :type user: User
        :param oauth_user_data: Instance of OAuthUserData that contains information to process the OAuth login.
        :type oauth_user_data: OAuthUserData
        """
        user_oauth_account = self.oauth_service.add_token_for_user(
            dbsession,
            user,
            oauth_user_data
        )

        user.oauth_token_entries.append(user_oauth_account)

    @gen.coroutine
    def create_stripe_record_for_user(self, request, user):

        # Stash some information about the signup in case we need it later
        # for fraud-style investigations.
        user_agent = request.headers.get("User-Agent", "Unknown")
        x_forwarded_for = request.headers.get("X-Forwarded-For", "Unknown")
        client_ip = request.remote_ip

        customer_id = yield self.stripe_service.create_new_customer(
            user,
            user_agent,
            x_forwarded_for,
            client_ip
        )

        raise gen.Return(customer_id)
