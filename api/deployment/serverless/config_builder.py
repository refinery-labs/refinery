import os
from functools import cached_property

from data_types.deployment_stages import DeploymentStages
from deployment.serverless.utils import slugify, get_unique_workflow_state_name
from pyconstants.project_constants import (
    LANGUAGE_TO_RUNTIME, LANGUAGE_TO_HANDLER)
from yaml import dump

from utils.general import logit


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
            "sqs_queue": self.build_sqs_queue,
            "bucket": self.build_s3_bucket
        }

    @cached_property
    def workflow_state_mappers_only_lambda(self):
        def ignore_workflow_state(workflow_state):
            logit("ignoring workflow state: " + workflow_state["id"], "debug")
            return

        return {
            "api_endpoint": ignore_workflow_state,
            "api_gateway_response": ignore_workflow_state,
            "lambda": self.build_lambda,
            "schedule_trigger": ignore_workflow_state,
            "sqs_queue": ignore_workflow_state,
            "bucket": ignore_workflow_state
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
        reserved_concurrency_count = workflow_state.get('reserved_concurrency_count')

        optional_arguments = {
            "reservedConcurrency": reserved_concurrency_count,
        } if not (reserved_concurrency_count in [None, False]) else {}

        return optional_arguments

    def build_lambda(self, workflow_state):
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

        iam_role = self.build_iam_role("lambda.amazonaws.com", role_name, ws_policies)

        self.set_aws_resources({
            role_name: iam_role
        })
        return role_name

    def build_iam_role(self, principal_service, role_name, policies):
        iam_policies = self.get_iam_role_policies(role_name, policies)

        assume_role_policy_document = {
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": principal_service
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }

        return {
            "Type": "AWS::IAM::Role",
            "Properties": {
                "RoleName": role_name,
                "AssumeRolePolicyDocument": assume_role_policy_document,
                "Policies": iam_policies
            }
        }

    def get_iam_role_policies(self, role_name, policies):
        base_policy_name = role_name + "Policy"
        role_policies = []
        for n, policy in enumerate(policies):
            action = policy["action"]
            resource = policy["resource"]

            role_policies.append(
                {
                    "PolicyName": f"{base_policy_name}{n}",
                    "PolicyDocument": {
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": action,
                                "Resource": resource
                            }
                        ]
                    }
                }
            )
        return role_policies

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
        proxy_method = self.get_proxy_method(workflow_state, path_part, i)
        api_resources.update(proxy_method)

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

        api_gateway_deployment_id = self.get_id(self.deployment_id)
        api_gateway_deployment_name = f"ApiGatewayDeployment{api_gateway_deployment_id}"

        self.set_aws_resources({
            "ApiGatewayRestApi": {
                "Type": "AWS::ApiGateway::RestApi",

                # TODO: Once we have code in API to handle the teardown of this resource, we can uncomment this
                # "DeletionPolicy": "Retain",

                "Properties": {
                    "Name": f"Gateway_{project_id}"
                }
            },
            api_gateway_deployment_name: {
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

    def build_lambda_proxy_iam_role(self, lambda_id):
        policies = [
            {
                "action": "lambda:*",
                "resource": {
                    "Fn::GetAtt": [f"{lambda_id}LambdaFunction", "Arn"]
                }
            }
        ]

        role_name = lambda_id + "ApiGatewayProxyRole"

        iam_role = self.build_iam_role("apigateway.amazonaws.com", role_name, policies)

        self.set_aws_resources({
            role_name: iam_role
        })
        return role_name

    def get_proxy_method(self, workflow_state, path_part, index):
        url_resource_name = self.get_url_resource_name(path_part, index)
        http_method = workflow_state['http_method']
        raw_id = workflow_state['id']
        id_ = self.get_id(raw_id)
        base = self.app_config.get("workflow_manager_api_url")
        uri = f"{base}/deployment/{self.deployment_id}/workflow/{raw_id}"

        lambda_id = workflow_state.get("lambda_proxy")

        method_response_codes = [
            {
                "StatusCode": 200
            },
            {
                "StatusCode": 500
            }
        ]

        integration = {
            "IntegrationHttpMethod": "POST",
            "Type": "HTTP",
            "Uri": uri,
            "IntegrationResponses": method_response_codes
        }
        if lambda_id is not None:
            lambda_id = self.get_id(lambda_id)
            lambda_id = lambda_id[0].upper() + lambda_id[1:]
            role_name = self.build_lambda_proxy_iam_role(lambda_id)

            lambda_uri_format = "arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${lambdaArn}/invocations"
            integration.update({
                "Credentials": {
                    "Fn::GetAtt": [role_name, "Arn"]
                },
                "Type": "AWS_PROXY",
                "Uri": {
                    "Fn::Sub": [
                        lambda_uri_format,
                        {
                            "lambdaArn": {
                                "Fn::GetAtt": [f"{lambda_id}LambdaFunction", "Arn"]
                            }
                        }
                    ]
                }
            })

        self.api_method_ids.append(id_)

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
                    "Integration": integration,
                    "MethodResponses": method_response_codes
                }
            }
        }

    ###########################################################################
    # S3 Bucket Resource
    ###########################################################################

    def build_s3_bucket_policy(self, bucket_id):
        id_ = bucket_id + "Policy"
        policy_statement = {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": [
                "s3:GetObject"
            ],
            "Resource": f"arn:aws:s3:::{bucket_id}/*"
        }
        bucket_policy_resource = {
            "Type": "AWS::S3::BucketPolicy",
            "Properties": {
                "Bucket": {
                    "Ref": bucket_id
                },
                "PolicyDocument": {
                    "Statement": [
                        policy_statement
                    ]
                }
            }
        }
        return {
            id_: bucket_policy_resource
        }

    def build_cloudfront_distribution(self, bucket_id):
        id_ = bucket_id + "Cloudfront"
        # An identifier for the origin which must be unique within the distribution
        origin = bucket_id + "Origin"

        origin_resource = {
            "DomainName": f"{bucket_id}.s3.amazonaws.com",
            "Id": origin,
            "CustomOriginConfig": {
                "HTTPPort": 80,
                "HTTPSPort": 443,
                "OriginProtocolPolicy": "https-only"
            }
        }

        cloudfront_resource = {
            "Type": "AWS::CloudFront::Distribution",
            "Properties": {
                "DistributionConfig": {
                    "Origins": [
                        origin_resource
                    ],
                    "Enabled": "true",
                    "DefaultRootObject": "index.html",
                    "CustomErrorResponses": [
                        {
                            "ErrorCode": 404,
                            "ResponseCode": 200,
                            "ResponsePagePath": "/index.html"
                        }
                    ],
                    "DefaultCacheBehavior": {
                        "AllowedMethods": [
                            "HEAD", "DELETE", "POST", "GET", "OPTIONS", "PUT", "PATCH"
                        ],
                        "TargetOriginId": origin,
                        # Defining if and how the QueryString and Cookies are forwarded to the origin which in this case is S3
                        "ForwardedValues": {
                            "QueryString": "false",
                            "Cookies": {
                                "Forward": "none"
                            }
                        },
                        "ViewerProtocolPolicy": "redirect-to-https",
                    },
                    "ViewerCertificate": {
                        "CloudFrontDefaultCertificate": "true"
                    }
                }
            }
        }
        return {
            id_: cloudfront_resource
        }

    def build_s3_bucket(self, workflow_state):
        bucket_name = workflow_state['bucket_name']
        publish = workflow_state.get('publish')
        cors = workflow_state.get('cors')

        s3_public_properties = {}
        if publish:
            s3_public_properties = {
                "AccessControl": "PublicRead",
                "WebsiteConfiguration": {
                    "IndexDocument": "index.html",
                    "ErrorDocument": "index.html"
                }
            }

        s3_cors = {}
        if cors:
            s3_cors = {
                "CorsConfiguration": {
                    "CorsRules": [
                        {
                            "AllowedHeaders": [
                                "*"
                            ],
                            "AllowedMethods": [
                                "GET", "PUT"
                            ],
                            "AllowedOrigins": [
                                "*"
                            ]
                        }
                    ]
                }
            }

        bucket_id = self.get_id(bucket_name)
        bucket_resource = {
            "Type": "AWS::S3::Bucket",
            "Properties": {
                "BucketName": bucket_id,
                **s3_public_properties,
                **s3_cors
            }
        }

        cloudfront_resource = {}
        if publish is not None and publish:
            cloudfront_resource = self.build_cloudfront_distribution(bucket_id)

        bucket_policy_resource = self.build_s3_bucket_policy(bucket_id)

        resources = {
            bucket_id: bucket_resource,
            **bucket_policy_resource,
            **cloudfront_resource
        }
        self.set_aws_resources(resources)

        self.set_aws_outputs({
            id_: {
                "Value": {
                    "Ref": id_
                }
            } for id_ in resources.keys()})

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
