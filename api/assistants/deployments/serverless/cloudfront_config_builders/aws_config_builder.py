import abc

from typing import Dict


def get_safe_config_key(s):
    return ''.join([i for i in s if i.isalnum()])


class AwsConfigBuilder(abc.ABC):
    def __init__(self, app_config, stage, credentials, project_id, deployment_id, current_resources):
        self.app_config = app_config
        self.stage = stage
        self.credentials = credentials
        self.project_id = project_id
        self.deployment_id = deployment_id
        self.current_resources = current_resources

        self.outputs = {}
        self.functions = {}
        self.resources = {}

    def set_outputs(self, outputs):
        self.outputs.update(outputs)

    def set_functions(self, functions):
        self.functions.update(functions)

    def set_resources(self, resources):
        self.resources.update(resources)

    @abc.abstractmethod
    def build(self, workflow_state: Dict[str, object]):
        pass

    def get_url_resource_name(self, name, index):
        safe_name = get_safe_config_key(name)
        return f"Path{safe_name}{index}"

    def get_id(self, id_):
        return get_safe_config_key(id_)
