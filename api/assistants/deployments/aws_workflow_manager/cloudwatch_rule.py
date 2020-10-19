from __future__ import annotations

from tornado import gen

from assistants.deployments.aws import cloudwatch_rule


class ScheduleTriggerWorkflowState(cloudwatch_rule.ScheduleTriggerWorkflowState):
    def _link_trigger_to_next_deployed_state(self, task_spawner, next_node):
        return None

    @gen.coroutine
    def predeploy(self, task_spawner):
        pass

    def deploy(self, task_spawner, project_id, project_config):
        return None
