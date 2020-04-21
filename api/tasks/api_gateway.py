def create_rest_api(aws_client_factory, credentials, name, description, version):
    api_gateway_client = aws_client_factory.get_aws_client(
        "apigateway",
        credentials
    )

    response = api_gateway_client.create_rest_api(
        name=name,
        description=description,
        version=version,
        apiKeySource="HEADER",
        endpointConfiguration={
            "types": [
                "EDGE",
            ]
        },
        binaryMediaTypes=[
            "*/*"
        ],
        tags={
            "RefineryResource": "true"
        }
    )

    return {
        "id": response["id"],
        "name": response["name"],
        "description": response["description"],
        "version": response["version"]
    }


def deploy_api_gateway_to_stage(aws_client_factory, credentials, rest_api_id, stage_name):
    api_gateway_client = aws_client_factory.get_aws_client(
        "apigateway",
        credentials
    )

    deployment_response = api_gateway_client.create_deployment(
        restApiId=rest_api_id,
        stageName=stage_name,
        stageDescription="API Gateway deployment deployed via refinery",
        description="API Gateway deployment deployed via refinery"
    )

    deployment_id = deployment_response["id"]

    return {
        "id": rest_api_id,
        "stage_name": stage_name,
        "deployment_id": deployment_id,
    }


def create_resource(aws_client_factory, credentials, rest_api_id, parent_id, path_part):
    api_gateway_client = aws_client_factory.get_aws_client(
        "apigateway",
        credentials
    )

    response = api_gateway_client.create_resource(
        restApiId=rest_api_id,
        parentId=parent_id,
        pathPart=path_part
    )

    return {
        "id": response["id"],
        "api_gateway_id": rest_api_id,
        "parent_id": parent_id,
    }

def create_method(aws_client_factory, credentials, method_name, rest_api_id, resource_id, http_method, api_key_required):
    api_gateway_client = aws_client_factory.get_aws_client(
        "apigateway",
        credentials
    )

    response = api_gateway_client.put_method(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod=http_method,
        authorizationType="NONE",
        apiKeyRequired=api_key_required,
        operationName=method_name,
    )

    return {
        "method_name": method_name,
        "rest_api_id": rest_api_id,
        "resource_id": resource_id,
        "http_method": http_method,
        "api_key_required": api_key_required,
    }


def add_integration_response(aws_client_factory, credentials, rest_api_id, resource_id, http_method, lambda_name):
    api_gateway_client = aws_client_factory.get_aws_client(
        "apigateway",
        credentials
    )
    response = api_gateway_client.put_integration_response(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod=http_method,
        statusCode="200",
        contentHandling="CONVERT_TO_TEXT"
    )


def link_api_method_to_lambda(aws_client_factory, credentials, rest_api_id, resource_id, http_method, api_path, lambda_name):
    api_gateway_client = aws_client_factory.get_aws_client(
        "apigateway",
        credentials
    )

    lambda_client = aws_client_factory.get_aws_client(
        "lambda",
        credentials
    )

    lambda_uri = "arn:aws:apigateway:" + credentials["region"] + ":lambda:path/" + lambda_client.meta.service_model.api_version + \
        "/functions/arn:aws:lambda:" + credentials["region"] + ":" + str(
            credentials["account_id"]) + ":function:" + lambda_name + "/invocations"

    integration_response = api_gateway_client.put_integration(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod=http_method,
        type="AWS_PROXY",
        # MUST be POST: https://github.com/boto/boto3/issues/572#issuecomment-239294381
        integrationHttpMethod="POST",
        uri=lambda_uri,
        connectionType="INTERNET",
        timeoutInMillis=29000  # 29 seconds
    )

    """
    For AWS Lambda you need to add a permission to the Lambda function itself
    via the add_permission API call to allow invocation via the CloudWatch event.
    """
    source_arn = "arn:aws:execute-api:" + credentials["region"] + ":" + str(
        credentials["account_id"]) + ":" + rest_api_id + "/*/" + http_method + api_path

    # We have to clean previous policies we added from this Lambda
    # Scan over all policies and delete any which aren't associated with
    # API Gateways that actually exist!

    lambda_permission_add_response = lambda_client.add_permission(
        FunctionName=lambda_name,
        StatementId=str(uuid.uuid4()).replace("_", "") + "_statement",
        Action="lambda:*",
        Principal="apigateway.amazonaws.com",
        SourceArn=source_arn
    )

    return {
        "api_gateway_id": rest_api_id,
        "resource_id": resource_id,
        "http_method": http_method,
        "lambda_name": lambda_name,
        "type": integration_response["type"],
        "arn": integration_response["uri"],
        "statement": lambda_permission_add_response["Statement"]
    }
