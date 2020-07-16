from __future__ import annotations

import pinject
import tornado
import botocore.exceptions
from typing import TYPE_CHECKING, List

from assistants.deployments.aws.api_gateway_types import ApiGatewayEndpoint, ApiGatewayLambdaConfig
from utils.general import log_exception

from tornado.concurrent import run_on_executor, futures
from utils.general import logit
from tornado import gen

from botocore.exceptions import ClientError

from utils.performance_decorators import emit_runtime_metrics

if TYPE_CHECKING:
    from assistants.deployments.aws.api_gateway import ApiGatewayWorkflowState

@gen.coroutine
@log_exception
def strip_api_gateway(api_gateway_manager, credentials, api_gateway_id):
    """
    Strip a given API Gateway of all of it's:
    * Resources
    * Resource Methods
    * Stages

    Allowing for the configuration details to be replaced.
    """
    # Verify the existance of API Gateway before proceeding
    logit("Verifying existance of API Gateway...")
    api_gateway_exists = yield api_gateway_manager.api_gateway_exists(
        credentials,
        api_gateway_id
    )

    # If it doesn't exist we can stop here - there's nothing
    # to strip!
    if not api_gateway_exists:
        raise gen.Return()

    rest_resources = yield api_gateway_manager.get_resources(
        credentials,
        api_gateway_id
    )

    lambda_configs: List[ApiGatewayLambdaConfig] = rest_resources["lambda_configs"]

    # List of futures to finish before we continue
    deletion_futures = []

    # Iterate over resources and delete everything that
    # can be deleted.
    for lambda_config in lambda_configs:
        # TODO there is a race here where the api resource _could_ be deleted before the method is deleted, does that matter?

        # Delete the methods
        deletion_futures.append(
            api_gateway_manager.delete_rest_api_resource_method(
                credentials,
                api_gateway_id,
                lambda_config.resource_id,
                lambda_config.method
            )
        )

        # We can't delete the root resource
        if lambda_config.path != "/":
            deletion_futures.append(
                api_gateway_manager.delete_rest_api_resource(
                    credentials,
                    api_gateway_id,
                    lambda_config.resource_id
                )
            )

    rest_stages = yield api_gateway_manager.get_stages(
        credentials,
        api_gateway_id
    )

    for rest_stage in rest_stages:
        deletion_futures.append(
            api_gateway_manager.delete_stage(
                credentials,
                api_gateway_id,
                rest_stage["stageName"]
            )
        )

    yield deletion_futures

    raise gen.Return()


def parse_api_gateway_resource_methods(gateway_endpoint, resource_id, resource_path, resource_methods):
    lambda_configs = []
    for method, method_attributes in resource_methods.items():
        # Set the method as being used
        gateway_endpoint.set_method_in_use(method)

        # Get the linked lambda and add it to the list of configured lambdas
        method_integration = method_attributes.get("methodIntegration")
        if method_integration is None:
            continue

        linked_lambda_uri = method_integration["uri"]

        lambda_config = ApiGatewayLambdaConfig(resource_id, linked_lambda_uri, method, resource_path)
        lambda_configs.append(lambda_config)

    return lambda_configs


class ApiGatewayManager(object):
    aws_client_factory = None
    aws_cloudwatch_client = None
    logger = None

    # noinspection PyUnresolvedReferences
    @pinject.copy_args_to_public_fields
    def __init__(self, aws_client_factory, aws_cloudwatch_client, logger, loop=None):
        self.executor = futures.ThreadPoolExecutor(10)
        self.loop = loop or tornado.ioloop.IOLoop.current()

    @run_on_executor
    @emit_runtime_metrics("api_gateway__api_gateway_exists")
    def api_gateway_exists(self, credentials, api_gateway_id):
        api_gateway_client = self.aws_client_factory.get_aws_client(
            "apigateway",
            credentials
        )
        try:
            api_gateway_data = api_gateway_client.get_rest_api(
                restApiId=api_gateway_id,
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "NotFoundException":
                logit(f"API Gateway {api_gateway_id} appears to have been deleted or no longer exists!")
                return False

        return True

    @run_on_executor
    @emit_runtime_metrics("api_gateway__get_resources")
    def get_resources(self, credentials, rest_api_id):
        """
        For all resources that exist in this API Gateway, create an in-memory representation of them.

        API Gateway resources have {path, methods, integration (lambda arn)}. They are a nested structure
        that have children.

        :param credentials:
        :param rest_api_id:
        :param api_gateway:
        :return:
        """

        api_gateway_client = self.aws_client_factory.get_aws_client(
            "apigateway",
            credentials
        )

        response = api_gateway_client.get_resources(
            restApiId=rest_api_id,
            limit=500,
            embed=[
                "methods"
            ]
        )

        gateway_endpoints = []
        lambda_configs = []
        base_resource_id = None

        items = response["items"]
        for item in items:
            resource_id = item["id"]
            resource_path = item["path"]

            # A default resource is created along with an API gateway, we grab
            # it so we can make our base method
            if resource_path == "/":
                base_resource_id = resource_id
                continue

            resource_methods = {}
            if "resourceMethods" in item:
                resource_methods = item.get("resourceMethods")

            gateway_endpoint = ApiGatewayEndpoint(
                resource_id,
                resource_path
            )

            resource_lambda_configs = parse_api_gateway_resource_methods(
                gateway_endpoint,
                resource_id,
                resource_path,
                resource_methods
            )
            lambda_configs.extend(resource_lambda_configs)

            gateway_endpoints.append(gateway_endpoint)

        return dict(
            base_resource_id=base_resource_id,
            gateway_endpoints=gateway_endpoints,
            lambda_configs=lambda_configs
        )

    @run_on_executor
    @emit_runtime_metrics("api_gateway__get_stages")
    def get_stages(self, credentials, rest_api_id):
        api_gateway_client = self.aws_client_factory.get_aws_client(
            "apigateway",
            credentials
        )

        response = api_gateway_client.get_stages(
            restApiId=rest_api_id
        )

        return response["item"]

    @run_on_executor
    @emit_runtime_metrics("api_gateway__delete_rest_api")
    def delete_rest_api(self, credentials, rest_api_id):
        api_gateway_client = self.aws_client_factory.get_aws_client(
            "apigateway",
            credentials
        )

        try:
            response = api_gateway_client.delete_rest_api(
                restApiId=rest_api_id,
            )
        except botocore.exceptions.ClientError as boto_error:
            # If it's not an NotFoundException exception it's not what we except so we re-raise
            if boto_error.response["Error"]["Code"] != "NotFoundException":
                raise

        return {
            "id": rest_api_id,
        }

    @run_on_executor
    @emit_runtime_metrics("api_gateway__delete_rest_api_resource")
    def delete_rest_api_resource(self, credentials, rest_api_id, resource_id):
        api_gateway_client = self.aws_client_factory.get_aws_client(
            "apigateway",
            credentials
        )

        try:
            response = api_gateway_client.delete_resource(
                restApiId=rest_api_id,
                resourceId=resource_id,
            )
        except botocore.exceptions.ClientError as boto_error:
            # If it's not an NotFoundException exception it's not what we except so we re-raise
            if boto_error.response["Error"]["Code"] != "NotFoundException":
                raise

        return {
            "rest_api_id": rest_api_id,
            "resource_id": resource_id
        }

    @run_on_executor
    @emit_runtime_metrics("api_gateway__delete_rest_api_resource_method")
    def delete_rest_api_resource_method(self, credentials, rest_api_id, resource_id, method):
        api_gateway_client = self.aws_client_factory.get_aws_client(
            "apigateway",
            credentials
        )

        try:
            response = api_gateway_client.delete_method(
                restApiId=rest_api_id,
                resourceId=resource_id,
                httpMethod=method,
            )
        except Exception as e:
            logit(f"Exception occurred while deleting {resource_id} in {rest_api_id}, method '{method}'! Exception: {e}")
            pass

        return {
            "rest_api_id": rest_api_id,
            "resource_id": resource_id,
            "method": method
        }

    @run_on_executor
    @emit_runtime_metrics("api_gateway__delete_stage")
    def delete_stage(self, credentials, rest_api_id, stage_name):
        api_gateway_client = self.aws_client_factory.get_aws_client(
            "apigateway",
            credentials
        )

        response = api_gateway_client.delete_stage(
            restApiId=rest_api_id,
            stageName=stage_name
        )

        return {
            "rest_api_id": rest_api_id,
            "stage_name": stage_name
        }
