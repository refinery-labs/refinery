from __future__ import annotations

import time
from uuid import uuid4

import botocore
from botocore.exceptions import ClientError
from typing import TYPE_CHECKING

from assistants.decorators import aws_exponential_backoff
from assistants.deployments.aws_workflow_manager import api_endpoint
from utils.general import logit

if TYPE_CHECKING:
    from assistants.deployments.aws.api_endpoint import ApiEndpointWorkflowState


def create_rest_api(aws_client_factory, credentials, name, description, version):
    api_gateway_client = aws_client_factory.get_aws_client(
        "apigateway",
        credentials
    )

    attempts = 0
    response = None
    while attempts < 5:
        try:
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
            break

        except botocore.exceptions.ClientError as err:
            response = err.response
            if response and response.get("Error", {}).get("Code") == "TooManyRequestsException":
                logit("TooManyRequestsException when trying to deploy the api gateway")
                # we are calling the api too fast, let's try sleeping for a bit and trying again
                time.sleep(1)
                attempts += 1

    return response["id"]


@aws_exponential_backoff()
def try_deploy_api_gateway_to_stage(api_gateway_client, rest_api_id, stage_name):
    return api_gateway_client.create_deployment(
        restApiId=rest_api_id,
        stageName=stage_name,
        stageDescription="API Gateway deployment deployed via refinery",
        description="API Gateway deployment deployed via refinery"
    )


def deploy_api_gateway_to_stage(aws_client_factory, credentials, rest_api_id, stage_name):
    api_gateway_client = aws_client_factory.get_aws_client(
        "apigateway",
        credentials
    )

    deployment_response = try_deploy_api_gateway_to_stage(
        api_gateway_client,
        rest_api_id,
        stage_name
    )

    deployment_id = deployment_response["id"]

    return {
        "id": rest_api_id,
        "stage_name": stage_name,
        "deployment_id": deployment_id,
    }


@aws_exponential_backoff()
def try_to_create_resource(api_gateway_client, rest_api_id, parent_id, path_part):
    return api_gateway_client.create_resource(
        restApiId=rest_api_id,
        parentId=parent_id,
        pathPart=path_part
    )


def create_resource(aws_client_factory, credentials, rest_api_id, parent_id, path_part):
    api_gateway_client = aws_client_factory.get_aws_client(
        "apigateway",
        credentials
    )

    response = try_to_create_resource(
        api_gateway_client,
        rest_api_id,
        parent_id,
        path_part
    )

    return response["id"]


@aws_exponential_backoff(max_attempts=10)
def try_to_create_method(api_gateway_client, rest_api_id, resource_id, http_method, api_key_required, method_name):
    return api_gateway_client.put_method(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod=http_method,
        authorizationType="NONE",
        apiKeyRequired=api_key_required,
        operationName=method_name,
    )


def create_method(aws_client_factory, credentials, method_name, rest_api_id, resource_id, http_method, api_key_required):
    api_gateway_client = aws_client_factory.get_aws_client(
        "apigateway",
        credentials
    )

    try_to_create_method(
        api_gateway_client,
        rest_api_id,
        resource_id,
        http_method,
        api_key_required,
        method_name
    )

    return {
        "method_name": method_name,
        "rest_api_id": rest_api_id,
        "resource_id": resource_id,
        "http_method": http_method,
        "api_key_required": api_key_required,
    }


def get_lambda_uri_for_api_method(aws_client_factory, credentials, api_endpoint: ApiEndpointWorkflowState):
    lambda_client = aws_client_factory.get_aws_client(
        "lambda",
        credentials
    )

    api_version = lambda_client.meta.service_model.api_version
    return api_endpoint.get_lambda_uri(api_version)


@aws_exponential_backoff(max_attempts=10)
def try_to_put_api_integration(api_gateway_client, rest_api_id, resource_id, api_endpoint: ApiEndpointWorkflowState, lambda_uri):
    return api_gateway_client.put_integration(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod=api_endpoint.http_method,
        type="AWS_PROXY",
        # MUST be POST: https://github.com/boto/boto3/issues/572#issuecomment-239294381
        integrationHttpMethod="POST",
        uri=lambda_uri,
        connectionType="INTERNET",
        timeoutInMillis=29000  # 29 seconds
    )


@aws_exponential_backoff(max_attempts=10)
def try_to_put_http_api_integration(api_gateway_client, rest_api_id, resource_id, api_endpoint: ApiEndpointWorkflowState, http_url):
    return api_gateway_client.put_integration(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod=api_endpoint.http_method,
        type="HTTP_PROXY",
        integrationHttpMethod=api_endpoint.http_method,
        uri=http_url,
        connectionType="INTERNET",
        timeoutInMillis=29000  # 29 seconds
    )


@aws_exponential_backoff(max_attempts=10)
def try_to_put_integration_response(api_gateway_client, rest_api_id, resource_id, api_endpoint):
    return api_gateway_client.put_integration_response(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod=api_endpoint.http_method,
        statusCode="200",
        contentHandling="CONVERT_TO_TEXT"
    )


def link_api_method_to_lambda(aws_client_factory, credentials, rest_api_id, resource_id, api_endpoint: ApiEndpointWorkflowState):
    api_gateway_client = aws_client_factory.get_aws_client(
        "apigateway",
        credentials
    )

    lambda_client = aws_client_factory.get_aws_client(
        "lambda",
        credentials
    )

    api_version = lambda_client.meta.service_model.api_version
    lambda_uri = api_endpoint.get_lambda_uri(api_version)

    try:
        integration_response = try_to_put_api_integration(
            api_gateway_client,
            rest_api_id,
            resource_id,
            api_endpoint,
            lambda_uri
        )
    except ClientError as e:
        raise Exception(f"Unable to set integration {rest_api_id} {resource_id} for lambda {lambda_uri}: {str(e)}")

    source_arn = api_endpoint.get_source_arn(rest_api_id)

    # We have to clean previous policies we added from this Lambda
    # Scan over all policies and delete any which aren't associated with
    # API Gateways that actually exist!

    lambda_permission_add_response = lambda_client.add_permission(
        FunctionName=api_endpoint.name,
        StatementId=str(uuid4()).replace("_", "") + "_statement",
        Action="lambda:*",
        Principal="apigateway.amazonaws.com",
        SourceArn=source_arn
    )

    # Clown-shoes AWS bullshit for binary response
    try:
        try_to_put_integration_response(
            api_gateway_client,
            rest_api_id,
            resource_id,
            api_endpoint
        )
    except ClientError as e:
        raise Exception(f"Unable to set integration response {rest_api_id} {resource_id} for lambda {lambda_uri}: {str(e)}")

    return {
        "api_gateway_id": rest_api_id,
        "resource_id": resource_id,
        "http_method": api_endpoint.http_method,
        "lambda_name": api_endpoint.name,
        "type": integration_response["type"],
        "arn": integration_response["uri"],
        "statement": lambda_permission_add_response["Statement"]
    }


def link_api_method_to_workflow(aws_client_factory, credentials, rest_api_id, resource_id, api_endpoint: api_endpoint.ApiEndpointWorkflowState):
    api_gateway_client = aws_client_factory.get_aws_client(
        "apigateway",
        credentials
    )

    try:
        integration_response = try_to_put_http_api_integration(
            api_gateway_client,
            rest_api_id,
            resource_id,
            api_endpoint,
            api_endpoint._workflow_manager_invoke_url
        )
    except ClientError as e:
        raise Exception(f"Unable to set integration {rest_api_id} {resource_id} for url {api_endpoint._workflow_manager_invoke_url}: {str(e)}")

    # Clown-shoes AWS bullshit for binary response
    try:
        try_to_put_integration_response(
            api_gateway_client,
            rest_api_id,
            resource_id,
            api_endpoint
        )
    except ClientError as e:
        raise Exception(f"Unable to set integration response {rest_api_id} {resource_id} for ur {api_endpoint._workflow_manager_invoke_url}: {str(e)}")
