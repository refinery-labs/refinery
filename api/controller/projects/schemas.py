SAVE_PROJECT_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
            "project_id": {
                "type": "string",
            },
        "config": {
                "type": "string",
            }
    },
    "required": [
        "project_id",
        "config"
    ]
}

SEARCH_SAVED_PROJECTS_SCHEMA = {
    "type": "object",
    "properties": {
            "query": {
                "type": "string",
            }
    },
    "required": [
        "query",
    ]
}

GET_PROJECT_VERSIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "project_id": {
            "type": "string",
        }
    },
    "required": [
        "project_id",
    ]
}

DELETE_SAVED_PROJECT_SCHEMA = {
    "type": "object",
    "properties": {
            "id": {
                "type": "string",
            }
    },
    "required": [
        "id"
    ]
}

GET_PROJECT_CONFIG_SCHEMA = {
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

SAVE_PROJECT_SCHEMA = {
    "type": "object",
    "properties": {
            "project_id": {
                "type": ["string", "boolean"],
            },
        "diagram_data": {
                "type": ["string", "boolean"],
            },
        "version": {
                "type": ["string", "boolean"],
        },
        "config": {
                "type": ["string", "boolean"],
        }
    },
    "required": [
        "project_id",
        "diagram_data",
        "version",
        "config"
    ]
}

RENAME_PROJECT_SCHEMA = {
    "type": "object",
    "properties": {
            "project_id": {
                "type": "string"
            },
        "name": {
                "type": "string"
            }
    },
    "required": [
        "project_id",
        "name"
    ]
}

CREATE_PROJECT_SHORT_LINK_SCHEMA = {
    "type": "object",
    "properties": {
            "diagram_data": {
                "type": "object",
            }
    },
    "required": [
        "diagram_data"
    ]
}

GET_PROJECT_SHORT_LINK_SCHEMA = {
    "type": "object",
    "properties": {
            "project_short_link_id": {
                "type": "string",
            }
    },
    "required": [
        "project_short_link_id"
    ]
}

CREATE_GIT_REPO_SCHEMA = {
    "type": "object",
    "properties": {
        "git_repo_id": {
            "type": "string",
            "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        }
    },
    "required": [
        "git_repo_id"
    ]
}


