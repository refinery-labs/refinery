import json
import uuid

from tornado import gen
from typing import Union, Dict, List

from assistants.deployments.aws.api_endpoint import ApiEndpointWorkflowState
from assistants.deployments.aws.api_gateway import ApiGatewayWorkflowState, ApiGatewayDeploymentState
from assistants.deployments.aws.aws_workflow_state import AwsWorkflowState
from assistants.deployments.aws.lambda_function import LambdaDeploymentState
from assistants.deployments.aws.sns_topic import SnsTopicDeploymentState
from assistants.deployments.aws.types import AwsDeploymentState
from assistants.deployments.aws.warmer_trigger import add_auto_warmup, WarmerTriggerWorkflowState
from assistants.deployments.diagram.deploy_diagram import DeploymentDiagram
from assistants.deployments.diagram.errors import InvalidDeployment
from assistants.deployments.diagram.trigger_state import TriggerWorkflowState
from assistants.deployments.diagram.types import StateTypes
from assistants.deployments.diagram.workflow_states import WorkflowState, StateLookup
from assistants.deployments.teardown_manager import AwsTeardownManager
from utils.general import logit


def json_to_aws_deployment_state(workflow_state_json):
    arn = workflow_state_json.get("arn")
    ws_type = workflow_state_json.get("type")
    state_hash = workflow_state_json.get("state_hash")
    name = workflow_state_json.get("name")

    try:
        state_type = StateTypes(ws_type)
    except ValueError as e:
        raise InvalidDeployment(f"workflow state {arn} has invalid type {ws_type}")

    if state_type == StateTypes.LAMBDA:
        return LambdaDeploymentState(name, state_type, state_hash, arn)

    elif state_type == StateTypes.API_GATEWAY:
        api_gateway_id = workflow_state_json.get("rest_api_id")
        return ApiGatewayDeploymentState(name, state_type, state_hash, arn, api_gateway_id)

    elif state_type == StateTypes.SNS_TOPIC:
        return SnsTopicDeploymentState(name, state_type, state_hash, arn)

    return AwsDeploymentState(name, state_type, state_hash, arn)


class AwsDeployment(DeploymentDiagram):
    def __init__(self, *args, api_gateway_manager=None, latest_deployment=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.api_gateway_manager = api_gateway_manager

        self._workflow_state_lookup: StateLookup[AwsWorkflowState] = self._workflow_state_lookup
        self._previous_state_lookup: StateLookup[AwsDeploymentState] = StateLookup[AwsDeploymentState]()

        self.gateway_id = None
        if self.project_config.get("api_gateway") and self.project_config["api_gateway"].get("gateway_id"):
            self.gateway_id = self.project_config["api_gateway"]["gateway_id"]

        if latest_deployment is not None and "workflow_states" in latest_deployment:
            # deserialize the workflow states from the previous deployment to use them as a reference when diffing.
            for ws in latest_deployment["workflow_states"]:
                state = json_to_aws_deployment_state(ws)

                if isinstance(state, ApiGatewayDeploymentState) and self.gateway_id is not None:
                    state.api_gateway_id = self.gateway_id

                self._previous_state_lookup.add_state(state)

    def serialize(self):
        serialized_deployment = super().serialize()
        workflow_states: [Dict] = []
        workflow_relationships: [Dict] = []

        for ws in self._workflow_state_lookup.states():
            workflow_states.append(ws.serialize())
            for transition_type_transitions in ws.transitions.values():
                workflow_relationships.extend(
                    [transition.serialize(use_arns=False) for transition in transition_type_transitions]
                )

        return {
            **serialized_deployment,
            "workflow_states": workflow_states,
            "workflow_relationships": workflow_relationships,
        }

    def get_updated_config(self):
        return {
            **self.project_config,
            "api_gateway": {
                "gateway_id": self.api_gateway.api_gateway_id if self.api_gateway is not None else None
            }
        }

    @property
    def api_gateway(self) -> Union[ApiGatewayWorkflowState, None]:
        return self._workflow_state_lookup.find_state(lambda state: state.type == StateTypes.API_GATEWAY)

    def current_deployment_workflow_states(self) -> List[AwsDeploymentState]:
        return [ws.current_state for ws in self._workflow_state_lookup.states()]

    def get_previous_state(self, state_id) -> Union[AwsDeploymentState, None]:
        if self._previous_state_lookup is None:
            return None
        return self._previous_state_lookup[state_id]

    def get_previous_api_gateway_state(self, api_gateway_arn: str) -> ApiGatewayDeploymentState:
        non_existing_deployment_state = ApiGatewayDeploymentState(None, StateTypes.API_GATEWAY, None, api_gateway_arn, None)

        if self._previous_state_lookup is None:
            return non_existing_deployment_state

        # try to locate the API Gateway from the previous deployment
        api_gateway_state = self._previous_state_lookup.find_state(lambda state: state.arn == api_gateway_arn)
        if api_gateway_state is not None:
            assert isinstance(api_gateway_state, ApiGatewayDeploymentState)

            return api_gateway_state

        return non_existing_deployment_state

    def _add_previous_state_for_cleanup(self, deployment_state: AwsDeploymentState):
        """
        To ensure all resources are cleaned up, it may be necessary to appened a discovered resource to
        the list of previously deployed states.

        :param deployment_state: A discovered deployed state while deploying the current state.
        :return:
        """
        # Create a random UUID since we are just going to be cleaning this up
        deployment_state.arn = str(uuid.uuid4())

        self._previous_state_lookup.add_state(deployment_state)

    def unused_workflow_states(self) -> List[AwsDeploymentState]:
        """
        At the end of deployment, any workflow states that do not exist in the current state of deployment will be
        returned with the intent of removal.

        :return: A list of deployment states marked for removal.
        """
        if self._previous_state_lookup is None:
            return []

        previous_state_ids = set(self._previous_state_lookup.states())
        current_state_ids = set(self._workflow_state_lookup.states())
        removable_state_ids = previous_state_ids - current_state_ids

        removeable_states = [
            self._previous_state_lookup[state_id] for state_id in removable_state_ids
        ]

        # Additional filtering step for api gateways since we give them random ids
        return [
            state for state in removeable_states
            if isinstance(state, ApiGatewayWorkflowState) and self.api_gateway.api_gateway_id != state.api_gateway_id
        ]

    @gen.coroutine
    def remove_workflow_states(
            self,
            aws_teardown_manager: AwsTeardownManager,
            credentials,
            successful_deploy
    ):
        if successful_deploy:
            # If we had a successful deploy, then we only want to remove unused resources
            workflow_states = self.unused_workflow_states()
        else:
            # Otherwise, we remove the entire current deployment since it failed
            workflow_states = self.current_deployment_workflow_states()

        yield aws_teardown_manager.teardown_deployed_states(credentials, workflow_states)

        return workflow_states

    def validate_arn_exists_and_mark_for_cleanup(self, state_type: StateTypes, arn: str):
        """
        Validate if an arn exists in the current deployment.
        If it does not, then we check if we know to remove it via the previous state.
        Otherwise, we add this to our previous state so we know to clean it up.

        :param state_type:
        :param arn:
        :return: boolean of whether the arn exists in the current deployment.
        """

        find_state_by_arn = lambda state: state.arn == arn

        workflow_state = self._workflow_state_lookup.find_state(find_state_by_arn)
        if workflow_state is not None:
            return True

        previous_workflow_state = self._previous_state_lookup.find_state(find_state_by_arn)
        if previous_workflow_state is None:
            deploy_state = AwsDeploymentState(None, state_type, None, arn)
            self._add_previous_state_for_cleanup(deploy_state)

        return False

    def _update_workflow_states_with_deploy_info(self, task_spawner):
        update_futures = []

        for workflow_state in self._workflow_state_lookup.states():
            if isinstance(workflow_state, ApiEndpointWorkflowState):
                api_gateway_id = self.api_gateway.api_gateway_id
                workflow_state.set_gateway_id(api_gateway_id)

            elif isinstance(workflow_state, TriggerWorkflowState):
                # If this workflow state feels triggered, calm it down by associating it with its deployed children
                workflow_state_futures = workflow_state.link_deployed_triggers_to_next_state(task_spawner)
                update_futures.extend(workflow_state_futures)

        return update_futures

    def _use_or_create_api_gateway(self):
        api_gateway = ApiGatewayWorkflowState(self.credentials)
        api_gateway.setup(self, {})

        self.add_workflow_state(api_gateway)

    @gen.coroutine
    def _create_auto_warmers(
            self,
            task_spawner,
            credentials,
            unique_deploy_id,
            warmup_concurrency_level,
            workflow_states
    ):
        combined_warmup_list = json.loads(
            json.dumps(
                [state.serialize() for state in workflow_states]
            )
        )
        logit("Adding auto-warming to the deployment...")

        warmup_concurrency_level = int(warmup_concurrency_level)
        warmer_triggers_data = yield add_auto_warmup(
            task_spawner,
            credentials,
            warmup_concurrency_level,
            unique_deploy_id,
            combined_warmup_list
        )

        for warmer_trigger in warmer_triggers_data:
            warmer_id = warmer_trigger["id"]
            name = warmer_trigger["name"]
            arn = warmer_trigger["arn"]

            warmer_trigger_state = WarmerTriggerWorkflowState(
                None, warmer_id, name, StateTypes.WARMER_TRIGGER, arn=arn)
            self.add_workflow_state(warmer_trigger_state)

    def get_workflow_state_predeploy_future(self, workflow_state: WorkflowState):
        if isinstance(workflow_state, ApiGatewayWorkflowState):
            return self.api_gateway.predeploy(self.task_spawner, self.api_gateway_manager)
        return None

    def get_workflow_state_deploy_future(self, workflow_state: WorkflowState):
        if isinstance(workflow_state, ApiGatewayWorkflowState):
            return workflow_state.deploy(
                self.task_spawner, self.api_gateway_manager, self.project_id, self.project_config)
        return None

    @gen.coroutine
    def execute_predeploy(self):
        predeploy_futures = self.get_workflow_state_futures(
            self.create_predeploy_future,
            self.get_workflow_state_predeploy_future
        )
        predeploy_exceptions = yield self.handle_deploy_futures(predeploy_futures)
        raise gen.Return(predeploy_exceptions)

    @gen.coroutine
    def execute_deploy(self):
        deploy_futures = self.get_workflow_state_futures(
            self.create_deploy_future,
            self.get_workflow_state_deploy_future
        )
        deployment_exceptions = yield self.handle_deploy_futures(deploy_futures)
        raise gen.Return(deployment_exceptions)

    @gen.coroutine
    def execute_setup_api_endpoints(self, deployed_api_endpoints):
        setup_endpoint_futures = self.api_gateway.setup_api_endpoints(
                self.task_spawner, deployed_api_endpoints)

        setup_endpoint_executions = yield self.handle_deploy_futures(setup_endpoint_futures)
        raise gen.Return(setup_endpoint_executions)

    @gen.coroutine
    def execute_finalize_gateway(self):
        future = dict(
            future=self.api_gateway.finalize_setup(self.task_spawner, self.api_gateway_manager),
            workflow_state=self.api_gateway
        )
        exceptions = yield self.handle_deploy_futures([future])
        raise gen.Return(exceptions)

    @gen.coroutine
    def deploy(self):
        # If we have api endpoints to deploy, we will deploy an api gateway for them
        deployed_api_endpoints = self._workflow_state_lookup.find_states(
            lambda state: state.type == StateTypes.API_ENDPOINT)

        deploying_api_gateway = len(deployed_api_endpoints) > 0

        if deploying_api_gateway:
            self._use_or_create_api_gateway()

        predeploy_exceptions = yield self.execute_predeploy()
        if len(predeploy_exceptions) != 0:
            raise gen.Return([])

        # If we experienced exceptions while deploying, we must stop deployment
        deployment_exceptions = yield self.execute_deploy()
        if len(deployment_exceptions) != 0:
            raise gen.Return(deployment_exceptions)

        if deploying_api_gateway:
            setup_api_endpoint_exceptions = yield self.execute_setup_api_endpoints(deployed_api_endpoints)
            if len(setup_api_endpoint_exceptions) != 0:
                raise gen.Return(setup_api_endpoint_exceptions)

            finalize_exceptions = yield self.execute_finalize_gateway()
            if len(finalize_exceptions) != 0:
                raise gen.Return(finalize_exceptions)

        update_futures = self._update_workflow_states_with_deploy_info(self.task_spawner)

        warmup_concurrency_level = self.project_config.get("warmup_concurrency_level")
        if warmup_concurrency_level:

            workflow_states = self._workflow_state_lookup.find_states(
                lambda state: state.type == StateTypes.LAMBDA or state.type == StateTypes.API_ENDPOINT
            )

            yield self._create_auto_warmers(
                self.task_spawner,
                self.credentials,
                self._unique_deploy_id,
                warmup_concurrency_level,
                workflow_states
            )

        update_exceptions = yield self.handle_deploy_futures(update_futures)
        if len(update_exceptions) != 0:
            raise gen.Return(update_exceptions)

        cleanup_futures = self._cleanup_unused_workflow_state_resources(self.task_spawner)
        cleanup_exceptions = yield self.handle_deploy_futures(cleanup_futures)
        if len(cleanup_exceptions) != 0:
            raise gen.Return(cleanup_exceptions)

        raise gen.Return(deployment_exceptions)

    @gen.coroutine
    def deploy_diagram(self, diagram_data):
        # TODO enforce json schema for incoming deployment data?

        # Kick off the creation of the log table for the project ID
        # This is fine to do if one already exists because the SQL
        # query explicitly specifies not to create one if it exists.
        project_log_table_future = self.task_spawner.create_project_id_log_table(
            self.credentials,
            self.project_id
        )

        self.load_deployment_graph(diagram_data)

        deployment_exceptions = yield self.deploy()

        if len(deployment_exceptions) > 0:
            # This is the earliest point we can apply the breaks in the case of an exception
            # It's the callers responsibility to tear down the nodes

            logit("[ ERROR ] An uncaught exception occurred during the deployment process!", "error")
            logit(deployment_exceptions, "error")
            raise gen.Return(deployment_exceptions)

        # Make sure that log table is set up
        # It almost certainly is by this point
        yield project_log_table_future

        raise gen.Return(deployment_exceptions)
