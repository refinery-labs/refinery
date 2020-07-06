GITHUB_CREATE_NEW_REPO_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
        },
        "description": {
            "type": "string",
        }
    },
    "required": [
        "name",
        "description"
    ]
}