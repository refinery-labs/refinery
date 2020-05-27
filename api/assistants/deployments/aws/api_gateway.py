from __future__ import annotations

import uuid

from tornado import gen
from typing import Dict, TYPE_CHECKING

from assistants.deployments.api_gateway import ApiGatewayManager
from assistants.deployments.diagram.types import ApiGatewayDeploymentState, ApiGatewayEndpoint, ApiGatewayLambdaConfig
from assistants.deployments.diagram.workflow_states import WorkflowState, StateTypes
from utils.general import get_random_node_id, logit

API_GATEWAY_STATE_NAME = "__api_gateway__"
API_GATEWAY_STATE_ARN = "API_GATEWAY"
API_GATEWAY_STAGE_NAME = "refinery"

if TYPE_CHECKING:
    from assistants.deployments.diagram.deploy_diagram import DeploymentDiagram
    from assistants.task_spawner.task_spawner_assistant import TaskSpawner


class MissingResourceException(Exception):
    pass


class ApiGatewayResponseWorkflowState(WorkflowState):
    pass


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
