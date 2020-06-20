from assistants.deployments.diagram.workflow_states import WorkflowState


class TriggerWorkflowState(WorkflowState):
    def _link_trigger_to_next_deployed_state(self, task_spawner, next_node):
        return None

    def link_deployed_triggers_to_next_state(self, task_spawner):
        deploy_trigger_futures = []

        for transition_type, transitions in self.transitions.items():
            for transition in transitions:

                future = self._link_trigger_to_next_deployed_state(
                    task_spawner, transition.next_node)

                if future is None:
                    continue

                deploy_trigger_futures.append(
                    dict(
                        future=future,
                        workflow_state=self
                    )
                )

        return deploy_trigger_futures
