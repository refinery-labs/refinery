
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
import sys


from .constants import gmemory


def _send_sqs_message_in_batches(sqs_url, sqs_message_list):
    sqs_message_list = sqs_message_list
    new_sqs_client = boto3.client("sqs")

    while True:
        # Pull last ten messages off the list
        message_batch = sqs_message_list[-10:]

        # Remove them from the original messages
        sqs_message_list = sqs_message_list[:-10]

        if len(message_batch) == 0:
            break

        _send_sqs_messages(
            new_sqs_client,
            sqs_url,
            message_batch
        )

        if len(sqs_message_list) == 0:
            break

    raise SystemExit


def _send_sqs_messages(sqs_client, sqs_url, sqs_message_list):
    sqs_entries = []

    # Generate SQS entries
    for sqs_message in sqs_message_list:
        sqs_entries.append({
            "Id": str(uuid.uuid4()),
            "MessageBody": json.dumps(
                sqs_message
            )
        })

    response = sqs_client.send_message_batch(
        QueueUrl=sqs_url,
        Entries=sqs_entries
    )


def _spawn_off_sqs_worker(queue_url, queue_insert_id, execution_id, branch_ids, fan_out_ids):
    exhausted_queue = False
    new_thread = False

    queue_items = gmemory._get_queue_input_from_redis(
        queue_insert_id,
        100
    )

    enriched_queue_items = []

    # Add metadata to queue items
    for queue_item in queue_items:
        enriched_queue_items.append({
            "_refinery": {
                "queue_insert_id": queue_insert_id,
                "execution_id": execution_id,
                "branch_ids": branch_ids,
                "fan_out_ids": fan_out_ids,
                "input_data": queue_item,
            }
        })

    if len(enriched_queue_items) == 0:
        exhausted_queue = True
    else:
        new_thread = threading.Thread(
            target=_send_sqs_message_in_batches,
            args=(
                queue_url,
                enriched_queue_items
            )
        )

        new_thread.start()

        # Wedge for Boto3 bug: https://github.com/boto/botocore/issues/1246
        time.sleep(0.2)

    return {
        "thread": new_thread,
        "exhausted_queue": exhausted_queue
    }


def _sqs_worker(queue_insert_id, execution_id, branch_ids, fan_out_ids, context):
    """
    An SQS worker takes the messages stored in Redis and loads them into
    an SQS queue. The Refinery "magic" which takes place is the ability to
    return a large number of items (e.g. 100K, 1M) from a code block and have
    them all be loaded into SQS without any additional code. Of course, this is
    not quite so simple to do in implementation. SQS allows a maximum of 10 messages
    to be stored in the queue per API request. While the throughput is unlimited, it
    would almost certainly take longer than the max-timeout of a given Lambda to store
    all of this data in SQS. So instead we opt for loading all of the data into redis
    first (very fast) and then self-invoke the Lambda in the SQS Worker mode. The SQS
    Worker mode just pulls things off of the redis queue and loads them into SQS 10
    messages at a time. If the timeout for the function is close at hand the SQS worker
    will automatically finish it's current load and then invoke itself again to extend
    the work infinitely until it is done.

    Basically the steps are the following:
    * A Code Block returns a large array of values to be stored in SQS.
    * The custom runtime receives this array and stores it in redis as a list (fast).
    * The custom runtime self-invokes as many SQS workers as calculated to be necessary.
    * The SQS workers pull 10 messages a time out (multi-threaded) of redis and insert them into SQS
    * Upon getting close to their timeout the SQS workers finish up and then invoke themselves
    * This continues until the redis list has been exhaused.

    Each SQS worker can do 10 messages at a time, and this is multi-threaded.
    Performance measurements show the ideal thread number to be 15. Using this
    we can achieve about 1K SQS inserts per 2.5 seconds (for every worker instance).

    Assuming ~400 inserts a second, that's 24K a minute (and 360K in 15 minutes).
    5 SQS workers is 120K a minute
    10 SQS works is 240K a minute
    """

    print("I'm an SQS worker spawned with queue_insert_id of: " + queue_insert_id)
    sys.stdout.flush()

    # If we have less than or equal to ten seconds of
    # remaining runtime we should quit out.
    remaining_time_limit = (1000 * 10)

    # Get target queue URL
    queue_url = gmemory._get_queue_url(
        queue_insert_id
    )

    # 15 is about the golden number of effective threads
    max_threads = 15

    while True:
        active_threads = []
        exhausted_queue = False

        # Spawn up threads to put things on SQS
        for i in range(0, max_threads):
            if exhausted_queue == False:
                worker_spawn_data = _spawn_off_sqs_worker(
                    queue_url,
                    queue_insert_id,
                    execution_id,
                    branch_ids,
                    fan_out_ids
                )

                if worker_spawn_data["thread"]:
                    active_threads.append(
                        worker_spawn_data["thread"]
                    )

                if worker_spawn_data["exhausted_queue"]:
                    exhausted_queue = True

        # Wait until all threads finish
        for thread in active_threads:
            thread.join()

        # If we've finished up our queue we should quit out
        if exhausted_queue:
            break

        # Now check how much time we have left before timeout
        remaining_milliseconds = context.get_remaining_time_in_millis()
        if remaining_milliseconds <= remaining_time_limit:
            # Self invoke and quit
            lambda_client = boto3.client(
                "lambda"
            )

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
            break
    return
