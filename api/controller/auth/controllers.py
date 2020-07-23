import hmac
import hashlib
import json
import time

import pinject
import stripe
from email_validator import validate_email, EmailNotValidError
from tornado import gen
from jsonschema import validate as validate_schema

from assistants.accounts import get_user_free_trial_information
from assistants.aws_account_management.account_pool_manager import AwsAccountPoolManager, AwsAccountPoolEmptyException
from controller import BaseHandler
from controller.decorators import authenticated
from models import Organization, User, EmailAuthToken, Project, ProjectVersion, ProjectConfig, AWSAccount
from pyconstants.project_constants import DEFAULT_PROJECT_CONFIG
from services.project_inventory.project_inventory_service import ProjectInventoryService


class GetAuthenticationStatus(BaseHandler):
    @authenticated
    @gen.coroutine
    def get(self):
        current_user = self.get_authenticated_user()

        if current_user:
            intercom_user_hmac = hmac.new(
                # secret key (keep safe!)
                bytes(self.app_config.get("intercom_hmac_secret"), encoding="UTF-8"),
                # user's email address
                bytes(current_user.email, encoding="UTF-8"),
                # hash function
                digestmod=hashlib.sha256
            ).hexdigest()

            self.write({
                "authenticated": True,
                "name": current_user.name,
                "email": current_user.email,
                "permission_level": current_user.permission_level,
                "trial_information": get_user_free_trial_information(
                    self.get_authenticated_user()
                ),
                "intercom_user_hmac": intercom_user_hmac
            })
            return

        self.write({
            "success": True,
            "authenticated": False
        })


class NewRegistrationDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, project_inventory_service):
        pass


class NewRegistration(BaseHandler):
    dependencies = NewRegistrationDependencies
    project_inventory_service: ProjectInventoryService = None

    @gen.coroutine
    def post(self):
        """
        Register a new Refinery account.

        This will trigger an email to verify the user's account.
        Email is used for authentication, so by design the user will
        have to validate their email to log into the service.
        """
        schema = {
            "type": "object",
            "properties": {
                "organization_name": {
                    "type": "string",
                },
                "name": {
                    "type": "string",
                },
                "email": {
                    "type": "string",
                },
                "phone": {
                    "type": "string",
                },
                "stripe_token": {
                    "type": "string",
                }
            },
            "required": [
                "organization_name",
                "name",
                "email",
                "phone",
                "stripe_token",
            ]
        }

        validate_schema(self.json, schema)

        self.logger("Processing user registration...")

        # Before we continue, check if the email is valid
        try:
            email_validator = validate_email(
                self.json["email"]
            )
            email = email_validator["email"]  # replace with normalized form
        except EmailNotValidError as e:
            self.logger("Invalid email provided during signup!")
            self.write({
                "success": False,
                "result": {
                    "code": "INVALID_EMAIL",
                    "msg": str(e)  # The exception string is user-friendly by design.
                }
            })
            raise gen.Return()

        # Create new organization for user
        new_organization = Organization()
        new_organization.name = self.json["organization_name"]

        # Set defaults
        new_organization.payments_overdue = False

        # Check if the user is already registered
        user = self.dbsession.query(User).filter_by(
            email=self.json["email"]
        ).first()

        # If the user already exists, stop here and notify them.
        # They should be given the option to attempt to authenticate/confirm
        # their account by logging in.
        if user is not None:
            self.write({
                "success": False,
                "result": {
                    "code": "USER_ALREADY_EXISTS",
                    "msg": "A user with that email address already exists!"
                }
            })
            raise gen.Return()

        # Create the user itself and add it to the organization
        new_user = User()
        new_user.name = self.json["name"]
        new_user.email = self.json["email"]
        new_user.phone_number = self.json["phone"]
        new_user.has_valid_payment_method_on_file = True

        # Create a new email auth token as well
        email_auth_token = EmailAuthToken()

        # Pull out the authentication token
        raw_email_authentication_token = email_auth_token.token

        # Add the token to the list of the user's token
        new_user.email_auth_tokens.append(
            email_auth_token
        )

        # Add user to the organization
        new_organization.users.append(
            new_user
        )

        # Set this user as the billing admin
        new_organization.billing_admin_id = new_user.id

        self.dbsession.add(new_organization)

        # Stash some information about the signup incase we need it later
        # for fraud-style investigations.
        user_agent = self.request.headers.get("User-Agent", "Unknown")
        x_forwarded_for = self.request.headers.get("X-Forwarded-For", "Unknown")
        client_ip = self.request.remote_ip

        # noinspection PyUnresolvedReferences
        try:
            # Additionally since they've validated their email we'll add them to Stripe
            customer_id = yield self.task_spawner.stripe_create_customer(
                new_user.email,
                new_user.name,
                new_user.phone_number,
                self.json["stripe_token"],
                {
                    "user_agent": user_agent,
                    "client_ip": client_ip,
                    "x_forwarded_for": x_forwarded_for,
                }
            )
        except stripe.error.CardError as e:
            self.logger("Card declined: ")
            self.logger(e)
            self.write({
                "success": False,
                "code": "INVALID_CARD_ERROR",
                "msg": "Invalid payment information!"
            })
            self.dbsession.rollback()
            raise gen.Return()
        except stripe.error.StripeError as e:
            self.logger("Exception occurred while creating stripe account: ")
            self.logger(e)
            self.write({
                "success": False,
                "code": "GENERIC_STRIPE_ERROR",
                "msg": "An error occurred while communicating with the Stripe API."
            })
            self.dbsession.rollback()
            raise gen.Return()
        except Exception as e:
            self.logger("Exception occurred while creating stripe account: ")
            self.logger(e)
            self.write({
                "success": False,
                "code": "UNKNOWN_ERROR",
                "msg": "Some unknown error occurred, this shouldn't happen!"
            })
            self.dbsession.rollback()
            raise gen.Return()

        # Set user's payment_id to the Stripe customer ID
        new_user.payment_id = customer_id

        self.dbsession.commit()

        # Add default projects to the user's account
        example_projects = self.project_inventory_service.add_example_projects_user(user)

        for project in example_projects:
            self.dbsession.add(project)

        self.dbsession.commit()

        # Send registration confirmation link to user's email address
        # The first time they authenticate via this link it will both confirm
        # their email address and authenticate them.
        self.logger("Sending user their registration confirmation email...")
        yield self.task_spawner.send_registration_confirmation_email(
            self.json["email"],
            raw_email_authentication_token
        )

        self.write({
            "success": True,
            "result": {
                "msg": "Registration was successful! Please check your inbox to validate your email address and to log in."
            }
        })

        # This is sent internally so that we can keep tabs on new users coming through.
        self.task_spawner.send_internal_registration_confirmation_email(
            self.json["email"],
            self.json["name"],
            self.json["phone"]
        )


class EmailLinkAuthenticationDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, aws_account_freezer, aws_account_pool_manager):
        pass


class EmailLinkAuthentication(BaseHandler):
    dependencies = EmailLinkAuthenticationDependencies
    aws_account_freezer = None
    aws_account_pool_manager: AwsAccountPoolManager = None

    @gen.coroutine
    def get(self, email_authentication_token=None):
        """
        This is the endpoint which is linked to in the email send out to the user.

        Currently this responds with ugly text errors, but eventually it will be just
        another REST-API endpoint.
        """
        self.logger("User is authenticating via email link")

        # Query for the provided authentication token
        email_authentication_token = self.dbsession.query(EmailAuthToken).filter_by(
            token=str(email_authentication_token)
        ).first()

        if email_authentication_token is None:
            self.logger("User's token was not found in the database", "error")
            self.write("Invalid authentication token, did you copy the link correctly?")
            raise gen.Return()

        # Calculate token age
        token_age = (int(time.time()) - email_authentication_token.timestamp)

        # Check if the token is expired
        if email_authentication_token.is_expired == True:
            self.logger("The user's email token was already marked as expired.", "error")
            self.write("That email token has expired, please try authenticating again to request a new one.")
            raise gen.Return()

        # Check if the token is older than the allowed lifetime
        # If it is then mark it expired and return an error
        if token_age >= int(self.app_config.get("email_token_lifetime")):
            self.logger("The user's email token was too old and was marked as expired.")

            # Mark the token as expired in the database
            email_authentication_token.is_expired = True
            self.dbsession.commit()

            self.write("That email token has expired, please try authenticating again to request a new one.")
            raise gen.Return()

        """
		NOTE: We've disabled expiration of email links on click for Enrique Enciso since
		he wants to use it for his team and they want to share an account. This is basically
		a holdover until we have more proper team support.

		# Since the user has now authenticated
		# Mark the token as expired in the database
		email_authentication_token.is_expired = True
		"""

        # Pull the user's organization
        user_organization = self.dbsession.query(Organization).filter_by(
            id=email_authentication_token.user.organization_id
        ).first()
        if user_organization is None:
            self.logger("User login was denied due to their account not having an organization")
            self.write("Your account is in a corrupt state, please contact customer support for more information.")
            raise gen.Return()

        # Check if the user has previously authenticated via
        # their email address. If not we'll mark their email
        # as validated as well.
        if not email_authentication_token.user.email_verified:
            try:
                self.aws_account_pool_manager.reserve_aws_account_for_organization(self.dbsession, user_organization.id)
                email_authentication_token.user.email_verified = True
            except AwsAccountPoolEmptyException:
                # If we have no accounts to provide this organization, we want to raise an error
                self.logger(f"Unable to provide organization {user_organization.id} with an AWS account", "error")

                # TODO this message should be standardized
                self.write("Unable to complete account registration due to an internal error, please reach out to the Refinery team to have this issue resolved.")
                raise gen.Return()

        self.dbsession.commit()

        # Check if the user's account is disabled
        # If it's disabled don't allow the user to log in at all.
        if email_authentication_token.user.disabled:
            self.logger("User login was denied due to their account being disabled!")
            self.write("Your account is currently disabled, please contact customer support for more information.")
            raise gen.Return()

        # Check if the user's organization is disabled
        # If it's disabled don't allow the user to log in at all.
        if user_organization.disabled:
            self.logger("User login was denied due to their organization being disabled!")
            self.write("Your organization is currently disabled, please contact customer support for more information.")
            raise gen.Return()

        self.logger("User authenticated successfully")

        # Authenticate the user via secure cookie
        self.authenticate_user_id(
            email_authentication_token.user.id
        )

        self.redirect(
            "/"
        )


class Authenticate(BaseHandler):
    @gen.coroutine
    def post(self):
        """
        This fires off an authentication email for a given user.
        """
        schema = {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                }
            },
            "required": [
                "email"
            ]
        }

        validate_schema(self.json, schema)

        # Get user based off of the provided email
        user = self.dbsession.query(User).filter_by(
            email=self.json["email"]
        ).first()

        if user is None:
            self.write({
                "success": False,
                "code": "USER_NOT_FOUND",
                "msg": "No user was found with that email address."
            })
            raise gen.Return()

        # Generate an auth token and add it to the user's account
        # Create a new email auth token as well
        email_auth_token = EmailAuthToken()

        # Pull out the authentication token
        raw_email_authentication_token = email_auth_token.token

        # Add the token to the list of the user's token
        user.email_auth_tokens.append(
            email_auth_token
        )

        self.dbsession.commit()

        yield self.task_spawner.send_authentication_email(
            user.email,
            raw_email_authentication_token
        )

        self.write({
            "success": True,
            "msg": "Sent an authentication email to the user. Please click the link in the email to log in to Refinery!"
        })


class Logout(BaseHandler):
    @gen.coroutine
    def post(self):
        self.clear_cookie("session")
        self.write({
            "success": True
        })
