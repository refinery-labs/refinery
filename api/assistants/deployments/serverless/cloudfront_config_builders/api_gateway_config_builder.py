from functools import cached_property

from assistants.deployments.serverless.cloudfront_config_builders.aws_config_builder import AwsConfigBuilder


class ApiGatewayConfigBuilder(AwsConfigBuilder):
    def build(self, workflow_state):
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

        self.set_resources({
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

        self.set_outputs({
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

    @cached_property
    def api_method_ids(self):
        return [
            id_
            for id_, resource in self.current_resources.items()
            if resource["Type"] == "AWS::ApiGateway::Method"
        ]
