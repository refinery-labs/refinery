

class ScheduleTriggerWorkflowState(TriggerWorkflowState):
    def __init__(self, *args, **kwargs):
        super(ScheduleTriggerWorkflowState, self).__init__(*args, **kwargs)

        self.schedule_expression = None
        self.description = None
        self.input_string = None

        account_id = self._credentials["account_id"]
        self.events_role_arn = f"arn:aws:iam::{account_id}:role/refinery_default_aws_cloudwatch_role"

        self.deployed_state: ScheduleTriggerDeploymentState = self.deployed_state

    def serialize(self):
        serialized_ws = super(ScheduleTriggerWorkflowState, self).serialize()
        return {
            **serialized_ws,
            "schedule_expression": self.schedule_expression,
            "input_string": self.input_string,
            "description": self.description,
            "state_hash": self.current_state.state_hash
        }

    def get_state_hash(self):
        serialized_state = self.serialize()

        serialized_lambda_values = json.dumps(serialized_state).encode('utf-8')
        return hashlib.sha256(serialized_lambda_values).hexdigest()

    def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
        super(ScheduleTriggerWorkflowState, self).setup(deploy_diagram, workflow_state_json)
        if self.deployed_state is None:
            self.deployed_state = ScheduleTriggerDeploymentState(self.type, self.arn, None)

        self.schedule_expression = workflow_state_json["schedule_expression"]
        self.description = workflow_state_json["description"]
        self.input_string = workflow_state_json["input_string"]

    def deploy(self, task_spawner, project_id, project_config):
        if self.deployed_state_exists() and not self.state_has_changed():
            # State for the Cloudwatch rule has not changed
            return None

        logit(f"Deploying schedule trigger '{self.name}'...")
        return task_spawner.create_cloudwatch_rule(
            self._credentials,
            self
        )

    @gen.coroutine
    def predeploy(self, task_spawner):
        rule_info = yield task_spawner.get_cloudwatch_rules(
            self._credentials,
            self
        )

        self.deployed_state.exists = rule_info["exists"]
        self.deployed_state.rules = rule_info["rules"]
        self.current_state.state_hash = self.get_state_hash()

    def _rule_exists_for_state(self, state: LambdaWorkflowState):
        if not self.deployed_state_exists():
            return False

        return any([rule.arn == state.arn for rule in self.deployed_state.rules])

    def _link_trigger_to_next_deployed_state(self, task_spawner, next_node):
        if not self.state_has_changed() and self._rule_exists_for_state(next_node):
            # Cloudwatch rule has not changed and is already configured for this next state
            return None

        return task_spawner.add_rule_target(
            self._credentials,
            self,
            next_node
        )
