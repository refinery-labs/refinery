RUN_TMP_LAMBDA_SCHEMA = {
    "type": "object",
    "properties": {
            "input_data": {},
        "backpack": {},
        "language": {
                "type": "string",
            },
        "code": {
                "type": "string",
            },
        "libraries": {
                "type": "array",
            },
        "memory": {
                "type": "integer",
            },
        "max_execution_time": {
                "type": "integer",
            },
        "environment_variables": {
                "type": "array"
            },
        "layers": {
                "type": "array"
            },
        "debug_id": {
                "type": "string"
            },
        "shared_files": {
                "type": "array",
                "default": [],
                "items": {
                        "type": "object",
                        "properties": {
                            "body": {
                                "type": "string"
                            },
                            "version": {
                                "type": "string"
                            },
                            "type": {
                                "type": "string"
                            },
                            "id": {
                                "type": "string"
                            },
                            "name": {
                                "type": "string"
                            }
                        },
                    "required": [
                            "body",
                            "version",
                            "type",
                            "id",
                            "name"
                            ]
                }
            }
    },
    "required": [
        "input_data",
        "language",
        "code",
        "libraries",
        "memory",
        "max_execution_time",
        "environment_variables",
        "layers"
    ]
}

DEPLOY_DIAGRAM_SCHEMA = {
    "title": "Deploy Diagram",
    "type": "object",
    "properties": {
            "project_id": {"type": "string"},
        "project_name": {"type": "string"},
        "project_config": {"type": "object"},
        "diagram_data": {"type": "string"},
    },
    "required": [
        "project_id",
        "project_name",
        "project_config",
        "diagram_data"
    ]
}
