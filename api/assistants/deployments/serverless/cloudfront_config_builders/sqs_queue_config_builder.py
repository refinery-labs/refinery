from assistants.deployments.serverless.cloudfront_config_builders.aws_config_builder import AwsConfigBuilder
from assistants.deployments.serverless.utils import get_unique_workflow_state_name, slugify


class SqsQueueConfigBuilder(AwsConfigBuilder):
    def build(self, workflow_state):
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

        self.outputs = {
            id_: {
                "Value": {
                    "Ref": id_
                }
            }
        }
