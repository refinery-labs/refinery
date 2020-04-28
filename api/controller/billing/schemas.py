GET_BILLING_MONTH_TOTALS_SCHEMA = {
    "type": "object",
    "properties": {
            "billing_month": {
                "type": "string",
                "pattern": r"^\d\d\d\d\-\d\d$",
            }
    },
    "required": [
        "billing_month"
    ]
}

ADD_CREDIT_CARD_TOKEN_SCHEMA = {
    "type": "object",
    "properties": {
            "token": {
                "type": "string"
            }
    },
    "required": [
        "token"
    ]
}

DELETE_CREDIT_CARD_SCHEMA = {
    "type": "object",
    "properties": {
            "id": {
                "type": "string"
            }
    },
    "required": [
        "id"
    ]
}

MAKE_CREDIT_CARD_PRIMARY_SCHEMA = {
    "type": "object",
    "properties": {
            "id": {
                "type": "string"
            }
    },
    "required": [
        "id"
    ]
}
