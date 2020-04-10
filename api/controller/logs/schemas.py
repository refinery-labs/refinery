GET_PROJECT_EXECUTION_LOG_OBJECT_SCHEMAS = {
	"type": "object",
	"properties": {
		"logs_to_fetch": {
			"type": "array",
			"items": {
				"type": "object",
				"properties": {
					"s3_key": {
						"type": "string"
					},
					"log_id": {
						"type": "string"
					}
				},
				"required": ["s3_key", "log_id"]
			},
			"minItems": 1,
			"maxItems": 50
		}
	},
	"required": [
		"logs_to_fetch"
	]
}

GET_PROJECT_EXECUTION_LOGS_SCHEMA = {
	"type": "object",
	"properties": {
		"execution_pipeline_id": {
			"type": "string",
		},
		"arn": {
			"type": "string",
		},
		"project_id": {
			"type": "string",
		},
		"oldest_timestamp": {
			"type": "integer"
		}
	},
	"required": [
		"arn",
		"execution_pipeline_id",
		"project_id",
		"oldest_timestamp"
	]
}

GET_PROJECT_EXECUTION_LOGS_PAGE_SCHEMA = {
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

GET_PROJECT_EXECUTIONS_SCHEMA = {
	"type": "object",
	"properties": {
		"project_id": {
			"type": "string",
		},
		"oldest_timestamp": {
			"type": "integer"
		}
	},
	"required": [
		"project_id",
		"oldest_timestamp"
	]
}

