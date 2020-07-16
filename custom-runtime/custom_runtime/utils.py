
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


import base64
import boto3
import datetime
import json
import subprocess
import os
import sys
import time
import uuid


from urlparse import parse_qs


from .exc import AlreadyInvokedException, InvokeQueueEmptyException
from .constants import gmemory, S3_CLIENT
from .parallel_invoke import _parallel_invoke


def _api_endpoint(lambda_input, execution_id, context):
    # This will spin and continually query redis until either
    # we time out without getting our HTTP response OR we return
    # our response to the client.

    # Continually loop until we have only two seconds left
    # Max execution time is 30 seconds, so that's 28 seconds
    timed_out = True

    # As long as we have ~2 seconds of runway left continue
    # to query redis for our HTTP response data.
    while context.get_remaining_time_in_millis() > (2 * 1000):
        try:
            http_response = gmemory._get_input_data_from_redis(
                execution_id
            )
        except AlreadyInvokedException as e:
            http_response = False

        # When we have a non-False http_response we can
        # break out of the loop and declare we've not timed out.
        if http_response != False:
            timed_out = False
            break

        # Wait a moment before checking again
        time.sleep(0.01)

    # If it matches our magic value, replace the response
    # with "False" instead. This is to get around an issue with
    # the Python redis library using "False" as a "not found" default
    # value. So this is how we distinguish the difference.
    if http_response == "<FIX_REDIS_FALSE_BOOL_PASSING_ISSUE>":
        http_response = False

    # We've timed out, return an error
    if timed_out:
        return {
            "statusCode": 504,
            "headers": {},
            "body": json.dumps({
                "msg": "The request to the backend has timed out.",
                "success": False
            }),
            "isBase64Encoded": False
        }

    # Check if the response is actually in an API Gateway already
    # If not return as just regular JSON, if it is then return raw
    if type(http_response) == dict and "body" in http_response:
        return http_response

    # Return JSON response with the data
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "X-Frame-Options": "deny",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Server": "refinery"
        },
        "body": json.dumps(http_response),
        "isBase64Encoded": False
    }


def _write_temporary_execution_results(s3_log_bucket, program_output, return_data):
    """
    This is for getting around all of Lambda's extremely painful limitations
    when you run something manually, mainly:
    * Truncation of output data
    * Truncation of return data
    * Slow writing/flushing to Cloudwatch to retrieve output data

    This function is called when you pass special input to the Lambda
    (Code Block) when running it. It will cause the return data to
    indicate that the results are stored in S3.
    """

    unique_id = str(uuid.uuid4())

    # Full details of the execution
    temporary_run_data = {
        "program_output": program_output,
        "return_data": return_data,
    }

    # The S3 path we're storing the data at
    s3_object_path = "temporary_executions/" + unique_id + ".json"

    # Write data to S3
    response = S3_CLIENT.put_object(
        Bucket=s3_log_bucket,
        Key=s3_object_path,
        Body=json.dumps(
            temporary_run_data,
            sort_keys=True
        )
    )

    return {
        "s3_bucket": s3_log_bucket,
        "s3_path": s3_object_path,
    }


def _write_pipeline_logs(s3_log_bucket, project_id, lambda_arn, lambda_name, execution_pipeline_id, log_type, execution_details, program_output, backpack, input_data, return_data):
    def get_nearest_five_minutes():
        round_to = (60 * 5)
        dt = datetime.datetime.now()
        seconds = (dt.replace(tzinfo=None) - dt.min).seconds
        rounding = (
            seconds + round_to / 2
        ) // round_to * round_to
        return dt + datetime.timedelta(0, rounding - seconds, - dt.microsecond)

    s3_client = boto3.client(
        "s3"
    )

    log_id = str(uuid.uuid4())

    nearest_minute = get_nearest_five_minutes()
    date_shard_string = "dt=" + nearest_minute.strftime("%Y-%m-%d-%H-%M")

    s3_path = project_id + "/" + date_shard_string + "/" + execution_pipeline_id + \
        "/" + log_type + "~" + lambda_name + "~" + \
        log_id + "~" + str(int(time.time()))

    s3_data = {
        "id": log_id,
        "execution_pipeline_id": execution_pipeline_id,
        "project_id": project_id,
        "arn": lambda_arn,
        "name": lambda_name,
        "type": log_type,  # INPUT, EXCEPTION, COMPLETE
        "timestamp": int(time.time()),
        "program_output": program_output,
        "backpack": backpack,
        "input_data": input_data,
        "return_data": return_data,
    }

    # Merge in execution_details
    for key, value in execution_details.iteritems():
        s3_data[key] = value

    response = s3_client.put_object(
        Bucket=s3_log_bucket,
        Key=s3_path,
        Body=json.dumps(
            s3_data,
            sort_keys=True
        )
    )


def _spawner(branch_ids, invocation_id, context):
    """
    Fan-out invocations work in essentially the following stages:
    * A Lambda is invoked which has a fan-out transition
    * This Lambda sets up the counter in redis to prepare for fan-in
    * The Lambda also stores all invocation data in redis as a list
    * The Lambda then invokes itself with the ["_refinery"]["invoke"] options

    The value of ["_refinery"]["invoke"] is the following:
    {
            "invoke_id": {{UUID_OF_REDIS_LIST}},
            "invoke_speed": {{INTEGER_OF_PARALELL_SPAWNERS}},
    }

    The "invoke_id" refers to the ID of the list of invoke input(s)
    stored inside of redis. The "invoke_speed" refers to how many
    "spawner" Lambdas will be invoked.

    A "spawner" Lambda is just the Lambda invoking itself into a
    specific new mode of operation. This mode of operation works
    by spawning off multiple invocation threads which are continously
    looped over and fed more invoke requests. In each loop the remaining
    execution time is also checked. If the remaining execution time is
    less than 5 seconds the Lambda will then invoke itself again once
    to continue the invocation work (and will finish out it's pending
    invocations). If the invoke queue is finished the Lambda simply
    immediately exits.

    The "invoke_speed" determines the number of "spawner" Lambdas will
    run at the same time. In any case the spawners will always invoke
    all of the requested Lambdas for the returned data. The only thing
    that varies is the speed at which this will occur. It could be at
    the speed of 10 Lambdas invoking at ~18 invokes a second, or it could
    be at 100 Lambdas at ~18 invokes a second.
    """
    print("I am a spawner lambda who's spawned with an invocation ID of " + invocation_id)
    sys.stdout.flush()

    remaining_time_limit = (1000 * 10)
    parallel_invocation_number = 15
    queue_exhausted = False

    while queue_exhausted == False:
        # Reset list of Lambdas to invoke
        lambdas_to_invoke = []

        # Check if we're close to a timeout, if we are we should invoke ourselfs
        # and then dip out of performing more invocations.
        remaining_milliseconds = context.get_remaining_time_in_millis()
        if remaining_milliseconds <= remaining_time_limit:
            lambdas_to_invoke.append({
                "type": "lambda_fan_out",
                "arn": context.invoked_function_arn,
                "invocation_id": invocation_id,
                # Input data is purely to ensure we get idempotency
                "input_data": {
                        "why": "idempotency"
                }
            })
            start_time = time.time()
            _parallel_invoke(branch_ids, lambdas_to_invoke)
            return

        # Pull at least parallel_invocation_number number of inputs of the queue
        for i in range(0, parallel_invocation_number):
            try:
                lambdas_to_invoke.append(
                    gmemory._get_invocation_input_from_queue(
                        invocation_id
                    )
                )
            except InvokeQueueEmptyException as e:
                queue_exhausted = True
                # Break out of immediate for loop
                break

        start_time = time.time()
        _parallel_invoke(branch_ids, lambdas_to_invoke)

    return


def _pprint(input_dict):
    try:
        print(json.dumps(input_dict, sort_keys=True,
                         indent=4, separators=(",", ": ")))
    except:
        print(input_dict)


def _transition_type_in_transitions(transitions, transition_type):
    if "then" in transitions and type(transitions["then"]) == list:
        for transition in transitions["then"]:
            if "type" in transition and transition["type"] == transition_type:
                return True

    return False


def _warmup_concurrency_self_invoke(arn, decrement_counter):
    # Decrement concurrency counter
    decrement_counter = decrement_counter - 1

    if decrement_counter > 0:
        print("We have a higher level of concurrency to meet (" + str(decrement_counter) +
              " remaining), kicking off another layer of concurrency...")
        sys.stdout.flush()

        lambda_client = boto3.client(
            "lambda"
        )

        response = lambda_client.invoke(
            FunctionName=arn,
            InvocationType="RequestResponse",
            LogType="Tail",
            Payload=json.dumps({
                "_refinery": {
                    "warmup": decrement_counter
                },
            })
        )
        return

    print("We have no further concurrency to meet, this is the last one in the chain.")
    sys.stdout.flush()


def _improve_api_endpoint_request_data(lambda_input):
    # Try several body decoding methods and set fields
    # with the decoded values for each.
    if "body" in lambda_input:
        # Decode base64 body
        if "isBase64Encoded" in lambda_input and lambda_input["isBase64Encoded"]:
            # Base64
            try:
                lambda_input["raw_body"] = base64.b64decode(
                    lambda_input["body"]
                )
            except Exception as e:
                pass
        else:
            lambda_input["raw_body"] = lambda_input["body"]

        # JSON
        try:
            lambda_input["json"] = json.loads(
                lambda_input["raw_body"]
            )
        except Exception as e:
            lambda_input["json"] = None

        # application/x-www-form-urlencoded
        try:
            lambda_input["form"] = parse_qs(
                lambda_input["raw_body"]
            )
        except Exception as e:
            lambda_input["form"] = None

    return lambda_input


def _write_inline_code(inline_code, path):
    with open(path, "w") as file_handler:
        file_handler.write(inline_code.encode("utf8"))
    return path


def _write_s3_binary(s3_path, local_path):
    s3_response = S3_CLIENT.get_object(
        Bucket=os.environ["PACKAGES_BUCKET_NAME"],
        Key=s3_path
    )

    with open(local_path, "w") as file_handler:
        file_handler.write(
            s3_response["Body"].read()
        )


def _setup_inline_execution_shared_files(inline_file_list):
    shared_files_base_folder = "/tmp/shared_files/"

    if os.path.exists(shared_files_base_folder):
        _clear_temporary_files()

    # Make shared files directory
    os.mkdir(shared_files_base_folder)

    # Write all of the shared files
    for shared_file_metadata in inline_file_list:
        shared_file_path = shared_files_base_folder + \
            shared_file_metadata["name"]
        _write_inline_code(
            shared_file_metadata["body"],
            shared_file_path,
        )


def _clear_temporary_files():
    try:
        tmp_handler = subprocess.Popen(
            ["/bin/rm -rf /tmp/*"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            shell=True
        )
        tmp_handler.communicate()
    except Exception as e:
        pass


def _stream_execution_output_to_websocket(websocket, debug_id, output):
    websocket.send(json.dumps({
        "version": "1.0.0",
        "debug_id": debug_id,
        "action": "OUTPUT",
        "source": "LAMBDA",
        "body": output,
        "timestamp": int(time.time())
    }))
