import os
from functools import cached_property

from data_types.deployment_stages import DeploymentStages
from deployment.serverless.utils import slugify, get_unique_workflow_state_name
from pyconstants.project_constants import (
    LANGUAGE_TO_RUNTIME, LANGUAGE_TO_HANDLER)
from yaml import dump


class ServerlessConfigBuilder:
    _api_resource_base_set = False

    def __init__(self, app_config, credentials, project_id, deployment_id, stage, diagram_data):
        self.app_config = app_config
        self.credentials = credentials
        self.project_id = project_id
        self.deployment_id = deployment_id
        self.stage = stage
        self.diagram_data = diagram_data
        self.name = diagram_data['name']
        self.name = slugify(diagram_data['name'])
        self.workflow_states = diagram_data['workflow_states']
        self.functions = {}
        self.resources = {}
        self.container_images = {}
        self.api_method_ids = []
        self.serverless_config = {
            "service": slugify(self.name),
            "provider": {
                "name": "aws",
                "region": "us-west-2",
                "stage": self.stage
            },
            "functions": self.functions,
            "resources": self.resources,
            "package": {
                "individually": True,
                "exclude": ["./**"]
            },
        }

    @cached_property
    def workflow_state_mappers_all(self):
        return {
            "api_endpoint": self.build_api_endpoint,
            "api_gateway_response": self.build_api_gateway_response,
            "lambda": self.build_lambda,
            "schedule_trigger": self.build_schedule_trigger,
            "sqs_queue": self.build_sqs_queue
        }

    def ignore_workflow_state(self, workflow_state):
        return

    @cached_property
    def workflow_state_mappers_only_lambda(self):
        return {
            "api_endpoint": self.ignore_workflow_state,
            "api_gateway_response": self.ignore_workflow_state,
            "lambda": self.build_lambda,
            "schedule_trigger": self.ignore_workflow_state,
            "sqs_queue": self.ignore_workflow_state
        }

    @cached_property
    def workflow_state_mappers(self):
        if self.stage == DeploymentStages.dev:
            return self.workflow_state_mappers_only_lambda
        return self.workflow_state_mappers_all

    def build(self):
        for workflow_state in self.workflow_states:
            type_ = workflow_state['type']
            builder = self.workflow_state_mappers[type_]

            builder(workflow_state)

        # TODO for all images that have been identified, inject the refinery runtime into them

        return dump(self.serverless_config)

    ###########################################################################
    # Lambda
    ###########################################################################

    def get_optional_lambda_arguments(self, workflow_state):
        reserved_concurrency_count = workflow_state['reserved_concurrency_count']

        optional_arguments = {
            "reservedConcurrency": reserved_concurrency_count,
        } if reserved_concurrency_count is not False else {}

        return optional_arguments

    def build_lambda(self, workflow_state):
        workflow_state_id = workflow_state['id']
        id_ = self.get_id(workflow_state_id)
        name = get_unique_workflow_state_name(self.stage, workflow_state['name'], id_)
        memory = workflow_state['memory']
        max_execution_time = workflow_state['max_execution_time']

        lambda_environment = self.get_lambda_environment(workflow_state_id, workflow_state)

        optional_arguments = self.get_optional_lambda_arguments(workflow_state)

        self.functions[id_] = {
            "name": name,
            **lambda_environment,
            **optional_arguments,
            "description": "A lambda deployed by refinery",
            "memorySize": memory,
            "timeout": max_execution_time,
            "tracing": 'PassThrough',
        }

    def get_lambda_environment(self, workflow_state_id, workflow_state):
        id_ = self.get_id(workflow_state_id)

        lambda_path = f"lambda/{id_}"
        name = workflow_state["name"]
        language = workflow_state['language']
        environment_variables = workflow_state.get("environment_variables", {})

        account_id = self.credentials["account_id"]
        ecr_registry = f"{account_id}.dkr.ecr.us-west-2.amazonaws.com"
        image_name = get_unique_workflow_state_name(self.stage, name, id_).lower()

        repo_uri = f"{ecr_registry}/{image_name}"

        container = workflow_state.get('container')
        if container is not None:
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
        queue_name = get_unique_workflow_state_name(self.stage, workflow_state['name'], id_)

        self.set_aws_resources({
            id_: {
                "Type": "AWS::SQS::Queue",
                "Properties": {
                    "QueueName": slugify(queue_name)
                }
            }
        })

        handler_name = f"{queue_name}_Handler"
        try:
            handler_batch_size = int(workflow_state["batch_size"])
        except ValueError:
            raise Exception(f"unable to parse 'batch_size' for SQS Queue: {queue_name}")

        self.functions[f'QueueHandler{id_}'] = {
            "name": handler_name,
            "handler": "lambda/queue/index.handler",
            "package": {
                "include": [
                    f"lambda/queue/**"
                ]
            },
            "events": [{
                "sqs": {
                    "batchSize": handler_batch_size,
                    "arn": {
                        "Fn::GetAtt": [id_, "Arn"]
                    }
                }
            }]
        }

        self.set_aws_outputs({
            id_: {
                "Value": {
                    "Ref": id_
                }
            }
        })

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

        i = 0
        path_part = None
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

        # TODO We will not build an api gateway with SF, instead we will build and manage it from API.
        # Today, the api gateway is stored in the project config (different than the project.json)
        # we will need the restApiId (api gateway id) to persist through deployments to prevent
        # user's project domain from changing on every deploy, teardown, and redeploy.
        #
        # provider:
        #  apiGateway:
        #    restApiId:
        #      'Fn::ImportValue': apiGateway-restApiId

        self.set_aws_resources({
            "ApiGatewayRestApi": {
                "Type": "AWS::ApiGateway::RestApi",

                # TODO: Once we have code in API to handle the teardown of this resource, we can uncomment this
                # "DeletionPolicy": "Retain",

                "Properties": {
                    "Name": f"Gateway_{project_id}"
                }
            },
            "ApiGatewayDeployment": {
                "Type": "AWS::ApiGateway::Deployment",
                "DependsOn": self.api_method_ids,
                "Properties": {
                    "RestApiId": {
                        "Ref": "ApiGatewayRestApi"
                    },
                    "StageName": "${self:provider.stage, 'dev'}"
                }
            }
        })

        invoke_url_format = [
            "https://",
            {"Ref": "ApiGatewayRestApi"},
            ".execute-api.${self:provider.region}.amazonaws.com/${self:provider.stage, 'dev'}"
        ]

        self.set_aws_outputs({
            "ApiGatewayRestApiID": {
                "Value": {
                    "Ref": "ApiGatewayRestApi"
                }
            },
            "ApiGatewayInvokeURL": {
                "Value": {
                    "Fn::Join": [
                        "",
                        invoke_url_format
                    ]
                }
            }
        })

        self._api_resource_base_set = True

    def set_api_resource(self, api_resources, path_part, index, parent=None):
        resource = self.get_url_resource_name(path_part, index)
        parent_id = {}
        config = {
            "Type": "AWS::ApiGateway::Resource",
            "Properties": {
                "ParentId": parent_id,
                "PathPart": path_part,
                "RestApiId": {
                    "Ref": "ApiGatewayRestApi"
                }
            }
        }

        if parent:
            parent_id['Ref'] = self.get_url_resource_name(parent, index - 1)
        else:
            parent_id['Fn::GetAtt'] = [
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

        self.api_method_ids.append(id_)

        method_response_codes = [
            {
                "StatusCode": 200
            },
            {
                "StatusCode": 500
            }
        ]

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
                    "AuthorizationType": "",
                    "Integration": {
                        "IntegrationHttpMethod": http_method.upper(),
                        "Type": "HTTP",
                        "Uri": uri,
                        "IntegrationResponses": method_response_codes
                    },
                    "MethodResponses": method_response_codes
                }
            }
        }

    ###########################################################################
    # Utility functions
    ###########################################################################

    def get_url_resource_name(self, name, index):
        safe_name = self.get_safe_config_key(name)
        return f"Path{safe_name}{index}"

    def set_aws_resources(self, resources):
        if "Resources" not in self.resources:
            self.resources['Resources'] = {}

        self.resources["Resources"].update(resources)

    def set_aws_outputs(self, outputs):
        if "Outputs" not in self.resources:
            self.resources['Outputs'] = {}

        self.resources["Outputs"].update(outputs)

    def get_id(self, id_):
        return self.get_safe_config_key(id_)

    def get_safe_config_key(self, s):
        return ''.join([i for i in s if i.isalnum()])
