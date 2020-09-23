from typing import Dict, List, Any

EMPTY_ZIP_DATA = b"PK\x05\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"


# Note: These are referenced CodeBlockWorkflowState.setup, when adding a new value here, make sure the
# runtime is properly set if the value is specified as a language.
PYTHON_36_TEMPORAL_RUNTIME_PRETTY_NAME = "Python 3.6 Temporal"
NODEJS_12_TEMPORAL_RUNTIME_PRETTY_NAME = "Node JS 12 Temporal"

DEFAULT_PROJECT_CONFIG = {
    "version": "1.0.0",
    "environment_variables": {},
    "api_gateway": {
        "gateway_id": False,
    },
    "logging": {
        "level": "LOG_ALL",
    }
}


LAMBDA_SUPPORTED_LANGUAGES = [
    "python3.6",
    "python2.7",
    "nodejs8.10",
    "nodejs10.16.3",
    "nodejs10.20.1",
    "php7.3",
    "go1.12",
    "ruby2.6.4",
    PYTHON_36_TEMPORAL_RUNTIME_PRETTY_NAME,
    NODEJS_12_TEMPORAL_RUNTIME_PRETTY_NAME
]


# These languages are all custom
CUSTOM_RUNTIME_LANGUAGES = [
    "nodejs8.10",
    "nodejs10.16.3",
    "nodejs10.20.1",
    "php7.3",
    "go1.12",
    "python2.7",
    "python3.6",
    "ruby2.6.4"
]


LAMBDA_BASE_LIBRARIES: Dict[str, List[str]] = {
    "python3.6": [],
    "python2.7": [],
    "nodejs8.10": [],
    "nodejs10.16.3": [],
    "nodejs10.20.1": [],
    "php7.3": [],
    "go1.12": [],
    "ruby2.6.4": []
}

LAMBDA_TEMPORAL_RUNTIMES: Dict[str, str] = {
    "python3.6": "python36/lambda_function.py",
    "nodejs12.x": "nodejs12/lambda_function.js"
}

# Regex for character whitelists for different fields
REGEX_WHITELISTS = {
    "arn": r"[^a-zA-Z0-9\:\_\-]+",
    "execution_pipeline_id": r"[^a-zA-Z0-9\-]+",
    "project_id": r"[^a-zA-Z0-9\-]+",
}

THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME = "RefinerySelfHostedLambdaRole"
