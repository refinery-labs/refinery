from __future__ import annotations

import uuid

from tornado import gen
from typing import Dict, TYPE_CHECKING, List

from assistants.deployments.api_gateway import strip_api_gateway, ApiGatewayManager
from assistants.deployments.diagram.lambda_workflow_state import LambdaWorkflowState
from assistants.deployments.diagram.types import ApiGatewayDeploymentState, ApiGatewayEndpoint, ApiGatewayLambdaConfig
from assistants.deployments.diagram.utils import get_layers_for_lambda
from assistants.deployments.diagram.workflow_states import WorkflowState, StateTypes, DeploymentException
from utils.general import get_random_node_id, logit

if TYPE_CHECKING:
    from assistants.deployments.diagram.deploy_diagram import DeploymentDiagram
    from assistants.task_spawner.task_spawner_assistant import TaskSpawner


class MissingResourceException(Exception):
    pass


API_GATEWAY_STATE_NAME = "__api_gateway__"
API_GATEWAY_STATE_ARN = "API_GATEWAY"
API_GATEWAY_STAGE_NAME = "refinery"


class ApiGatewayWorkflowState(WorkflowState):
    def __init__(self, credentials):
        super(ApiGatewayWorkflowState, self).__init__(
            credentials,
            get_random_node_id(),
            API_GATEWAY_STATE_NAME,
            StateTypes.API_GATEWAY,
            arn=API_GATEWAY_STATE_ARN
        )

        self.project_id = ""

        # TODO is there a better way redeclare the type of a member variable?
        self.deployed_state: ApiGatewayDeploymentState = self.deployed_state
        self.current_state: ApiGatewayDeploymentState = self.current_state

    def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
        self.deployed_state = deploy_diagram.get_previous_api_gateway_state(API_GATEWAY_STATE_ARN)

        self.project_id = deploy_diagram.project_id

        # set the api gateway for this deployment since it already exists
        deploy_diagram.set_api_gateway(self)

    @property
    def api_gateway_id(self):
        """
        If the deployed state exists, then we return the api gateway id from there, otherwise we return
        the api gateway id we created in the current deployment.
        :return: api gateway id
        """
        return self.deployed_state.api_gateway_id \
            if self.deployed_state_exists() else self.current_state.api_gateway_id

    def serialize(self):
        ws_serialized = super(ApiGatewayWorkflowState, self).serialize()
        return {
            **ws_serialized,
            "rest_api_id": self.api_gateway_id
        }

    @gen.coroutine
    def get_api_gateway_deployment_state(self, api_gateway_manager: ApiGatewayManager):
        """
        For all resources that exist in this API Gateway, create an in-memory representation of them.

        API Gateway resources have {path, methods, integration (lambda arn)}. They are a nested structure
        that have children.

        :param api_gateway_manager:
        :return:
        """
        rest_resources = yield api_gateway_manager.get_resources(
            self._credentials,
            self.api_gateway_id
        )

        for resource_item in rest_resources:
            resource_id = resource_item["id"]
            resource_path = resource_item["path"]

            # A default resource is created along with an API gateway, we grab
            # it so we can make our base method
            if resource_path == "/":
                self.deployed_state.base_resource_id = resource_id
                continue

            resource_methods = {}
            if "resourceMethods" in resource_item:
                resource_methods = resource_item.get("resourceMethods")

            gateway_endpoint = ApiGatewayEndpoint(
                resource_item["id"],
                resource_item["path"]
            )
            for method, method_attributes in resource_methods.items():

                if "methodIntegration" not in method_attributes:
                    logit(
                        "Missing methodIntegration, Gateway ID: " + self.api_gateway_id
                        + " Resource: " + repr(resource_item),
                        "error"
                    )
                    # continue

                # Set the method as being used
                gateway_endpoint.set_method_in_use(method)

                # Get the linked lambda and add it to the list of configured lambdas
                linked_lambda_uri = method_attributes["methodIntegration"]["uri"]

                lambda_config = ApiGatewayLambdaConfig(method, resource_path)
                self.deployed_state.add_configured_lambda(linked_lambda_uri, lambda_config)

            # Create a map of paths to verify existence later
            # so we don't overwrite existing resources
            self.deployed_state.add_endpoint(gateway_endpoint)

        if self.deployed_state.base_resource_id is None:
            raise MissingResourceException("Missing API Gateway base resource ID. This should never happen")

        """ TODO don't think we need this since we only ever create one state 'refinery'
        rest_stages = yield api_gateway_manager.get_stages(
            self._credentials,
            self.api_gateway_id
        )

        self.deployed_state.stages = [rest_stage["stageName"] for rest_stage in rest_stages]
        """

    @gen.coroutine
    def setup_api_endpoints(self, task_spawner: TaskSpawner, api_gateway_manager, deployed_api_endpoints):
        for api_endpoint in deployed_api_endpoints:
            assert isinstance(api_endpoint, ApiEndpointWorkflowState)

            endpoint_is_configured = self.deployed_state.endpoint_is_configured(
                task_spawner, self._credentials, api_endpoint)

            creating_new_route = True
            if not api_endpoint.state_has_changed() \
                    and api_endpoint.deployed_state_exists() \
                    and endpoint_is_configured:

                logit(f"API Endpoint {api_endpoint.id} has not changed and exists, skipping setting up API route")

                creating_new_route = False

            yield api_endpoint.create_or_mark_lambda_api_route(
                task_spawner,
                self,
                creating_new_route
            )

        logit("Cleaning up unused API endpoints from API gateway...")
        yield self.deployed_state.remove_unused_resources(
            api_gateway_manager,
            self._credentials,
            self.api_gateway_id
        )

        logit("Now deploying API gateway to stage...")
        deploy_stage_results = yield task_spawner.deploy_api_gateway_to_stage(
            self._credentials,
            self.api_gateway_id,
            API_GATEWAY_STAGE_NAME
        )

    # TODO check deploy_stage_results?

    @gen.coroutine
    def predeploy(self, task_spawner, api_gateway_manager):
        if self.deployed_state.api_gateway_id is not None:
            logit("Verifying existence of API Gateway...")
            self.deployed_state.exists = yield api_gateway_manager.api_gateway_exists(
                self._credentials,
                self.deployed_state.api_gateway_id
            )

        # TODO when the api gateway id doesnt exists, we need to set it up again

        if self.deployed_state_exists():
            yield self.get_api_gateway_deployment_state(api_gateway_manager)

    @gen.coroutine
    def deploy(self, task_spawner, api_gateway_manager, project_id, project_config):
        # If we have a gateway id and the api gateway exists, we do not need to redeploy it
        if self.deployed_state.api_gateway_id is not None and self.deployed_state_exists():
            raise gen.Return()

        # We need to create an API gateway
        logit("Deploying API Gateway for API Endpoint(s)...")

        # We just generate a random ID for the API Gateway, no great other way to do it.
        # e.g. when you change the project name now it's hard to know what the API Gateway
        # is...
        formatted_uuid = str(uuid.uuid4()).replace('-', '')

        rest_api_name = f"Refinery-API-Gateway_{formatted_uuid}"

        gateway_id = yield task_spawner.create_rest_api(
            self._credentials,
            rest_api_name,
            "API Gateway created by Refinery. Associated with project ID " + self.project_id,
            "1.0.0"
        )
        self.current_state.api_gateway_id = gateway_id

        yield self.get_api_gateway_deployment_state(api_gateway_manager)


class ApiEndpointWorkflowState(LambdaWorkflowState):
    def __init__(self, *args, **kwargs):
        super(ApiEndpointWorkflowState, self).__init__(*args, **kwargs)

        self.http_method = None
        self.api_path = None
        self.url = None
        self.rest_api_id = None

        lambda_layers = get_layers_for_lambda("python2.7")

        self.language = "python2.7"
        self.code = ""
        self.libraries = []
        self.max_execution_time = 30
        self.memory = 512
        self.execution_mode = "API_ENDPOINT",
        self.layers = lambda_layers
        self.reserved_concurrency_count = False
        self.is_inline_execution = False
        self.shared_files_list = []

    def serialize(self):
        serialized_ws_state = WorkflowState.serialize(self)
        return {
            **serialized_ws_state,
            "url": self.url,
            "rest_api_id": self.rest_api_id,
            "http_method": self.http_method,
            "api_path": self.api_path,
            "state_hash": self.current_state.state_hash
        }

    def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
        super(LambdaWorkflowState, self).setup(deploy_diagram, workflow_state_json)

        self.http_method = workflow_state_json["http_method"]
        self.api_path = workflow_state_json["api_path"]

        self.execution_pipeline_id = deploy_diagram.project_id
        self.execution_log_level = deploy_diagram.project_config["logging"]["level"]
        self.execution_mode = "API_ENDPOINT"

        self._set_environment_variables_for_lambda({})

    def set_api_url(self, api_gateway_id):
        self.rest_api_id = api_gateway_id
        region = self._credentials["region"]
        api_path = self.api_path
        self.url = f"https://{api_gateway_id}.execute-api.{region}.amazonaws.com/refinery{api_path}"

    def get_lambda_uri(self, api_version):
        region = self._credentials["region"]
        account_id = self._credentials["account_id"]
        return f"arn:aws:apigateway:{region}:lambda:path/{api_version}/functions/arn:aws:lambda:{region}:" + \
               f"{account_id}:function:{self.name}/invocations"

    def get_source_arn(self, rest_api_id: str):
        region = self._credentials["region"]
        account_id = self._credentials["account_id"]

        # For AWS Lambda you need to add a permission to the Lambda function itself
        # via the add_permission API call to allow invocation via the CloudWatch event.
        return f"arn:aws:execute-api:{region}:{account_id}:{rest_api_id}/*/{self.http_method}{self.api_path}"

    @gen.coroutine
    def create_or_mark_lambda_api_route(self, task_spawner, api_gateway: ApiGatewayWorkflowState, creating_new_route):

        #
        # TODO clean up this method, it is too long
        #

        logit(f"Setting up route {self.http_method} {self.api_path} for API Endpoint '{self.name}'...")

        path_parts = self.api_path.split("/")
        path_parts = list(filter(lambda s: s != '', path_parts))

        if creating_new_route:
            # First we clean the Lambda of API Gateway policies which point
            # to dead API Gateways
            yield task_spawner.clean_lambda_iam_policies(
                self._credentials,
                self.name
            )

        # Set the pointer to the base
        current_base_pointer_id = api_gateway.deployed_state.base_resource_id

        # Path level, continuously updated
        current_path = ""

        # Create entire path from chain
        for path_part in path_parts:
            """
            TODO: Check for conflicting resources and don't
            overwrite an existing resource if it exists already.
            """
            # Check if there's a conflicting resource here
            current_path += "/" + path_part

            # Get existing resource ID instead of creating one
            api_endpoint = api_gateway.deployed_state.get_endpoint_from_path(current_path)
            if api_endpoint is not None:
                # The current endpoint we are looking at is in the path of what we are searching for
                # so we will want to keep it
                api_endpoint.set_endpoint_in_use()

                current_base_pointer_id = api_endpoint.id
            else:
                if not creating_new_route:
                    raise DeploymentException(
                        self.id, self.name, self.type, False, f"Expected this endpoint {current_path} to exist, but it is missing")

                # Otherwise go ahead and create one
                new_resource_id = yield task_spawner.create_resource(
                    self._credentials,
                    api_gateway.api_gateway_id,
                    current_base_pointer_id,
                    path_part
                )
                current_base_pointer_id = new_resource_id

                # Create a new api endpoint resource and add it to our deployed state
                api_endpoint = ApiGatewayEndpoint(
                    current_base_pointer_id, current_path)
                api_endpoint.set_endpoint_in_use()
                api_gateway.deployed_state.add_endpoint(api_endpoint)

            # Mark this retrieved endpoint as one that is in use
            api_endpoint.set_method_in_use(self.http_method)

        if creating_new_route:
            # Create method on base resource
            method_response = yield task_spawner.create_method(
                self._credentials,
                "HTTP Method",
                api_gateway.api_gateway_id,
                current_base_pointer_id,
                self.http_method,
                False,
            )

            # Link the API Gateway to the lambda
            link_response = yield task_spawner.link_api_method_to_lambda(
                self._credentials,
                api_gateway.api_gateway_id,
                current_base_pointer_id,
                self
            )

    def deploy(self, task_spawner, project_id, project_config):
        logit(f"Deploying API Endpoint '{self.name}'...")

        # TODO move this to predeploy
        self.execution_pipeline_id = project_id,
        self.execution_log_level = project_config["logging"]["level"]

        # TODO we also might want to check the api gateway to prove that the routes are also still setup?

        state_changed = self.state_has_changed()
        if not state_changed and self.deployed_state.exists:
            logit(f"{self.name} has not changed and is currently deployed, not redeploying")
            return None

        return self.deploy_lambda(task_spawner)


class ApiGatewayResponseWorkflowState(WorkflowState):
    pass
