SAVED_BLOCKS_CREATE_SCHEMA = {
	"type": "object",
	"properties": {
		"id": {
			"type": "string"
		},
		"description": {
			"type": "string"
		},
		"block_object": {
			"type": "object",
			"properties": {
				"name": {
					"type": "string",
				},
				"type": {
					"type": "string",
				}
			},
			"required": [
				"name",
				"type"
			]
		},
		"version": {
			"type": "integer",
		},
		"share_status": {
			"type": "string",
			"enum": [
				"PRIVATE",
				"PUBLISHED"
			]
		},
		"save_type": {
			"type": "string",
			"enum": [
				"FORK",
				"CREATE",
				"UPDATE"
			]
		},
		"shared_files": {
			"type": "array",
			"default": [],
		}
	},
	"required": [
		"block_object"
	]
}

SAVED_BLOCK_SEARCH_SCHEMA = {
	"type": "object",
	"properties": {
		"search_string": {
			"type": "string",
		},
		"share_status": {
			"type": "string",
			"enum": [
				"PRIVATE",
				"PUBLISHED"
			]
		},
		"language": {
			"type": "string",
		}
	},
	"required": [
		"search_string",
	]
}

SAVED_BLOCK_STATUS_CHECK_SCHEMA = {
	"type": "object",
	"properties": {
		"block_ids": {
			"type": "array",
			"items": {
				"type": "string"
			},
			"minItems": 1,
			"maxItems": 100
		}
	},
	"required": [
		"block_ids",
	]
}

SAVED_BLOCK_DELETE_SCHEMA = {
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

