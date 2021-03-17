DEPLOY_SECURE_RESOLVER_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["build", "remove", "arn"]
        },
        "stage": {
            "type": "string",
            "enum": ["dev", "prod"]
        },
        "project_id": {
            "type": "string",
        },
        "container_uri": {
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
                    }
                }
            }
        }
    },
    "required": [
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
