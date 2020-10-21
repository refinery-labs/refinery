from __future__ import annotations

import time
from uuid import uuid4

import botocore
from botocore.exceptions import ClientError
from typing import TYPE_CHECKING

from assistants.decorators import aws_exponential_backoff
from utils.general import logit
from utils.wrapped_aws_functions import api_gateway_create_rest_api, api_gateway_create_deployment, \
    api_gateway_create_resource, api_gateway_put_method, api_gateway_put_integration, \
    api_gateway_put_integration_response

if TYPE_CHECKING:
    from assistants.deployments.aws.api_endpoint import ApiEndpointWorkflowState


def create_rest_api(aws_client_factory, credentials, name, description, version):
    api_gateway_client = aws_client_factory.get_aws_client(
        "apigateway",
        credentials
    )

    response = api_gateway_create_rest_api(
        api_gateway_client,
        name=name,
        description=description,
        version=version,
        api_key_source="HEADER",
        endpoint_configuration={
            "types": [
                "EDGE",
            ]
        },
        binary_media_types=[
            "*/*"
        ],
        tags={
            "RefineryResource": "true"
        }
    )

    return response["id"]


def deploy_api_gateway_to_stage(aws_client_factory, credentials, rest_api_id, stage_name):
    api_gateway_client = aws_client_factory.get_aws_client(
        "apigateway",
        credentials
    )

    deployment_response = api_gateway_create_deployment(
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


def create_resource(aws_client_factory, credentials, rest_api_id, parent_id, path_part):
    api_gateway_client = aws_client_factory.get_aws_client(
        "apigateway",
        credentials
    )

    response = api_gateway_create_resource(
        api_gateway_client,
        rest_api_id,
        parent_id,
        path_part
    )

    return response["id"]


def create_method(aws_client_factory, credentials, method_name, rest_api_id, resource_id, http_method, api_key_required):
    api_gateway_client = aws_client_factory.get_aws_client(
        "apigateway",
        credentials
    )

    api_gateway_put_method(
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
        integration_response = api_gateway_put_integration(
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
        api_gateway_put_integration_response(
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
