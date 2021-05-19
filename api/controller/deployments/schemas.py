from enum import Enum, unique

@unique
class DeploySecureResolverAction(Enum):
    URL = "url",
    SECRETS = "secrets",
    DEPLOY = "deploy",
    REMOVE = "remove"


def make_action_schema(payload_type: DeploySecureResolverAction, payload_schema):
    return {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": [payload_type]
            },
            "payload": {
                "type": "object",
                **payload_schema
            }
        },
        "required": [
            "type",
            "payload"
        ]
    }


DEPLOY_SECURE_RESOLVER__BUILD_ACTION_SCHEMA = {
    "properties": {
        "stage": {
            "type": "string",
            "enum": ["dev", "prod"]
        },
        "container_uri": {
            "type": "string",
        },
        "app_dir": {
            "type": "string",
        },
        "language": {
            "type": "string",
        },
        "functions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "import_path": {
                        "type": "string"
                    },
                    "function_name": {
                        "type": "string"
                    },
                    "work_dir": {
                        "type": "string"
                    }
                },
                "required": [
                    "import_path",
                    "function_name"
                ]
            }
        },
    },
    "required": [
        "stage",
        "container_uri",
        "app_dir",
        "language",
        "functions"
    ]
}

DEPLOY_SECURE_RESOLVER__REMOVE_ACTION_SCHEMA = {
    "properties": {
        "stage": {
            "type": "string",
            "enum": ["dev", "prod"]
        }
    },
    "required": [
        "stage"
    ]
}

DEPLOY_SECURE_RESOLVER__URL_ACTION_SCHEMA = {
    "properties": {
        "deployment_id": {
            "type": "string"
        }
    },
    "required": [
        "deployment_id"
    ]
}

DEPLOY_SECURE_RESOLVER__WORKFLOW_STATES_ACTION_SCHEMA = {
    "properties": {
        "deployment_id": {
            "type": "string"
        }
    },
    "required": [
        "deployment_id"
    ]
}

DEPLOY_SECURE_RESOLVER__SECRETS_ACTION_SCHEMA = {
    "properties": {
        "deployment_id": {
            "type": "string"
        }
    },
    "required": [
        "deployment_id"
    ]
}

DEPLOY_SECURE_RESOLVER_SCHEMA = {
    "type": "object",
    "properties": {
        "project_id": {
            "type": "string"
        },
        "action": {
            "type": "object",
            "oneOf": [
                make_action_schema("url", DEPLOY_SECURE_RESOLVER__URL_ACTION_SCHEMA),
                make_action_schema("workflow_states", DEPLOY_SECURE_RESOLVER__WORKFLOW_STATES_ACTION_SCHEMA),
                make_action_schema("secrets", DEPLOY_SECURE_RESOLVER__SECRETS_ACTION_SCHEMA),
                make_action_schema("build", DEPLOY_SECURE_RESOLVER__BUILD_ACTION_SCHEMA),
                make_action_schema("remove", DEPLOY_SECURE_RESOLVER__REMOVE_ACTION_SCHEMA)
            ]
        }
    },
    "required": [
        "action",
        "project_id"
    ]
}

GET_LATEST_PROJECT_DEPLOYMENT_SCHEMA = {
    "type": "object",
    "properties": {
            "project_id": {
                "type": "string",
            }
    },
    "required": [
        "project_id"
    ]
}

DELETE_DEPLOYMENTS_IN_PROJECT_SCHEMA = {
    "type": "object",
    "properties": {
            "project_id": {
                "type": "string",
            }
    },
    "required": [
        "project_id"
    ]
}
