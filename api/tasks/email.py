from pystache import render
from requests import post
from utils.general import logit


def send_email(app_config, to_email_string, subject_string, message_text_string, message_html_string):
    """
    to_email_string: "example@refinery.io"
    subject_string: "Your important email"
    message_text_string: "You have an important email here!"
    message_html_string: "<h1>ITS IMPORTANT AF!</h1>"
    """

    logit("Sending email to '" + to_email_string +
          "' with subject '" + subject_string + "'...")

    requests_options = {
        "auth": ("api", app_config.get("mailgun_api_key")),
        "data": {
            "from": app_config.get("from_email"),
            "h:Reply-To": "support@refinery.io",
            "to": [
                to_email_string
            ],
            "subject": subject_string,
        }
    }

    if message_text_string:
        requests_options["data"]["text"] = message_text_string

    if message_html_string:
        requests_options["data"]["html"] = message_html_string

    response = post(
        "https://api.mailgun.net/v3/mail.refinery.io/messages",
        **requests_options
    )

    return response.text


###############################################################################
# Individual email functions
###############################################################################


def send_terraform_provisioning_error(app_config, aws_account_id, error_output):
    return send_email(
        app_config,
        app_config.get("alerts_email"),
        "[AWS Account Provisioning Error] The Refinery AWS Account #" +
        aws_account_id + " Encountered a Fatal Error During Terraform Provisioning",
        render(
            app_config.get("EMAIL_TEMPLATES")[
                "terraform_provisioning_error_alert"],
            {
                "aws_account_id": aws_account_id,
                "error_output": error_output,
            }
        ),
        False,
    )


def send_account_freeze_email(app_config, aws_account_id, amount_accumulated, organization_admin_email):
    return send_email(
        app_config,
        app_config.get("alerts_email"),
        "[Freeze Alert] The Refinery AWS Account #" + aws_account_id +
        " has been frozen for going over its account limit!",
        False,
        render(
            app_config.get("EMAIL_TEMPLATES")["account_frozen_alert"],
            {
                "aws_account_id": aws_account_id,
                "free_trial_billing_limit": app_config.get("free_trial_billing_limit"),
                "amount_accumulated": amount_accumulated,
                "organization_admin_email": organization_admin_email,
            }
        ),
    )


def send_registration_confirmation_email(app_config, email_address, auth_token):
    registration_confirmation_link = app_config.get(
        "web_origin") + "/authentication/email/" + auth_token

    return send_email(
        app_config,
        email_address,
        "Refinery.io - Confirm your Refinery registration",
        render(
            app_config.get("EMAIL_TEMPLATES")[
                "registration_confirmation_text"],
            {
                "registration_confirmation_link": registration_confirmation_link,
            }
        ),
        render(
            app_config.get("EMAIL_TEMPLATES")[
                "registration_confirmation"],
            {
                "registration_confirmation_link": registration_confirmation_link,
            }
        ),
    )


def send_internal_registration_confirmation_email(app_config, customer_email_address, customer_name, customer_phone):
    return send_email(
        app_config,
        app_config.get("internal_signup_notification_email"),
        "Refinery User Signup, " + customer_email_address,
        render(
            app_config.get("EMAIL_TEMPLATES")[
                "internal_registration_notification_text"],
            {
                "customer_email_address": customer_email_address,
                "customer_name": customer_name,
                "customer_phone": customer_phone
            }
        ),
        render(
            app_config.get("EMAIL_TEMPLATES")[
                "internal_registration_notification"],
            {
                "customer_email_address": customer_email_address,
                "customer_name": customer_name,
                "customer_phone": customer_phone
            }
        ),
    )


def send_authentication_email(app_config, email_address, auth_token):
    authentication_link = app_config.get(
        "web_origin") + "/authentication/email/" + auth_token

    return send_email(
        app_config,
        email_address,
        "Refinery.io - Login by email confirmation",
        render(
            app_config.get("EMAIL_TEMPLATES")[
                "authentication_email_text"],
            {
                "email_authentication_link": authentication_link,
            }
        ),
        render(
            app_config.get("EMAIL_TEMPLATES")["authentication_email"],
            {
                "email_authentication_link": authentication_link,
            }
        ),
    )
