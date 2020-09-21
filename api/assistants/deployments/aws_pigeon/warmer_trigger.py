import json

from tornado import gen

from assistants.deployments.aws_pigeon.aws_workflow_state import AwsWorkflowState
from utils.general import get_random_node_id, logit, split_list_into_chunks


@gen.coroutine
def create_warmer_for_lambda_set(task_spawner, credentials, warmup_concurrency_level, unique_deploy_id, combined_warmup_list):
    # Create Lambda warmers if enabled
    warmer_trigger_name = "WarmerTrigger" + unique_deploy_id
    logit("Deploying auto-warmer CloudWatch rule...")
    warmer_trigger_result = yield task_spawner.create_cloudwatch_rule(
        credentials,
        get_random_node_id(),
        warmer_trigger_name,
        "rate(5 minutes)",
        "A CloudWatch Event trigger to keep the deployed Lambdas warm.",
        "",
    )

    # Go through all the Lambdas deployed and make them the targets of the
    # warmer Lambda so everything is kept hot.
    # Additionally we'll invoke them all once with a warmup request so
    # that they are hot if hit immediately
    for deployed_lambda in combined_warmup_list:
        yield task_spawner.add_rule_target(
            credentials,
            warmer_trigger_name,
            deployed_lambda["name"],
            deployed_lambda["arn"],
            json.dumps({
                "_refinery": {
                    "warmup": warmup_concurrency_level,
                }
            })
        )

        task_spawner.warm_up_lambda(
            credentials,
            deployed_lambda["arn"],
            warmup_concurrency_level
        )

    raise gen.Return({
        "id": warmer_trigger_result["id"],
        "name": warmer_trigger_name,
        "arn": warmer_trigger_result["arn"]
    })


@gen.coroutine
def add_auto_warmup(task_spawner, credentials, warmup_concurrency_level, unique_deploy_id, combined_warmup_list):
    # Split warmup list into a list of lists with each list containing five elements.
    # This is so that we match the limit for CloudWatch Rules max targets (5 per rule).
    # See "Targets" under this following URL:
    # https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/cloudwatch_limits_cwe.html
    split_combined_warmup_list = split_list_into_chunks(
        combined_warmup_list,
        5
    )

    # Ensure each Cloudwatch Rule has a unique name
    warmup_unique_counter = 0

    warmup_futures = []

    for warmup_chunk_list in split_combined_warmup_list:
        warmup_futures.append(
            create_warmer_for_lambda_set(
                task_spawner,
                credentials,
                warmup_concurrency_level,
                unique_deploy_id + "_W" + str(warmup_unique_counter),
                warmup_chunk_list
            )
        )

        warmup_unique_counter += 1

    # Wait for all of the concurrent Cloudwatch Rule creations to finish
    warmer_triggers = yield warmup_futures
    raise gen.Return(warmer_triggers)


class WarmerTriggerWorkflowState(AwsWorkflowState):
    pass
