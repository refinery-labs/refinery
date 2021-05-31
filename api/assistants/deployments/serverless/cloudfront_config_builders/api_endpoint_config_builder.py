from assistants.deployments.serverless.cloudfront_config_builders.aws_config_builder import AwsConfigBuilder
from assistants.deployments.serverless.cloudfront_config_builders.iam_config_utils import build_iam_role


class ApiEndpointConfigBuilder(AwsConfigBuilder):
    def build(self, workflow_state):
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

        self.set_resources(api_resources)

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

        iam_role = build_iam_role("apigateway.amazonaws.com", role_name, policies)

        self.set_resources({
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
