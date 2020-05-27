class SnsTopicWorkflowState(TriggerWorkflowState):
    def __init__(self, *args, **kwargs):
        super(SnsTopicWorkflowState, self).__init__(*args, **kwargs)

        self.deployed_state: SnsTopicDeploymentState = self.deployed_state

    def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
        super(SnsTopicWorkflowState, self).setup(deploy_diagram, workflow_state_json)
        if self.deployed_state is None:
            self.deployed_state = SnsTopicDeploymentState(self.type, self.arn, None)

    def deploy(self, task_spawner, project_id, project_config):
        logit(f"Deploying SNS topic '{self.name}'...")

        return task_spawner.create_sns_topic(
            self._credentials,
            self.id,
            self.name
        )

    @gen.coroutine
    def predeploy(self, task_spawner: TaskSpawner):
        sns_subs_info = yield task_spawner.get_sns_topic_subscriptions(
            self._credentials,
            self
        )

        self.deployed_state.exists = sns_subs_info["exists"]
        self.deployed_state.subscriptions = sns_subs_info["subscriptions"]

    @gen.coroutine
    def cleanup(self, task_spawner: TaskSpawner, deployment: DeploymentDiagram):
        for subscription in self.deployed_state.subscriptions:
            sub_arn = subscription.subscription_arn
            endpoint = subscription.endpoint

            exists = deployment.validate_arn_exists(StateTypes.LAMBDA, endpoint)
            if not exists:
                yield task_spawner.unsubscribe_lambda_from_sns_topic(
                    self._credentials,
                    sub_arn
                )

    def _trigger_exists_for_state(self, state: LambdaWorkflowState):
        if not self.deployed_state_exists():
            return False

        return any([sub.endpoint == state.arn for sub in self.deployed_state.subscriptions])

    def _link_trigger_to_next_deployed_state(self, task_spawner, next_node):
        if self._trigger_exists_for_state(next_node):
            # We already have this trigger connected to this node
            return

        return task_spawner.subscribe_lambda_to_sns_topic(
            self._credentials,
            self,
            next_node,
        )
