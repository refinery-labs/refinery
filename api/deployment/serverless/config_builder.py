from functools import cached_property
from pyconstants.project_constants import (
    LANGUAGE_TO_RUNTIME, LANGUAGE_TO_HANDLER
)
from yaml import dump


class ServerlessConfigBuilder:
    _api_resource_base_set = False

    def __init__(self, app_config, project_id, deployment_id, project_config):
        self.app_config = app_config
        self.project_id = project_id
        self.deployment_id = deployment_id
        self.project_config = project_config
        self.name = project_config['name']
        self.workflow_states = project_config['workflow_states']
        self.functions = {}
        self.resources = {}
        self.serverless_config = {
            "service": self.slugify(self.name),
            "provider": {
                "name": "aws",
                "region": "us-west-2"
            },
            "functions": self.functions,
            "resources": self.resources,
            "package": {
                "individually": True,
                "exclude": ["./**"]
            }
        }

    @cached_property
    def workflow_state_mappers(self):
        return {
            "api_endpoint": self.build_api_endpoint,
            "api_gateway_response": self.build_api_gateway_response,
            "lambda": self.build_lambda,
            "schedule_trigger": self.build_schedule_trigger,
            "sqs_queue": self.build_sqs_queue
        }

    def build(self):
        for workflow_state in self.workflow_states:
            type_ = workflow_state['type']
            builder = self.workflow_state_mappers[type_]

            builder(workflow_state)

        return dump(self.serverless_config)

    ###########################################################################
    # Lambda
    ###########################################################################

    def build_lambda(self, workflow_state):
        id_ = self.get_id(workflow_state['id'])
        name = workflow_state['name']
        language = workflow_state['language']
        memory = workflow_state['memory']
        max_execution_time = workflow_state['max_execution_time']
        reserved_concurrency_count = workflow_state['reserved_concurrency_count']
        environment_variables = workflow_state.get("environment_variables", {})
        layers = workflow_state.get("layers", [])
        handler = self.get_lambda_handler(id_, LANGUAGE_TO_HANDLER[language])

        self.functions[id_] = {
            "name": name,
            "handler": handler,
            "description": "A lambda deployed by refinery",
            "runtime": LANGUAGE_TO_RUNTIME[language],
            "memorySize": memory,
            "timeout": max_execution_time,
            "reservedConcurrency": reserved_concurrency_count,
            "tracing": 'PassThrough',
            "environment": environment_variables,
            "layers": layers,
            "package": {
                "include": [
                    f"lambda/{id_}/**"
                ]
            }
        }
 
    def get_lambda_handler(self, id_, handler_module):
        return f'lambda/{id_}/{handler_module}'

    ###########################################################################
    # Schedule trigger
    ###########################################################################

    def build_schedule_trigger(self, workflow_state):
        # Do nothing, this is handled by temporal
        return 

    ###########################################################################
    # SQS queue
    ###########################################################################

    def build_sqs_queue(self, workflow_state):
        id_ = self.get_id(workflow_state['id'])
        queue_name = workflow_state['name']

        self.set_aws_resources({
            id_: {
                "Type": "AWS::SQS::Queue",
                "Properties": {
                    "QueueName": self.slugify(queue_name)
                }
            }
        })

        self.functions[f'QueueHandler{id_}'] = {
            "handler": "lambda/queue/index.handler",
            "events": [{
                "sqs": {
                    "batchSize": 10,
                    "arn": {
                        "Fn::GetAtt": [id_, "Arn"]
                    }
                }
            }]
        }

    ###########################################################################
    # API Resource
    ###########################################################################

    def build_api_gateway_response(self, workflow_state):
        # Do nothing
        return

    def build_api_endpoint(self, workflow_state):
        self.set_api_resource_base()

        api_resources = {}
        api_path = workflow_state['api_path']
        path_parts = [i.strip() for i in api_path.split('/') if i]

        for i, path_part in enumerate(path_parts):
            parent = path_parts[i - 1] if i > 0 else None
            self.set_api_resource(api_resources, path_part, i, parent)

        # Last element from enumeration will be the end of the url
        api_resources.update(self.get_proxy_method(workflow_state, path_part, i))

        self.set_aws_resources(api_resources)

    def set_api_resource_base(self):
        if self._api_resource_base_set:
            return

        project_id = self.get_id(self.project_id)

        self.set_aws_resources({
            "ApiGatewayRestApi": {
                "Type": "AWS::ApiGateway::RestApi",
                "Properties": {"Name": f"Gateway_{project_id}"}
            }
        })
        self._api_resource_base_set = True

    def set_api_resource(self, api_resources, path_part, index, parent=None):
        resource = self.get_url_resource_name(path_part, index)
        parentId = {}
        config = {
            "Type": "AWS::ApiGateway::Resource",
            "Properties": {
                "ParentId": parentId,
                "PathPart": path_part,
                "RestApiId": {
                    "Ref": "ApiGatewayRestApi"
                }
            }
        }

        if parent:
            parentId['Fn::Ref'] = self.get_url_resource_name(parent, index - 1)
        else:
            parentId['Fn::GetAtt'] = [
                'ApiGatewayRestApi',
                'RootResourceId'
            ]

        api_resources[resource] = config

    def get_proxy_method(self, workflow_state, path_part, index):
        url_resource_name = self.get_url_resource_name(path_part, index)
        http_method = workflow_state['http_method']
        raw_id = workflow_state['id']
        id_ = self.get_id(raw_id)
        base = self.app_config.get("workflow_manager_api_url")
        uri = f"{base}/deployment/{self.deployment_id}/workflow/{raw_id}"

        return {
            id_: {
                "Type": "AWS::ApiGateway::Method",
                "Properties": {
                    "ResourceId": {
                        "Ref": url_resource_name
                    },
                    "RestApiId": {
                        "Ref": "ApiGatewayRestApi",
                    },
                    "HttpMethod": http_method.upper(),
                    "Integration": {
                        "IntegrationMethod": "POST",
                        "Type": "HTTP",
                        "Uri": uri,
                    }
                }
            }
        }

    ###########################################################################
    # Utility functions
    ###########################################################################

    def get_url_resource_name(self, name, index):
        return f"Path{name}_{index}"

    def set_aws_resources(self, resources):
        if "Resources" not in self.resources:
            self.resources['Resources'] = {}

        self.resources["Resources"].update(resources)

    def get_id(self, id_):
        return ''.join([i for i in id_ if i.isalnum()])

    def slugify(self, name):
        return ''.join([
            i for i in name.replace(' ', '_') if i.isalnum() or i == '_'
        ])
