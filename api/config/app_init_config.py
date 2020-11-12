import json
import os

from pyconstants.project_constants import LAMBDA_BASE_LIBRARIES, LAMBDA_TEMPORAL_RUNTIMES


def app_init_config(app_config):
    """
    Inject configuration values which require the app's initiated environment

    :param app_config:
    :return:
    """

    # Email templates
    email_templates_folder = "./email_templates/"
    email_templates = {}
    for filename in os.listdir(email_templates_folder):
        template_name = filename.split(".")[0]
        with open(email_templates_folder + filename, "r") as file_handler:
            email_templates[template_name] = file_handler.read()

    lamdba_base_codes = {}
    lambda_temporal_runtimes = {}

    customer_iam_policy = ""

    # Load the default customer IAM policy
    with open("./install/refinery-customer-iam-policy.json", "r") as file_handler:
        customer_iam_policy = json.loads(
            file_handler.read()
        )

    for language_name, libraries in LAMBDA_BASE_LIBRARIES.items():
        # Load Lambda base templates
        with open("./lambda_bases/" + language_name, "r") as file_handler:
            lamdba_base_codes[language_name] = file_handler.read()

    for language_name, folder_name in LAMBDA_TEMPORAL_RUNTIMES.items():
        # Load temporal runtimes
        # TODO, this wont work for runtimes that are multiple files.
        # I did it this way to prevent an additional file read on every build.
        with open(f'./runtimes/{folder_name}', 'r') as f:
            lambda_temporal_runtimes[language_name] = f.read()

    default_project_array = []

    default_project_directory = "./default_projects/"

    for filename in os.listdir(default_project_directory):
        with open(default_project_directory + filename, "r") as file_handler:
            default_project_array.append(
                json.loads(
                    file_handler.read()
                )
            )

    # Config keys are all uppercase to signify special use case
    init_config = dict(
        EMAIL_TEMPLATES=email_templates,
        LAMDBA_BASE_CODES=lamdba_base_codes,
        LAMBDA_TEMPORAL_RUNTIMES=lambda_temporal_runtimes,
        CUSTOMER_IAM_POLICY=customer_iam_policy,
        DEFAULT_PROJECT_ARRAY=default_project_array
    )
    for k, v in init_config.items():
        app_config._config[k] = v
