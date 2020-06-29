
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

import redis
import json
import uuid
from .exc import AlreadyInvokedException, InvokeQueueEmptyException


_QUEUE_METADATA_EXPIRATION = (60 * 60 * 24)


class RefineryMemory:
    # 6 hours is the timeout here because it's the max retry
    # time for async Lambda invokes:
    # "If your Lambda function is invoked asynchronously and is throttled,
    # AWS Lambda automatically retries the throttled event for up to six
    # hours, with delays between retries."
    # https://docs.aws.amazon.com/lambda/latest/dg/concurrent-executions.html#throttling-behavior
    return_data_timeout = (60 * 60 * 6)

    json_types = [
        list,
        dict
    ]

    regular_types = [
        str,
        int,
        float,
        complex,
        bool,
    ]

    def __init__(self, in_hostname, in_password, in_port):
        self.redis_client = False
        self.hostname = in_hostname
        self.password = in_password
        self.port = in_port

    def connect(self):
        self.redis_client = redis.StrictRedis(
            host=self.hostname,
            port=self.port,
            db=0,
            socket_timeout=5,
            password=self.password,
        )

    def _get_input_data_from_redis(self, key, **kwargs):
        if not self.redis_client:
            self.connect()

        pipeline = self.redis_client.pipeline()
        pipeline.get(key)
        pipeline.delete(key)
        returned_data = pipeline.execute()

        # Raise an exception if the GET fails
        # This is how we achieve idempotency
        if returned_data[0] == None:
            raise AlreadyInvokedException()

        try:
            return json.loads(returned_data[0])
        except:
            pass

        return returned_data[0]

    def _store_return_data_to_redis(self, return_data, **kwargs):
        if not self.redis_client:
            self.connect()

        new_key = str(uuid.uuid4())

        self.redis_client.setex(
            new_key,
            self.return_data_timeout,
            json.dumps(
                return_data
            )
        )

        return new_key

    def _get_queue_input_from_redis(self, queue_insert_id, pop_number):
        """
        Pull pop_number of items off of the redis list to be thrown onto SQS.
        """
        if not self.redis_client:
            self.connect()

        # List of items pulled from redis
        return_items = []

        # Do a redis pipeline transaction
        pipeline = self.redis_client.pipeline()

        for i in range(0, pop_number):
            pipeline.lpop("SQS_QUEUE_DATA_" + queue_insert_id)

        returned_data_list = pipeline.execute()

        for return_data in returned_data_list:
            if return_data != None:
                try:
                    return_data = json.loads(
                        return_data
                    )
                except:
                    pass
                return_items.append(
                    return_data
                )

        return return_items

    def _get_queue_url(self, queue_insert_id):
        if not self.redis_client:
            self.connect()

        return self.redis_client.get(
            "SQS_TARGET_QUEUE_URL_" + queue_insert_id
        )

    def _get_queue_backpack(self, queue_insert_id):
        if not self.redis_client:
            self.connect()

        return json.loads(
            self.redis_client.get(
                "SQS_BACKPACK_DATA_" + queue_insert_id
            )
        )

    def _set_queue_data(self, queue_url, queue_items, backpack):
        if not self.redis_client:
            self.connect()

        # Generate a unique ID
        queue_insert_id = str(uuid.uuid4())

        # Generate a queue storage ID
        queue_storage_id = "SQS_QUEUE_DATA_" + queue_insert_id

        # Generate a redis key for storing the queue URL
        sqs_target_queue_url = "SQS_TARGET_QUEUE_URL_" + queue_insert_id

        # Generate a redis key for the backpack
        sqs_backpack_key = "SQS_BACKPACK_DATA_" + queue_insert_id

        # Do a redis pipeline transaction
        pipeline = self.redis_client.pipeline()

        # JSON-encode queue items
        for i in range(0, len(queue_items)):
            queue_items[i] = json.dumps(
                queue_items[i]
            )

        # Set the queue URL
        pipeline.setex(
            sqs_target_queue_url,
            _QUEUE_METADATA_EXPIRATION,  # 1-Day expiration
            queue_url
        )

        # Set the backpack
        pipeline.setex(
            sqs_backpack_key,
            _QUEUE_METADATA_EXPIRATION,  # 1-Day expiration
            json.dumps(
                backpack
            )
        )

        # Set expiration of items
        pipeline.expire(
            queue_storage_id,
            _QUEUE_METADATA_EXPIRATION,  # 1-Day expiration
        )

        pipeline.execute()

        # This is the batch size (the amount of queue items
        # that we put into Redis in a single transaction)
        SQS_BATCH_SIZE = (1000 * 10)

        # We have to batch these up so that we can process
        # extremely large return data.
        while len(queue_items) > 0:
            # Current batch of items to be put in redis
            queue_current_item_batch = queue_items[:SQS_BATCH_SIZE]

            # Remove the items from the queue items
            queue_items = queue_items[SQS_BATCH_SIZE:]

            # Do a redis pipeline transaction
            pipeline = self.redis_client.pipeline()

            # Store all the queue data in redis in a list
            pipeline.rpush(
                queue_storage_id,
                *queue_current_item_batch
            )

            pipeline.execute()

        return queue_insert_id

    def _set_fan_in_data(self, fan_out_id, invocation_list, **kwargs):
        if not self.redis_client:
            self.connect()

        # Generate an invocation array ID
        invocation_array_id = "INVOCATION_QUEUE_" + str(uuid.uuid4())

        # Do a redis pipeline transaction
        pipeline = self.redis_client.pipeline()

        # Set up the counter for fan-in
        pipeline.setex(
            "FAN_IN_COUNTER_" + fan_out_id,
            self.return_data_timeout,
            len(invocation_list)
        )

        # Store all invocation data in redis in a list
        pipeline.rpush(
            invocation_array_id,
            *invocation_list
        )

        # Set expiration of items
        pipeline.expire(
            invocation_array_id,
            _QUEUE_METADATA_EXPIRATION,  # 1-Day expiration
        )

        returned_data = pipeline.execute()

        return invocation_array_id

    def _get_invocation_input_from_queue(self, invocation_id):
        """
        Pops an invocation input off of the array.

        If the array has been exhausted then it raises InvokeQueueEmptyException
        """
        if not self.redis_client:
            self.connect()

        # Do a redis pipeline transaction
        pipeline = self.redis_client.pipeline()

        pipeline.lpop(invocation_id)

        returned_data = pipeline.execute()

        if returned_data[0] == None:
            raise InvokeQueueEmptyException()

        return json.loads(returned_data[0])

    def _fan_in_get_results_data(self, fan_out_id, **kwargs):
        """
        Gets the fan-in data and deletes it immediately
        """
        if not self.redis_client:
            self.connect()

        # Do a redis pipeline transaction
        pipeline = self.redis_client.pipeline()

        # Get array of returned data from fan-in
        pipeline.lrange(
            "FAN_IN_RESULTS_" + fan_out_id,
            0,
            -1
        )

        # Delete the return data
        pipeline.delete(
            "FAN_IN_RESULTS_" + fan_out_id
        )

        returned_data = pipeline.execute()

        # Raise an exception if the GET fails
        # This is how we achieve idempotency
        if returned_data[0] == None:
            raise AlreadyInvokedException()

        # Decode returned data
        decoded_return_data = []

        # Combine all of the collective backpacks into one
        # final backpack. Colliding keys are overwritten.
        combined_backpack = {}

        for returned_data_segment in returned_data[0]:
            returned_data_dict = json.loads(
                returned_data_segment
            )

            if type(returned_data_dict) == dict:
                for backpack_key, backpack_value in returned_data_dict["backpack"].iteritems():
                    combined_backpack[backpack_key] = backpack_value

            # Try to JSON-decode each segment
            decoded_return_data.append(
                returned_data_dict["output"]
            )

        return {
            "input_data": decoded_return_data,
            "backpack": combined_backpack
        }

    def _fan_in_operations(self, fan_out_id, return_data, backpack, **kwargs):
        """
        This function either returns False if we're not the last Lambda
        in the fan-in to be invoked or it returns a key of the data to be
        passed to the next function after the fan-in as input.
        """
        if not self.redis_client:
            self.connect()

        # Do a redis pipeline transaction
        pipeline = self.redis_client.pipeline()

        # Push return data into redis
        pipeline.lpush(
            "FAN_IN_RESULTS_" + fan_out_id,
            json.dumps({
                "backpack": backpack,
                "output": return_data
            })
        )

        # Update expiration
        pipeline.expire(
            "FAN_IN_RESULTS_" + fan_out_id,
            self.return_data_timeout,
        )

        # Decrement fan-in counter
        pipeline.decr(
            "FAN_IN_COUNTER_" + fan_out_id
        )

        # Get fan-in counter latest value
        pipeline.get(
            "FAN_IN_COUNTER_" + fan_out_id
        )

        returned_data = pipeline.execute()

        # Check fan-in counter value
        # If it's zero, we must move to invoke the next function
        fan_in_counter_result = int(returned_data[3])

        if fan_in_counter_result == 0:
            # Clean up previous data
            pipeline = self.redis_client.pipeline()

            # Delete fan-in counter
            pipeline.delete(
                "FAN_IN_COUNTER_" + fan_out_id
            )

            returned_data = pipeline.execute()

            return "FAN_IN_RESULTS_" + fan_out_id

        return False

    def _bulk_store_input_data(self, lambda_invocation_list):
        """
        Uses a redis pipeline to quickly store all the input data
        in the input lambda_invocation_list and replace "input_data"
        with a redis key for each.
        """
        if not self.redis_client:
            self.connect()

        # Do a redis pipeline transaction
        pipeline = self.redis_client.pipeline()

        for i in range(0, len(lambda_invocation_list)):
            new_input_data_key = str(uuid.uuid4())

            pipeline.setex(
                new_input_data_key,
                self.return_data_timeout,
                json.dumps({
                    "input_data": lambda_invocation_list[i]["input_data"],
                    "backpack": lambda_invocation_list[i]["backpack"]
                })
            )

            del lambda_invocation_list[i]["input_data"]
            lambda_invocation_list[i]["input_data_key"] = new_input_data_key

        # Execute in one quick transaction
        returned_data = pipeline.execute()

        return lambda_invocation_list

    def _store_and_check_if_merge(self, hset_name, branch_ids, current_lambda_arn, merge_lambda_arns, backpack, return_data):
        # Do a redis pipeline transaction
        pipeline = self.redis_client.pipeline()

        # Store return data in HASH
        pipeline.hset(
            hset_name,
            current_lambda_arn,
            json.dumps({
                "backpack": backpack,
                "return_data": return_data,
                "branch_ids": branch_ids,
            })
        )

        # Set expiration for the HASH
        pipeline.expire(
            hset_name,
            _QUEUE_METADATA_EXPIRATION
        )

        # Get the keys of the HASH after our HSET to see if we're the final
        # Lambda in the merge set.
        pipeline.hkeys(
            hset_name
        )

        # Execute in one quick transaction
        hset_returned_data = pipeline.execute()

        # Determine if we've the last Lambda in the merge
        # by the number of merge Lambdas and comparing it to the number of
        # HASH keys returned from HKEYS
        lambda_return_values_list = hset_returned_data[2]

        return len(lambda_return_values_list) == len(merge_lambda_arns)

    def _get_merge_data(self, hset_name, branch_ids):
        # Since we're the last Lambda in the merge we'll pull it all out.
        pipeline = self.redis_client.pipeline()
        pipeline.hvals(
            hset_name
        )
        pipeline.delete(
            hset_name
        )
        returned_data = pipeline.execute()
        lambda_return_metadata_list = returned_data[0]

        # Combine the backpacks and generate a list of return values
        return_values = []
        combined_backpack = {}

        for lambda_return_metadata in lambda_return_metadata_list:
            returned_data_dict = json.loads(
                lambda_return_metadata
            )

            for branch_id in returned_data_dict["branch_ids"]:
                if not (branch_id in branch_ids):
                    branch_ids.insert(0, branch_id)

            for backpack_key, backpack_value in returned_data_dict["backpack"].iteritems():
                combined_backpack[backpack_key] = backpack_value

            return_values.append(
                returned_data_dict["return_data"]
            )

        return {
            "backpack": combined_backpack,
            "return_data": return_values,
            "branch_ids": branch_ids,
        }

    def _merge_store_result(self, execution_id, branch_ids, target_lambda_arn, current_lambda_arn, merge_lambda_arns, backpack, return_data):
        """
        Uses a redis pipeline to store the results at an HASH of the following name:
        {{EXECUTION_ID}}{{TARGET_LAMBDA_ARN}} = {
                "{{CURRENT_RUNNING_LAMBDA_ARN}}": "{{RETURN_DATA}}"
        }

        If we're the last Lambda in the merge then we return the return_data to be
        passed as input to the target Lambda for the merge. Otherwise we return None.
        """
        if not self.redis_client:
            self.connect()

        # Create HSET name
        hset_name = execution_id + "_" + \
            target_lambda_arn + "_" + branch_ids[-1]

        # Store the merge data and check if we should merge
        should_merge = self._store_and_check_if_merge(
            hset_name,
            branch_ids,
            current_lambda_arn,
            merge_lambda_arns,
            backpack,
            return_data
        )

        # If we don't need to merge, we can stop here.
        if not should_merge:
            return None

        # Pull the merge data from redis and return it
        return self._get_merge_data(
            hset_name,
            branch_ids
        )
