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

STORE_LAMBDA_EXECUTION_DETAILS_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "account_id": {
                "type": "string",
                "pattern": "[0-9]{12}"
            },
            "log_name": {
                "type": "string",
            },
            "log_stream": {
                "type": "string",
            },
            "lambda_name": {
                "type": "string",
            },
            "raw_line": {
                "type": "string",
            },
            "timestamp": {
                "type": "number",
            },
            "timestamp_ms": {
                "type": "number",
            },
            "duration": {
                "type": "string",
            },
            "memory_size": {
                "type": "number",
            },
            "max_memory_used": {
                "type": "number",
            },
            "billed_duration": {
                "type": "number",
            },
            "report_requestid": {
                "type": "string",
            }
        },
        "required": [
            "account_id",
            "log_name",
            "log_stream",
            "lambda_name",
            "raw_line",
            "timestamp",
            "timestamp_ms",
            "duration",
            "memory_size",
            "max_memory_used",
            "billed_duration",
            "report_requestid"
        ]
    }
}
