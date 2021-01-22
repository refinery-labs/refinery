from __future__ import annotations

from typing import Dict, TYPE_CHECKING

from tornado import gen

from assistants.deployments.aws_workflow_manager.lambda_function import LambdaWorkflowState
from assistants.task_spawner.task_spawner_assistant import TaskSpawner

from pyconstants.project_constants import THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME

if TYPE_CHECKING:
    from assistants.deployments.aws.aws_deployment import AwsDeployment

handler_code = """
'use strict';
const https = require('https')

function log(data) {
    process.stdout.write(JSON.stringify(data));
}

function httpsPost({body, ...options}) {
    return new Promise((resolve,reject) => {
        const req = https.request({
            method: 'POST',
            ...options,
        }, res => {
            const chunks = [];
            res.on('data', data => chunks.push(data))
            res.on('end', () => {
                let body = Buffer.concat(chunks);
                switch(res.headers['content-type']) {
                    case 'application/json':
                        body = JSON.parse(body);
                        break;
                }
                resolve(body)
            })
        })
        req.on('error',reject);
        if(body) {
            req.write(body);
        }
        req.end();
    })
}

module.exports.handler = async event => {
    const workflowCallbackURL = new URL(process.env.WORKFLOW_CALLBACK_URL);

    const data = JSON.stringify(event.Records);
    
    const res = await httpsPost({
        hostname: workflowCallbackURL.host,
        path: workflowCallbackURL.pathname,
        port: workflowCallbackURL.port,
        headers: {
            'Content-Type': 'application/json',
            'Content-Length': data.length
        },
        body: data
    })
    
    log(res);

    return {};
};
"""


class SqsQueueHandlerWorkflowState(LambdaWorkflowState):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.language = "nodejs10.x"
        self.code = handler_code
        self.libraries = []
        self.max_execution_time = 30
        self.memory = 512
        self.execution_mode = "REGULAR"
        self.layers = []
        self.reserved_concurrency_count = False
        self.is_inline_execution = False
        self.shared_files_list = []

        account_id = str(self._credentials["account_id"])
        account_type = self._credentials["account_type"]
        if account_type == "THIRDPARTY":
            # TODO this role needs to change for the workflow manager
            self.role = f"arn:aws:iam::{account_id}:role/{THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME}"
        else:
            self.role = f"arn:aws:iam::{account_id}:role/refinery_workflow_manager_queue_handler_role"

        self.environment_variables = {}
        self._set_environment_variables_for_lambda()

    def serialize(self):
        serialized_ws_state = super().serialize()
        return {
            **serialized_ws_state,
            "state_hash": self.current_state.state_hash
        }

    @gen.coroutine
    def predeploy(self, task_spawner: TaskSpawner):
        raise gen.Return()

    def setup(self, deploy_diagram: AwsDeployment, workflow_state_json: Dict[str, object]):
        pass

    def deploy(self, task_spawner, project_id, project_config):
        return None
