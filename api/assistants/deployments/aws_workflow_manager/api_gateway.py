from __future__ import annotations

from botocore.exceptions import ClientError
from tornado import gen, locks
from typing import Dict, TYPE_CHECKING, List

from assistants.deployments.api_gateway import ApiGatewayManager
from assistants.deployments.aws_workflow_manager.api_endpoint import ApiEndpointWorkflowState
from assistants.deployments.aws_workflow_manager.aws_workflow_state import AwsWorkflowState
from assistants.deployments.aws_workflow_manager.types import AwsDeploymentState
from assistants.deployments.diagram.workflow_states import StateTypes
from utils.general import logit
from assistants.deployments.aws_workflow_manager.api_gateway_types import ApiGatewayEndpoint, ApiGatewayLambdaConfig

API_GATEWAY_STATE_NAME = "__api_gateway__"
API_GATEWAY_STATE_ARN = "API_GATEWAY"
API_GATEWAY_STAGE_NAME = "refinery"

if TYPE_CHECKING:
    from assistants.deployments.aws_workflow_manager.aws_deployment import AwsDeployment
    from assistants.task_spawner.task_spawner_assistant import TaskSpawner


class MissingResourceException(Exception):
    pass


class ApiGatewayResponseWorkflowState(AwsWorkflowState):
    pass


class ApiGatewayDeploymentState(AwsDeploymentState):
    """
    ApiGatewayDeploymentState holds the deployed state attributes of the project's api gateway.
    """

    def __init__(self, name, state_type, state_hash, arn, api_gateway_id):
        super().__init__(name, state_type, state_hash, arn)

        self.api_gateway_id = api_gateway_id

        self.base_resource_id = None
        self.stages = []
        self._path_existence_map: Dict[str, ApiGatewayEndpoint] = {}
        self._configured_lambdas: Dict[str, ApiGatewayLambdaConfig] = {}

    def add_endpoint(self, api_endpoint: ApiGatewayEndpoint):
        """
        Add an endpoint to the gateway's deployed state.

        :param api_endpoint:
        :return:
        """
        self._path_existence_map[api_endpoint.path] = api_endpoint

    def add_configured_lambda(self, lambda_uri, lambda_config):
        """
        Add a lambda integration to the gateway's deployed state.

        :param lambda_uri:
        :param lambda_config:
        :return:
        """
        self._configured_lambdas[lambda_uri] = lambda_config

    def get_endpoint_from_path(self, path: str) -> ApiGatewayEndpoint:
        """
        Lookup a deployed endpoint in the gateway by path.

        :param path:
        :return:
        """
        return self._path_existence_map.get(path)

    @gen.coroutine
    def remove_unused_resources(self, api_gateway_manager, credentials, api_gateway_id):
        """
        Remove any deployed resources which have not been marked as "in use" when deploying
        the current project.

        :param api_gateway_manager:
        :param credentials:
        :param api_gateway_id:
        :return:
        """

        deletion_futures = []
        for api_endpoint in self._path_existence_map.values():
            methods = api_endpoint.get_methods_to_be_removed()
            for method in methods:
                future = api_gateway_manager.delete_rest_api_resource_method(
                    credentials,
                    api_gateway_id,
                    api_endpoint.id,
                    method
                )
                deletion_futures.append(future)

            if api_endpoint.endpoint_can_be_removed():
                future = api_gateway_manager.delete_rest_api_resource(
                    credentials,
                    api_gateway_id,
                    api_endpoint.id
                )
                deletion_futures.append(future)

        yield deletion_futures

    def endpoint_is_configured(self, task_spawner, credentials, api_endpoint: ApiEndpointWorkflowState) -> bool:
        """
        Lookup the gateway method integration and compare it against the expected API endpoint workflow state.

        :param task_spawner:
        :param credentials:
        :param api_endpoint:
        :return:
        """

        lambda_uri = task_spawner.get_lambda_uri_for_api_method(credentials, api_endpoint)

        configured_lambda = self._configured_lambdas.get(lambda_uri)
        if configured_lambda is None:
            return False

        return configured_lambda.matches_expected_state(api_endpoint)

    def __str__(self):
        return f'Api Gateway Deployment State arn: {self.arn}, state_hash: {self.state_hash}, exists: {self.exists}, api gateway id: {self.api_gateway_id}'


class ApiGatewayWorkflowState(AwsWorkflowState):
    def __init__(self, credentials):
        super().__init__(
            credentials,

            # we will set the id during setup
            '',

            API_GATEWAY_STATE_NAME,
            StateTypes.API_GATEWAY,
            API_GATEWAY_STATE_ARN
        )

        # TODO is there a better way redeclare the type of a member variable?
        self.deployed_state: ApiGatewayDeploymentState = self.deployed_state
        self.current_state: ApiGatewayDeploymentState = ApiGatewayDeploymentState(self.name, StateTypes.API_GATEWAY, None, self.arn, None)

        self._lookup_endpoint_lock = locks.Lock()

    def setup(self, deploy_diagram: AwsDeployment, workflow_state_json: Dict[str, object]):
        # There will only ever be one API Gateway per project, so we can use the project id as the
        # identifier for this component
        self.deployed_state = deploy_diagram.get_previous_state(API_GATEWAY_STATE_ARN)
        if self.deployed_state is None:
            self.deployed_state = ApiGatewayDeploymentState(
                self.name, StateTypes.API_GATEWAY, None, API_GATEWAY_STATE_ARN, deploy_diagram.gateway_id
            )

        self.id = deploy_diagram.project_id.replace('-', '')

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
        ws_serialized = super().serialize()
        return {
            **ws_serialized,
            "rest_api_id": self.api_gateway_id
        }

    @gen.coroutine
    def _setup_deployment_state(
        self,
        api_gateway_manager: ApiGatewayManager,
        deployment_state: ApiGatewayDeploymentState
    ):
        """
        Retrieve resources from the deployed gateway and store them for later reference.

        :param api_gateway_manager:
        :param deployment_state:
        :return:
        """

        rest_resources = yield api_gateway_manager.get_resources(
            self._credentials,
            self.api_gateway_id
        )

        self.deployed_state.base_resource_id = rest_resources["base_resource_id"]

        gateway_endpoints: List[ApiGatewayEndpoint] = rest_resources["gateway_endpoints"]
        lambda_configs: List[ApiGatewayLambdaConfig] = rest_resources["lambda_configs"]

        # Create a map of paths to verify existence later
        # so we don't overwrite existing resources
        for lambda_config in lambda_configs:
            deployment_state.add_configured_lambda(lambda_config.lambda_uri, lambda_config)

        for gateway_endpoint in gateway_endpoints:
            deployment_state.add_endpoint(gateway_endpoint)

        if deployment_state.base_resource_id is None:
            raise MissingResourceException("Missing API Gateway base resource ID. This should never happen.")

        # TODO don't think we need this since we only ever create one state: 'refinery'

        """ 
        rest_stages = yield api_gateway_manager.get_stages(
            self._credentials,
            self.api_gateway_id
        )

        self.deployed_state.stages = [rest_stage["stageName"] for rest_stage in rest_stages]
        """

    @gen.coroutine
    def get_deployed_state(self, api_gateway_manager: ApiGatewayManager):
        yield self._setup_deployment_state(api_gateway_manager, self.deployed_state)

    def get_api_resource(self, check_path):
        return self.deployed_state.get_endpoint_from_path(check_path)

    @gen.coroutine
    def create_api_resource(self, task_spawner, parent_id, check_path, path_part):
        """
        Given a parent resource id and relative path part, create a new API gateway resource.

        :param task_spawner:
        :param parent_id:
        :param check_path:
        :param path_part:
        :return:
        """

        new_resource_id = yield task_spawner.create_resource(
            self._credentials,
            self.api_gateway_id,
            parent_id,
            path_part
        )

        # Create a new api endpoint resource and add it to our deployed state
        api_gateway_endpoint = ApiGatewayEndpoint(new_resource_id, check_path)

        yield self.deployed_state.add_endpoint(api_gateway_endpoint)

        raise gen.Return(api_gateway_endpoint)

    @gen.coroutine
    def get_or_create_endpoint(self, task_spawner, current_base_pointer_id, check_path, path_part):
        """
        Lookup the relative path part and create a new API resource if it does not exist.

        NOTE: We have a lock here in order to prevent two paths from trying to create the same
        resource. For example, consider the two paths: /test/123 and /test/abc, both of which
        do not currently exist. If this function is called concurrently without a lock, then
        a resource named 'test' will try to be created by both calls leading to a race condition.

        :param task_spawner:
        :param current_base_pointer_id:
        :param check_path:
        :param path_part:
        :return:
        """

        with (yield self._lookup_endpoint_lock.acquire()):
            api_gateway_endpoint = self.get_api_resource(check_path)
            if api_gateway_endpoint is None:
                logit(f"Creating new api resource: {check_path}")
                # Otherwise go ahead and create one
                api_gateway_endpoint = yield self.create_api_resource(
                    task_spawner,
                    current_base_pointer_id,
                    check_path,
                    path_part
                )
        raise gen.Return(
            api_gateway_endpoint
        )

    @gen.coroutine
    def ensure_endpoint_exists_in_api_gateway(self, task_spawner, api_endpoint: ApiEndpointWorkflowState):
        """
        Given an API path, ensure that all parts of the path exist as resources in the API gateway.

        :param task_spawner:
        :param api_endpoint:
        :return:
        """

        path_parts = [part for part in api_endpoint.api_path.split("/") if part != '']

        # Path level, continuously updated
        current_path = ""

        # The endpoint as it exists in API Gateway
        api_gateway_endpoint = None

        def get_current_base_pointer_id():
            return api_gateway_endpoint.id \
                if api_gateway_endpoint is not None else self.deployed_state.base_resource_id

        # Create entire path from chain
        for path_part in path_parts:
            # Check if there's a conflicting resource here
            check_path = current_path + "/" + path_part

            # Get existing resource ID instead of creating one
            api_gateway_endpoint = yield self.get_or_create_endpoint(
                task_spawner,
                get_current_base_pointer_id(),
                check_path,
                path_part
            )

            # The current endpoint we are looking at is in the path of what we are searching for
            # so we will want to prevent it from being cleaned at the end of deployment
            api_gateway_endpoint.set_endpoint_in_use()

            current_path = check_path

        found_api_gateway_endpoint = api_gateway_endpoint is not None
        api_endpoint_has_method = api_gateway_endpoint.method_exists(api_endpoint.http_method)
        should_create_method = found_api_gateway_endpoint or not api_endpoint_has_method

        if found_api_gateway_endpoint:
            # Mark the method in the api endpoint, at the end of the path, as in use
            api_gateway_endpoint.set_method_in_use(api_endpoint.http_method)

        raise gen.Return(
            dict(
                current_base_pointer_id=get_current_base_pointer_id(),
                should_create_method=should_create_method
            )
        )

    @gen.coroutine
    def create_lambda_api_route(self, task_spawner, api_endpoint: ApiEndpointWorkflowState):
        logit(f"Setting up route {api_endpoint.http_method} {api_endpoint.api_path} for API Endpoint '{api_endpoint.name}'...")

        return_data = yield self.ensure_endpoint_exists_in_api_gateway(task_spawner, api_endpoint)

        current_base_pointer_id = return_data.get("current_base_pointer_id")

        # Create method on base resource
        try:
            method_response = yield task_spawner.create_method(
                self._credentials,
                "HTTP Method",
                self.api_gateway_id,
                current_base_pointer_id,
                api_endpoint.http_method,
                False,
            )
        except ClientError as e:
            if e.response["Error"]["Code"] != "ConflictException":
                raise

        # Link the API Gateway to the lambda
        link_response = yield task_spawner.link_api_method_to_workflow(
            self._credentials,
            self.api_gateway_id,
            current_base_pointer_id,
            api_endpoint
        )

    def setup_api_endpoint(self, task_spawner, api_endpoint):
        return self.create_lambda_api_route(task_spawner, api_endpoint)

    def setup_api_endpoints(self, task_spawner: TaskSpawner, deployed_api_endpoints):
        setup_endpoint_futures = []
        for api_endpoint in deployed_api_endpoints:
            assert isinstance(api_endpoint, ApiEndpointWorkflowState)

            setup_endpoint_future = self.setup_api_endpoint(task_spawner, api_endpoint)
            setup_endpoint_futures.append(
                dict(
                    future=setup_endpoint_future,
                    workflow_state=api_endpoint
                )
            )

        return setup_endpoint_futures

    @gen.coroutine
    def finalize_setup(self, task_spawner, api_gateway_manager):
        logit("Cleaning up unused API endpoints from API gateway...")
        yield self.deployed_state.remove_unused_resources(
            api_gateway_manager,
            self._credentials,
            self.api_gateway_id
        )

        # TODO check deploy_stage_results?
        logit("Now deploying API gateway to stage...")
        deploy_stage_results = yield task_spawner.deploy_api_gateway_to_stage(
            self._credentials,
            self.api_gateway_id,
            API_GATEWAY_STAGE_NAME
        )

    @gen.coroutine
    def predeploy(self, task_spawner, api_gateway_manager):
        if self.deployed_state.api_gateway_id is not None:
            logit("Verifying existence of API Gateway...")
            self.deployed_state.exists = yield api_gateway_manager.api_gateway_exists(
                self._credentials,
                self.deployed_state.api_gateway_id
            )

        if self.deployed_state_exists():
            yield self.get_deployed_state(api_gateway_manager)

    @gen.coroutine
    def deploy(self, task_spawner, api_gateway_manager, project_id, project_config):
        # If we have a gateway id and the api gateway exists, we do not need to redeploy it
        if self.deployed_state_exists():
            raise gen.Return()

        # We need to create an API gateway
        logit("Deploying API Gateway for API Endpoint(s)...")

        rest_api_name = f"Refinery-API-Gateway_{self.id}"

        gateway_id = yield task_spawner.create_rest_api(
            self._credentials,
            rest_api_name,
            f"API Gateway created by Refinery. Associated with project ID {project_id}",
            "1.0.0"
        )
        self.current_state.api_gateway_id = gateway_id

        # Once we have this deployed, cache the state of the API Gateway resources so we can
        # later verify if lambdas are already configured for it.
        yield self.get_deployed_state(api_gateway_manager)
