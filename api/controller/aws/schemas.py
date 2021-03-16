RUN_TMP_LAMBDA_SCHEMA = {
    "type": "object",
    "properties": {
        "project_id": {"type": "string"},
        "input_data": {},
        "backpack": {},
        "diagram_data": {"type": "string"},
        "block_id": {"type": "string"}
    },
    "required": [
        "project_id",
        "input_data",
        "diagram_data",
        "block_id"
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
