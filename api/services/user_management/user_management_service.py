from models.email_auth_tokens import EmailAuthToken
from models.organizations import Organization
from models.users import User
from services.user_management.exceptions import DuplicateUserCreationError


class UserManagementService:
    def __init__(self, logger):
        """
        Manages user accounts (and organizations, for now)
        :type logger: logit
        """
        self.logger = logger

    def create_new_user_and_organization(
            self,
            dbsession,
            name,
            email,
            phone=None,
            organization_name="",
            require_email_verification=True
    ):
        """
        Creates a new User within a new Organization.
        :param dbsession: An active SQLAlchemy database session
        :type dbsession: sqlalchemy.orm.Session
        :param name: Name of the user to be created
        :type name: basestring
        :param email: Email address for user
        :type email: basestring
        :param phone: (optional) Phone number for user
        :type phone: basestring
        :param organization_name: (optional) Name of the user's organization
        :type organization_name: basestring
        :param require_email_verification: If true, then user must verify their email before login
        :type require_email_verification: bool
        :return: The new user and organization instances
        """
        new_user = self._create_new_user(
            dbsession,
            name,
            email,
            phone=phone,
            require_email_verification=require_email_verification
        )

        new_organization = self._create_new_organization(new_user, organization_name=organization_name)

        return new_user, new_organization

    def _create_new_organization(self, new_user, organization_name=""):
        """
        Creates and returns a new organization
        :param new_user: Instance of a User to add to the organization.
        :type new_user: User
        :param organization_name: (optional) Name of the user's organization
        :type organization_name: basestring
        :return: New organization instance
        """
        # Create new organization for user
        new_organization = Organization()
        new_organization.name = organization_name

        # Set defaults
        new_organization.payments_overdue = False

        # Set this user as the billing admin
        new_organization.billing_admin_id = new_user.id

        # Add user to the organization
        new_organization.users.append(
            new_user
        )

        return new_organization

    def _create_new_user(self, dbsession, name, email, phone=None, require_email_verification=True):
        """
        Creates a new User and the initial user's state.
        :param dbsession: An active SQLAlchemy database session
        :type dbsession: sqlalchemy.orm.Session
        :param name: Name of the user to be created
        :type name: basestring
        :param email: Email address for user
        :type email: basestring
        :param phone: (optional) Phone number for user
        :type phone: basestring
        :param require_email_verification: If true, then user must verify their email before login
        :type require_email_verification: bool
        :return:
        """
        # Check if the user is already registered
        user = dbsession.query(User).filter_by(email=email).first()

        # If the user already exists, stop here and notify them.
        # They should be given the option to attempt to authenticate/confirm their account by logging in.
        if user is not None:
            self.logger("Could not create user because a user with that email already exists: " + email)
            raise DuplicateUserCreationError("A user with that email address already exists", "USER_ALREADY_EXISTS")

        # Create the user itself and add it to the organization
        new_user = User()
        new_user.name = name
        new_user.email = email
        new_user.phone_number = phone
        new_user.has_valid_payment_method_on_file = True

        # TODO: Port over Email verification logic from server.py
        if require_email_verification:
            # Create a new email auth token as well
            email_auth_token = EmailAuthToken()

            # Pull out the authentication token
            raw_email_authentication_token = email_auth_token.token

            # Add the token to the list of the user's token
            new_user.email_auth_tokens.append(
                email_auth_token
            )

        return new_user
