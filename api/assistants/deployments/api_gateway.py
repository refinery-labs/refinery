import pinject
import tornado
import botocore.exceptions

from utils.general import get_random_node_id, log_exception

from tornado.concurrent import run_on_executor, futures
from utils.general import logit
from tornado import gen

from botocore.exceptions import ClientError

from utils.performance_decorators import emit_runtime_metrics


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
    return_data = {
        "deleted": True,
        "type": "api_gateway",
        "id": get_random_node_id(),
        "arn": "arn:aws:apigateway:" + credentials["region"] + "::/restapis/" + api_gateway_id,
        "name": "__api_gateway__",
    }

    # Verify the existance of API Gateway before proceeding
    logit("Verifying existance of API Gateway...")
    api_gateway_exists = yield api_gateway_manager.api_gateway_exists(
        credentials,
        api_gateway_id
    )

    # If it doesn't exist we can stop here - there's nothing
    # to strip!
    if not api_gateway_exists:
        raise gen.Return(return_data)

    rest_resources = yield api_gateway_manager.get_resources(
        credentials,
        api_gateway_id
    )

    # List of futures to finish before we continue
    deletion_futures = []

    # Iterate over resources and delete everything that
    # can be deleted.
    for resource_item in rest_resources:
        # TODO there is a race here where the api resource _could_ be deleted
        # before the method is deleted, does that matter?

        # Delete the methods
        if "resourceMethods" in resource_item:
            for http_method, values in resource_item["resourceMethods"].items():
                deletion_futures.append(
                    api_gateway_manager.delete_rest_api_resource_method(
                        credentials,
                        api_gateway_id,
                        resource_item["id"],
                        http_method
                    )
                )
        # We can't delete the root resource
        if resource_item["path"] != "/":
            deletion_futures.append(
                api_gateway_manager.delete_rest_api_resource(
                    credentials,
                    api_gateway_id,
                    resource_item["id"]
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

    raise gen.Return(return_data)


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
                logit("API Gateway " + api_gateway_id + " appears to have been deleted or no longer exists!")
                return False

        return True

    @run_on_executor
    @emit_runtime_metrics("api_gateway__get_resources")
    def get_resources(self, credentials, rest_api_id):
        api_gateway_client = self.aws_client_factory.get_aws_client(
            "apigateway",
            credentials
        )

        response = api_gateway_client.get_resources(
            restApiId=rest_api_id,
            limit=500
        )

        return response["items"]

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
