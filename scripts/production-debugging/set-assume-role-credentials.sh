#!/bin/bash
ALL_CREDS_JSON=$(curl -H "X-Service-Secret: $SECRET_KEY" https://app.refinery.io/services/v1/assume_role_credentials/380475238443)

export AWS_ACCESS_KEY_ID=$(echo "$ALL_CREDS_JSON" | jq .access_key_id)
export AWS_SESSION_TOKEN=$(echo "$ALL_CREDS_JSON" | jq .session_token)
export AWS_SECRET_ACCESS_KEY=$(echo "$ALL_CREDS_JSON" | jq .secret_access_key)

echo "Set key with ID: $AWS_ACCESS_KEY_ID"

