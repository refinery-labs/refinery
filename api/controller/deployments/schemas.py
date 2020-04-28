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
