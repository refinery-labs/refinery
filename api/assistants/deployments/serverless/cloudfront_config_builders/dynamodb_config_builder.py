from assistants.deployments.serverless.cloudfront_config_builders.aws_config_builder import AwsConfigBuilder
from assistants.deployments.serverless.utils import slugify


class DynamoDBConfigBuilder(AwsConfigBuilder):
    def build(self, workflow_state):
        # TODO (cthompson) create these tables with PointInTimeRecoverySpecification
        return {
            "Type": "AWS::DynamoDB::Table",
            "Properties": {
                "TableName": slugify(workflow_state["name"]),
                "AttributeDefinitions": [
                    {
                        "AttributeName": "Key",
                        "AttributeType": "S"
                    }
                ],
                "KeySchema": [
                    {
                        "AttributeName": "Key",
                        "KeyType": "HASH"
                    }
                ],
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 10,
                    "WriteCapacityUnits": 10
                }
            }
        }
