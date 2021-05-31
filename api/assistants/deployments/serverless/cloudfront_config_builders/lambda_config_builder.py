import os

from assistants.deployments.serverless.cloudfront_config_builders.aws_config_builder import AwsConfigBuilder
from assistants.deployments.serverless.cloudfront_config_builders.iam_config_utils import build_iam_role
from assistants.deployments.serverless.utils import get_unique_workflow_state_name
from pyconstants.project_constants import LANGUAGE_TO_HANDLER, LANGUAGE_TO_RUNTIME


class LambdaConfigBuilder(AwsConfigBuilder):
    def build(self, workflow_state):
        workflow_state_id = workflow_state['id']
        id_ = self.get_id(workflow_state_id)
        name = get_unique_workflow_state_name(self.stage, workflow_state['name'], id_)

        function_config = {
            "name": name,
            "description": "A lambda deployed by Refinery",
            "tracing": 'PassThrough',
        }

        memory = workflow_state.get('memory')
        if memory is not None:
            function_config.update({'memorySize': memory})

        max_execution_time = workflow_state.get('max_execution_time')
        if max_execution_time is not None:
            function_config.update({'timeout': max_execution_time})

        role = self.get_lambda_role(id_, workflow_state)
        if role is not None:
            function_config.update({'role': role})

        lambda_environment = self.get_lambda_environment(workflow_state_id, workflow_state)
        function_config.update(lambda_environment)

        optional_arguments = self.get_optional_lambda_arguments(workflow_state)
        function_config.update(optional_arguments)

        self.functions[id_] = function_config

    def get_lambda_environment(self, workflow_state_id, workflow_state):
        id_ = self.get_id(workflow_state_id)

        lambda_path = f"lambda/{id_}"
        name = workflow_state["name"]
        language = workflow_state['language']
        environment_variables = workflow_state.get("environment_variables", {})

        account_id = self.credentials["account_id"]
        ecr_registry = f"{account_id}.dkr.ecr.us-west-2.amazonaws.com"
        image_name = get_unique_workflow_state_name(self.stage, name, id_).lower()

        container = workflow_state.get('container')
        if container is not None:
            repo_uri = f"{ecr_registry}/{image_name}"

            # Image tag is located in a json file in the lambda directory
            config_path = os.path.join(lambda_path, "container.json")
            image_tag = f"${{file(./{config_path}):tag}}"

            environment_variables = {
                **environment_variables,
                "REFINERY_FUNCTION_NAME": workflow_state_id
            }

            return {
                "image": f"{repo_uri}@{image_tag}",
                "environment": environment_variables
            }

        handler = self.get_lambda_handler(id_, LANGUAGE_TO_HANDLER[language])
        layers = workflow_state.get("layers", [])
        return {
            "handler": handler,
            "layers": layers,
            "environment": environment_variables,
            "runtime": LANGUAGE_TO_RUNTIME[language],
            "package": {
                "include": [
                    f"{lambda_path}/**"
                ]
            }
        }

    def get_lambda_role(self, id_, workflow_state):
        ws_policies = workflow_state.get("policies")
        if ws_policies is None:
            return None

        role_name = id_ + "Role"

        iam_role = build_iam_role("lambda.amazonaws.com", role_name, ws_policies)

        self.set_resources({
            role_name: iam_role
        })
        return role_name

    def get_optional_lambda_arguments(self, workflow_state):
        reserved_concurrency_count = workflow_state.get('reserved_concurrency_count')

        optional_arguments = {
            "reservedConcurrency": reserved_concurrency_count,
        } if not (reserved_concurrency_count in [None, False]) else {}

        return optional_arguments

    def get_lambda_handler(self, id_, handler_module):
        return f'lambda/{id_}/{handler_module}'

