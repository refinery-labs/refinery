from functools import cached_property

from typing import Dict, Type, Union

from data_types.deployment_stages import DeploymentStages
from assistants.deployments.serverless.cloudfront_config_builders.api_endpoint_config_builder import ApiEndpointConfigBuilder
from assistants.deployments.serverless.cloudfront_config_builders.api_gateway_config_builder import ApiGatewayConfigBuilder
from assistants.deployments.serverless.cloudfront_config_builders.aws_config_builder import AwsConfigBuilder
from assistants.deployments.serverless.cloudfront_config_builders.dynamodb_config_builder import DynamoDBConfigBuilder
from assistants.deployments.serverless.cloudfront_config_builders.lambda_config_builder import LambdaConfigBuilder
from assistants.deployments.serverless.cloudfront_config_builders.s3_config_builder import S3ConfigBuilder
from assistants.deployments.serverless.cloudfront_config_builders.sqs_queue_config_builder import SqsQueueConfigBuilder
from assistants.deployments.serverless.utils import slugify
from yaml import dump

from utils.general import logit


class IgnoreConfigBuilder(AwsConfigBuilder):
    def build(self, workflow_state):
        logit(f"ignoring workflow state: {workflow_state['id']}", "debug")
        return


ConfigBuilder = Union[
    LambdaConfigBuilder,
    ApiEndpointConfigBuilder,
    IgnoreConfigBuilder,
    SqsQueueConfigBuilder,
    S3ConfigBuilder,
    ApiGatewayConfigBuilder,
    DynamoDBConfigBuilder
]
WorkflowStateConfigBuilderLookup = Dict[str, Type[ConfigBuilder]]


class ServerlessConfigBuilder:
    def __init__(self, app_config, credentials, project_id, deployment_id, stage, diagram_data):
        self.app_config = app_config
        self.credentials = credentials
        self.project_id = project_id
        self.deployment_id = deployment_id
        self.stage = stage

        self.name = slugify(diagram_data['name'])
        self.workflow_states = diagram_data['workflow_states']

        self.functions = {}
        self.resources = {}
        self.outputs = {}

        self.serverless_config = {
            "service": self.name,
            "provider": {
                "name": "aws",
                "region": "us-west-2",
                "stage": self.stage
            },
            "functions": self.functions,
            "resources": {
                "Resources": self.resources,
                "Outputs": self.outputs
            },
            "package": {
                "individually": True,
                "exclude": ["./**"]
            },
        }

    @cached_property
    def workflow_state_config_builders(self) -> WorkflowStateConfigBuilderLookup:
        return {
            "lambda": LambdaConfigBuilder,
            "api_endpoint": ApiEndpointConfigBuilder,
            "api_gateway": ApiGatewayConfigBuilder,
            "api_gateway_response": IgnoreConfigBuilder,
            "schedule_trigger": IgnoreConfigBuilder,
            "sqs_queue": SqsQueueConfigBuilder,
            "bucket": S3ConfigBuilder,
            "key_value_table": DynamoDBConfigBuilder
        }

    @cached_property
    def workflow_state_config_builders_just_lambda(self) -> WorkflowStateConfigBuilderLookup:
        return {
            "lambda": LambdaConfigBuilder,
            "api_endpoint": IgnoreConfigBuilder,
            "api_gateway": IgnoreConfigBuilder,
            "api_gateway_response": IgnoreConfigBuilder,
            "schedule_trigger": IgnoreConfigBuilder,
            "sqs_queue": IgnoreConfigBuilder,
            "bucket": IgnoreConfigBuilder,
            "key_value_table": IgnoreConfigBuilder
        }

    @cached_property
    def workflow_state_mappers(self):
        if self.stage == DeploymentStages.dev:
            return self.workflow_state_config_builders_just_lambda
        return self.workflow_state_config_builders

    def config_builder_factory_build(self, config_builder) -> ConfigBuilder:
        return config_builder(
            self.app_config,
            self.stage,
            self.credentials,
            self.project_id,
            self.deployment_id,
            self.resources
        )

    def build_with_config_builder(self, type_, workflow_state):
        config_builder = self.workflow_state_mappers[type_]

        builder = self.config_builder_factory_build(config_builder)
        builder.build(workflow_state)

        self.update_config_from_builder(builder)

    def build(self):
        for workflow_state in self.workflow_states:
            type_ = workflow_state["type"]
            self.build_with_config_builder(type_, workflow_state)

        # API Gateway is only built once all the workflow states have been built since
        # it depends on all API Endpoints to be created
        self.build_with_config_builder("api_gateway", None)

        return dump(self.serverless_config)

    def update_config_from_builder(self, aws_config_builder: AwsConfigBuilder):
        self.functions.update(aws_config_builder.functions)
        self.resources.update(aws_config_builder.resources)
        self.outputs.update(aws_config_builder.outputs)
