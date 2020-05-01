from pyconstants.project_constants import LAMBDA_SUPPORTED_LANGUAGES

RUN_LAMBDA_SCHEMA = {
    "type": "object",
    "properties": {
            "input_data": {},
        "backpack": {},
        "arn": {
                "type": "string",
                },
        "execution_id": {
                "type": "string",
                },
        "debug_id": {
                "type": "string",
                }
    },
    "required": [
        "input_data",
        "arn"
    ]
}

GET_CLOUDWATCH_LOGS_FOR_LAMBDA_SCHEMA = {
    "type": "object",
    "properties": {
            "arn": {
                "type": "string",
            },

    },
    "required": [
        "arn"
    ]
}

UPDATE_ENVIRONMENT_VARIABLES_SCHEMA = {
    "type": "object",
    "properties": {
            "project_id": {
                "type": "string",
            },
        "arn": {
                "type": "string",
        },
        "environment_variables": {
                "type": "array",
                },

    },
    "required": [
        "arn",
        "environment_variables"
    ]
}

BUILD_LIBRARIES_PACKAGE_SCHEMA = {
    "type": "object",
    "properties": {
            "libraries": {
                "type": "array"
            },
        "language": {
                "type": "string",
                "enum": LAMBDA_SUPPORTED_LANGUAGES
        }
    },
    "required": [
        "libraries",
        "language"
    ]
}

CHECK_IF_LIBRARIES_CACHED_SCHEMA = {
    "type": "object",
    "properties": {
            "libraries": {
                "type": "array"
            },
        "language": {
                "type": "string",
                "enum": LAMBDA_SUPPORTED_LANGUAGES
        }
    },
    "required": [
        "libraries",
        "language"
    ]
}
