
"""
Copyright (C) Refinery Labs Inc. - All Rights Reserved

NOTICE: All information contained herein is, and remains
the property of Refinery Labs Inc. and its suppliers,
if any. The intellectual and technical concepts contained
herein are proprietary to Refinery Labs Inc.
and its suppliers and may be covered by U.S. and Foreign Patents,
patents in process, and are protected by trade secret or copyright law.
Dissemination of this information or reproduction of this material
is strictly forbidden unless prior written permission is obtained
from Refinery Labs Inc.
"""

import threading
import boto3
import time
import json
import uuid
import math


from .constants import gmemory


def get_branch_id_from_invoke_queue(invoke_queue):
    """
    This takes an invoke queue and analyzes it to see
    if we need to produce a new branch_id. If we do then
    it returns a new branch_id, if not it returns False.
    """

    # Types of transitions to be counted for merges
    countable_merge_transition_types = [
        "lambda",
        "sns_topic",
        "sqs_queue",
        "merge"
    ]

    # Count of the number of spawns (that match our types)
    number_of_spawns = 0

    for invoke_queue_item in invoke_queue:
        if invoke_queue_item["type"] in countable_merge_transition_types:
            number_of_spawns += 1

    # If we're not branching no new branch ID is needed and
    # we just return a False
    if number_of_spawns <= 1:
        return False

    # If the invoke_queue has more than one item it means we are branching
    # so we'll add another branch_id to the branch_ids list.
    return str(uuid.uuid4())

def get_merge_invoke_data(new_invoke_data):
    merge_result = gmemory._merge_store_result(
        new_invoke_data["execution_id"],
        new_invoke_data["branch_ids"],
        new_invoke_data["arn"],
        new_invoke_data["invoked_function_arn"],
        new_invoke_data["merge_lambdas"],
        new_invoke_data["backpack"],
        new_invoke_data["input_data"]
    )

    if merge_result == None:
        return merge_result

    # Pull the shared branch IDs from redis
    new_invoke_data["branch_ids"] = merge_result["branch_ids"]

    # Remove the last branch ID
    new_invoke_data["branch_ids"] = new_invoke_data["branch_ids"][1:]

    # If the return value was not None that means it's the final
    # Lambda in the merge and we can do a "then" transition with
    # the combined array of results as the input.
    new_invoke_data = {
        "branch_ids": new_invoke_data["branch_ids"],
        "backpack": merge_result["backpack"],
        "execution_id": new_invoke_data["execution_id"],
        "fan_out_ids": new_invoke_data["fan_out_ids"],
        "type": "merge",
        "arn": new_invoke_data["arn"],
        "input_data": json.loads(
            json.dumps(
                merge_result["return_data"]
            )
        )
    }

    return new_invoke_data


def _parallel_invoke(branch_ids, invoke_queue):
    # List of active threads
    active_threads = []

    # Maximum number of threads
    max_threads = 50

    # Invokes a Lambda directly with input_data asynchronously
    def lambda_invoker_worker_direct_input(execution_id, branch_ids, fan_out_ids, arn, input_data):
        return_wrapper_data = {
            "_refinery": {
                "branch_ids": branch_ids,
                "input_data": input_data,
                "parallel": False,
                "execution_id": execution_id,
                "fan_out_ids": fan_out_ids,
            }
        }

        lambda_client = boto3.client(
            "lambda"
        )

        response = lambda_client.invoke(
            FunctionName=arn,
            InvocationType="Event",
            LogType="None",
            Payload=json.dumps(
                return_wrapper_data
            )
        )

        raise SystemExit

    # Invokes a Lambda asynchronously
    def lambda_invoker_worker_redis(execution_id, branch_ids, fan_out_ids, arn, return_key):
        return_wrapper_data = {
            "_refinery": {
                "branch_ids": branch_ids,
                "indirect": {
                    "type": "redis",
                            "key": return_key,
                },
                "parallel": False,
                "execution_id": execution_id,
                "fan_out_ids": fan_out_ids,
            }
        }

        lambda_client = boto3.client(
            "lambda"
        )

        response = lambda_client.invoke(
            FunctionName=arn,
            InvocationType="Event",
            LogType="None",
            Payload=json.dumps(
                return_wrapper_data
            )
        )

        raise SystemExit

    # Self-invocation for a fan-out transition
    def lambda_invoker_fan_out(arn, return_key, invocation_id, branch_ids):
        return_wrapper_data = {
            "_refinery": {
                "branch_ids": branch_ids,
                "invoke": invocation_id,
                "indirect": {
                    "type": "redis",
                            "key": return_key,
                },
                "parallel": False
            }
        }

        lambda_client = boto3.client(
            "lambda"
        )

        response = lambda_client.invoke(
            FunctionName=arn,
            InvocationType="Event",
            LogType="None",
            Payload=json.dumps(
                return_wrapper_data
            )
        )

        raise SystemExit

    # Invokes a Lambda asynchronously with fan-in results as input
    def lambda_invoker_worker_fan_in(execution_id, branch_ids, fan_out_ids, arn, fan_out_id):
        return_wrapper_data = {
            "_refinery": {
                "branch_ids": branch_ids,
                "indirect": {
                    "type": "redis_fan_in",
                            "key": fan_out_id,
                },
                "parallel": False,
                "execution_id": execution_id,
                "fan_out_ids": fan_out_ids,
            }
        }

        lambda_client = boto3.client(
            "lambda"
        )

        response = lambda_client.invoke(
            FunctionName=arn,
            InvocationType="Event",
            LogType="None",
            Payload=json.dumps(
                return_wrapper_data
            )
        )

        raise SystemExit

    # Mass-inserts return data into SQS queue
    def sqs_insert_data(execution_id, branch_ids, fan_out_ids, arn, input_data, backpack, context):
        # Generate queue URL from SQS ARN
        arn_parts = arn.split(":")
        queue_url = "https://sqs." + \
            arn_parts[3] + ".amazonaws.com/" + \
            arn_parts[4] + "/" + arn_parts[5]

        queue_items = input_data

        if type(input_data) != list:
            queue_items = [
                input_data
            ]

        # Insert all the data into redis as a temporary holding zone
        queue_insert_id = gmemory._set_queue_data(
            queue_url,
            queue_items,
            backpack
        )

        # We calculate the number of workers to spin up by
        # having a target of 1 minute of time to fill up the SQS
        # queue with the messages previously stored in redis.
        # This is to balance the additional invoke and compute
        # cost with the speed of insertion into SQS.
        # A multi-threaded SQS worker generally can insert at a
        # rate of 400 messages per second.

        number_of_workers = len(queue_items) / \
            (400 * 60)  # 400/sec for 60 seconds
        number_of_workers = int(math.ceil(number_of_workers))

        # We cap the number of workers at 20 just to make the cost
        # reasonable
        if number_of_workers > 20:
            number_of_workers = 20

        # If the float is to small it will occassionally be brought
        # down to zero so we set a minimum of one worker
        if number_of_workers < 1:
            number_of_workers = 1

        lambda_client = boto3.client(
            "lambda"
        )

        # Invoke data for the self-invokes to spawn SQS workers
        for i in range(0, number_of_workers):
            lambda_invoke_data = {
                "_refinery": {
                    "sqs_worker": {
                        "branch_ids": branch_ids,
                        "queue_insert_id": queue_insert_id,
                        "execution_id": execution_id,
                        "fan_out_ids": fan_out_ids,
                    }
                }
            }

            response = lambda_client.invoke(
                FunctionName=context.invoked_function_arn,
                InvocationType="Event",
                LogType="None",
                Payload=json.dumps(
                    lambda_invoke_data
                )
            )

            # Check how much runway we have. If it's less than five seconds
            # we'll dip out and it'll just have to be a slower drip into SQS.
            # This is after the first-invoke intentionally so that we always
            # have at least one going.
            if context.get_remaining_time_in_millis() <= (5 * 1000):
                break

        raise SystemExit

    # Publishes to an SNS topic
    def sns_topic_publish_worker(execution_id, branch_ids, fan_out_ids, arn, input_data, backpack):
        # Handle large data that won't fit in the 256K SNS max size
        sns_client = boto3.client(
            "sns"
        )

        return_wrapper_data = {
            "_refinery": {
                "branch_ids": branch_ids,
                "indirect": False,
                "parallel": False,
                "execution_id": execution_id,
                "fan_out_ids": fan_out_ids,
                "input_data": input_data,
                "backpack": backpack
            }
        }

        response = sns_client.publish(
            TopicArn=arn,
            Message=json.dumps(
                return_wrapper_data
            )
        )

        raise SystemExit

    # Publishes to redis to be picked up by a polling API Gateway Lambda
    def api_gateway_response(execution_id, input_data):
        if input_data == False:
            input_data = "<FIX_REDIS_FALSE_BOOL_PASSING_ISSUE>"

        # Store with expiration in redis
        gmemory.redis_client.setex(
            execution_id,
            gmemory.return_data_timeout,
            json.dumps(
                input_data
            )
        )

        raise SystemExit

    # Spawns a new worked and adds it to active_threads
    def spawn_new_worker():
        # Types that equate to just a "lambda" type execution
        lambda_equivalent_types = [
            "lambda",
            "merge",
            "fan_out_execution"
        ]

        new_invoke_data = invoke_queue.pop()

        # Check type and invoke appropriately
        if (new_invoke_data["type"] in lambda_equivalent_types) and "input_data_key" in new_invoke_data:
            new_thread = threading.Thread(
                target=lambda_invoker_worker_redis,
                args=(
                    new_invoke_data["execution_id"],
                    new_invoke_data["branch_ids"],
                    new_invoke_data["fan_out_ids"],
                    new_invoke_data["arn"],
                    new_invoke_data["input_data_key"]
                )
            )
            new_thread.start()
            time.sleep(0.05)  # Annoying wedge due to boto3 bug
        elif (new_invoke_data["type"] in lambda_equivalent_types) and "input_data" in new_invoke_data:
            new_thread = threading.Thread(
                target=lambda_invoker_worker_direct_input,
                args=(
                    new_invoke_data["execution_id"],
                    new_invoke_data["branch_ids"],
                    new_invoke_data["fan_out_ids"],
                    new_invoke_data["arn"],
                    new_invoke_data["input_data"]
                )
            )
            new_thread.start()
            time.sleep(0.05)  # Annoying wedge due to boto3 bug
        elif new_invoke_data["type"] == "lambda_fan_out":
            new_thread = threading.Thread(
                target=lambda_invoker_fan_out,
                args=(
                    new_invoke_data["arn"],
                    new_invoke_data["input_data_key"],
                    new_invoke_data["invocation_id"],
                    new_invoke_data["branch_ids"],
                )
            )
            new_thread.start()
            time.sleep(0.05)  # Annoying wedge due to boto3 bug
        elif new_invoke_data["type"] == "lambda_fan_in":
            new_thread = threading.Thread(
                target=lambda_invoker_worker_fan_in,
                args=(
                    new_invoke_data["execution_id"],
                    new_invoke_data["branch_ids"],
                    new_invoke_data["fan_out_ids"],
                    new_invoke_data["arn"],
                    new_invoke_data["fan_out_id"]
                )
            )
            new_thread.start()
            time.sleep(0.05)  # Annoying wedge due to boto3 bug
        elif new_invoke_data["type"] == "sns_topic":
            new_thread = threading.Thread(
                target=sns_topic_publish_worker,
                args=(
                    new_invoke_data["execution_id"],
                    new_invoke_data["branch_ids"],
                    new_invoke_data["fan_out_ids"],
                    new_invoke_data["arn"],
                    new_invoke_data["input_data"],
                    new_invoke_data["backpack"]
                )
            )
            new_thread.start()
            time.sleep(0.05)  # Annoying wedge due to boto3 bug
        elif new_invoke_data["type"] == "api_gateway_response":
            new_thread = threading.Thread(
                target=api_gateway_response,
                args=(
                    new_invoke_data["execution_id"],
                    new_invoke_data["input_data"]
                )
            )
            new_thread.start()
        elif new_invoke_data["type"] == "sqs_queue":
            new_thread = threading.Thread(
                target=sqs_insert_data,
                args=(
                    new_invoke_data["execution_id"],
                    new_invoke_data["branch_ids"],
                    new_invoke_data["fan_out_ids"],
                    new_invoke_data["arn"],
                    new_invoke_data["input_data"],
                    new_invoke_data["backpack"],
                    new_invoke_data["context"],
                )
            )
            new_thread.start()
            time.sleep(0.05)  # Annoying wedge due to boto3 bug
        else:
            raise Exception("No known handler for invocation: " +
                            json.dumps(new_invoke_data))

        return new_thread

    # Bug fix
    lambda_client = boto3.client(
        "lambda"
    )

    # First iterate over all the invocations and load the input data
    # into redis in a single transaction/pipeline to speed it up.
    new_invoke_queue = []

    # Create a special list for Lambdas to load the input data at once
    lambda_invoke_list = []

    # If it's necessary, get the new branch ID
    new_branch_id = get_branch_id_from_invoke_queue(
        invoke_queue
    )

    while len(invoke_queue) > 0:
        new_invoke_data = invoke_queue.pop()

        # Copy in the branch IDs
        new_invoke_data["branch_ids"] = json.loads(
            json.dumps(
                branch_ids
            )
        )

        # If we have a new branch ID, add it to the list of branch IDs
        # This only occurs when we have a new branch of execution (e.g.
        # we have two Lambdas spawned from one Lambda).
        if new_branch_id:
            new_invoke_data["branch_ids"].insert(0, new_branch_id)

        # If it's a merge transition, then pop off the last branch ID
        if new_invoke_data["type"] == "merge":
            new_invoke_data = get_merge_invoke_data(
                new_invoke_data
            )

            # If the merge result was None there's no additional invocation
            # to be made here so we can skip this loop.
            if new_invoke_data == None:
                continue

        if new_invoke_data["type"] == "lambda" or new_invoke_data["type"] == "lambda_fan_out":
            lambda_invoke_list.append(
                new_invoke_data
            )
        else:
            new_invoke_queue.append(
                new_invoke_data
            )

    # Process the Lambda's input_data
    # input_data is replaced with return_key
    lambda_invoke_list = gmemory._bulk_store_input_data(
        lambda_invoke_list
    )

    # Combine resulting lists
    invoke_queue = new_invoke_queue + lambda_invoke_list

    # Keep looping while there's still Lambdas to invoke
    while len(invoke_queue) > 0:
        # If we've not maxing out acive threads then spawn new ones
        if len(active_threads) < max_threads:
            active_threads.append(
                spawn_new_worker()
            )
        else:
            # Iterate over our active threads and remove finished
            new_active_thread_list = []
            already_spawned = False

            # Check if any threads are finished
            for active_thread in active_threads:
                if active_thread.is_alive():
                    new_active_thread_list.append(active_thread)
                elif already_spawned == False:
                    new_active_thread_list.append(
                        spawn_new_worker()
                    )
                    already_spawned = True

            active_threads = new_active_thread_list

    # Wait until all threads finish
    for thread in active_threads:
        thread.join()

    # We're all done
    return


