
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

from websocket import create_connection
import subprocess
import traceback
import boto3
import time
import json
import uuid
import math
import sys
import os


from .constants import gmemory, _VERSION, RUNTIME_DIR
from .clock import _start_clock, _stop_clock
from .exc import AlreadyInvokedException
from .parallel_invoke import _parallel_invoke
from .sqs import _sqs_worker
from .utils import _setup_inline_execution_shared_files, _write_pipeline_logs
from .utils import _api_endpoint, _write_inline_code, _write_s3_binary
from .utils import _warmup_concurrency_self_invoke, _spawner
from .utils import _stream_execution_output_to_websocket, _clear_temporary_files
from .utils import _transition_type_in_transitions, _write_temporary_execution_results
from .utils import _improve_api_endpoint_request_data


def _init(custom_runtime, request_id, lambda_input, context, execution_details):
    start_time = time.time()

    # Generate the path to the execution payload
    handler_parts = os.getenv("_HANDLER").split(".")
    executable_path = os.getenv("LAMBDA_TASK_ROOT") + "/" + handler_parts[0]

    execution_pipeline_id = os.environ["EXECUTION_PIPELINE_ID"]
    s3_log_bucket = os.environ["LOG_BUCKET_NAME"]
    execution_pipeline_logging_level = os.environ["PIPELINE_LOGGING_LEVEL"]

    # If pipeline logging is enabled
    # We initialize the S3 client to prevent threading bugs
    if execution_pipeline_logging_level != "LOG_NONE":
        _start_clock("S3 Boto Client Initialization")
        # Bug fix test
        s3_client = boto3.client(
            "s3"
        )
        _stop_clock("S3 Boto Client Initialization")

    # Indicate a special execution condition
    # For example, an API Gateway Lambda
    execution_mode = os.environ["EXECUTION_MODE"]

    # Branch IDs, these are used for merges and are added whenever
    # a Code Block spawns multiple child executions (through multiple
    # thens, a fan-out, etc)
    branch_ids = []

    # Execution ID, this is an ID which correlates to an execution chain
    execution_id = False

    # Bake in transition data
    transitions = json.loads(os.environ["TRANSITION_DATA"])

    # Set default fan-out IDs list to be empty
    fan_out_ids = []

    # Throw exceptions fully (for use in tmp-runs, etc)
    throw_exceptions_fully = False

    # If the execution is a temporary execution, for example if the
    # Lambda is being execute in the Refinery editor.
    is_temporary_execution = False

    # If the execution is being live streamed via WebSocket callbacks
    # then this will be the actual reference to the websocket client.
    live_debug = False

    # The backpack variable is a variable that is automatically passed
    # between code block executions and is an arbitrary map/dict/object
    # that you can set key/values on. This is useful for storing some data
    # to be used in a non-immediate code block in the workflow. This way you
    # don't have to always return all of your data in a weird format in order
    # to pass it along.
    backpack = {}

    _start_clock("Loading Input Data")

    # This is for the SNS topic message case, we just attempt to parse
    # the JSON at the location we expect it to be. If it fails it's just
    # because it's not a SNS message and so we can skip it.
    try:
        lambda_input = json.loads( lambda_input["Records"][0]["Sns"]["Message"]
        )
    except:
        # If we get an exception it's just because it isn't an SNS topic message.
        # So we just continue on as usual.
        pass

    # This is for messages coming off an SQS queue, the regular output is confusing
    # So we format it to be regular input
    try:
        # This is just to check if it's an SQS "shaped" message
        receipt_handle = lambda_input["Records"][0]["receiptHandle"]

        lambda_input_list = []

        # Set metadata from items in queue batch
        for batch_item in lambda_input["Records"]:
            batch_input_data = json.loads(
                batch_item["body"]
            )

            if "_refinery" in batch_input_data:
                # Set the metadata
                execution_id = batch_input_data["_refinery"]["execution_id"]
                fan_out_ids = batch_input_data["_refinery"]["fan_out_ids"]
                queue_insert_id = batch_input_data["_refinery"]["queue_insert_id"]
                branch_ids = batch_input_data["_refinery"]["branch_ids"]

            lambda_input_list.append(
                batch_input_data["_refinery"]["input_data"]
            )

        # Let's grab the backpack
        backpack = gmemory._get_queue_backpack(
            queue_insert_id
        )

        # Set the Lambda input data
        lambda_input = lambda_input_list

        # If that didn't throw an exception it's certainly SQS and we need to format
        # the returned data.
    except Exception as e:
        pass

    # By default inline execution is disabled
    is_inline_execution = False

    # Detect refinery wrapper and unwrap if existant
    # Else just leave it unmodified
    if type(lambda_input) == dict and "_refinery" in lambda_input:
        # If a branch ID array exists in the input, set it.
        if "branch_ids" in lambda_input["_refinery"]:
            branch_ids = lambda_input["_refinery"]["branch_ids"]

        """
		In order to speed up inline executions (e.g. Editor executions)
		we keep the base Lambda layers/packages/configs deployed in a Lambda.
		Then we set an environment variable on the Lambda to indicate that this is
		just a Lambda to be used for inline execution. When this environment variable
		is set it allows for passing arbitrary code into the Lambda as a parameter of "inline_code":

		For example:
		{
			"_refinery": {
				"inline_code": "def test()..."
			}
		}

		This code is written to a file in /tmp/ and the "executable_path" variable
		is updated to this new path.

		For other Lambdas in production this environment variable is NOT set so this
		input being passed will have no effect. Obviously arbitrary code execution is
		not something we want to allow for the actually Lambdas we have in prod deploys :)

		This dramatically increases execution times for inline runs and allows a much better
		development experience for our users.
		"""
        is_inline_execution = (
            os.getenv("IS_INLINE_EXECUTOR", False) == "True" and
            "inline_code" in lambda_input["_refinery"]
        )

        # If it's an inline execution write the temporary code file
        if is_inline_execution:
            # Backwards compatibility
            if type(lambda_input["_refinery"]["inline_code"]) == str:
                lambda_input["_refinery"]["inline_code"] = {
                    "shared_files": [],
                    "base_code": lambda_input["_refinery"]["inline_code"]["base_code"]
                }

            # Set up files for inline execution, returns executable path
            _setup_inline_execution_shared_files(
                lambda_input["_refinery"]["inline_code"]["shared_files"]
            )

            # Base code path
            executable_path = "/tmp/" + str(uuid.uuid4())
            if "base_code" in lambda_input["_refinery"]["inline_code"]:
                _write_inline_code(
                    lambda_input["_refinery"]["inline_code"]["base_code"],
                    executable_path
                )

            # Pull in a remote file and execute it. This is used for things like
            # inline executions using fully-compiled binaries (Go). Since passing
            # the binary in as input would exceed the max size we pass the S3 path
            # in and then pull it down at runtime.
            if "s3_path" in lambda_input["_refinery"]["inline_code"]:
                # Write binary to disk
                _write_s3_binary(
                    lambda_input["_refinery"]["inline_code"]["s3_path"],
                    executable_path
                )

                # Mark as executable
                os.chmod(executable_path, 0o775)

        """
		For doing live debugging/streaming of the Lambda execution.

		Provides a debug_id for tracing and a callback URL for the websocket
		to do the actual calling-back to.

		"live_debug": {
			"debug_id": "{{UUID}}",
			"websocket_uri": "ws://35.131.123.111:4444/ws/v1/lambdas/connectback", # Websocket callback URL with API server direct IP
		}
		"""
        if "live_debug" in lambda_input["_refinery"]:
            live_debug = lambda_input["_refinery"]["live_debug"]
            live_debug["websocket"] = create_connection(
                live_debug["websocket_uri"]
            )

        # Check if it's just a warmup request
        if "warmup" in lambda_input["_refinery"]:
            decrement_counter = lambda_input["_refinery"]["warmup"]
            _warmup_concurrency_self_invoke(
                context.invoked_function_arn,
                decrement_counter
            )
            print("Lambda warming event received, quitting out.")
            sys.stdout.flush()

            custom_runtime.send_response(
                request_id,
                ""
            )
            return

        # Check if it's a temporary execution
        if "temporary_execution" in lambda_input["_refinery"]:
            is_temporary_execution = True

        # Check if it's an SQS queue worker
        if "sqs_worker" in lambda_input["_refinery"]:
            _sqs_worker(
                lambda_input["_refinery"]["sqs_worker"]["queue_insert_id"],
                lambda_input["_refinery"]["sqs_worker"]["execution_id"],
                lambda_input["_refinery"]["sqs_worker"]["branch_ids"],
                lambda_input["_refinery"]["sqs_worker"]["fan_out_ids"],
                context
            )
            custom_runtime.send_response(
                request_id,
                ""
            )
            return

        # Set execution ID if set
        if "execution_id" in lambda_input["_refinery"]:
            execution_id = lambda_input["_refinery"]["execution_id"]

        # Set/propogate fan-out ID list if set
        if "fan_out_ids" in lambda_input["_refinery"]:
            fan_out_ids = lambda_input["_refinery"]["fan_out_ids"]

        # Throw exceptions fully (for use in tmp-runs, etc)
        if "throw_exceptions_fully" in lambda_input["_refinery"]:
            throw_exceptions_fully = True

        # Set is invoke status
        is_spawner_invocation = False

        # We don't immediately invoke ourselves until after loading
        # useless return data to ensure idempotency
        if "invoke" in lambda_input["_refinery"]:
            is_spawner_invocation = True
            invocation_id = lambda_input["_refinery"]["invoke"]

        # This is for non-redis calls, e.g. through SNS or SQS
        if "backpack" in lambda_input["_refinery"]:
            backpack = lambda_input["_refinery"]["backpack"]

        _side_loaded = False
        if "indirect" in lambda_input["_refinery"] and lambda_input["_refinery"]["indirect"] and "type" in lambda_input["_refinery"]["indirect"]:
            # Input data is stored in redis
            if lambda_input["_refinery"]["indirect"]["type"] == "redis":
                try:
                    stored_input = gmemory._get_input_data_from_redis(
                        lambda_input["_refinery"]["indirect"]["key"]
                    )
                    lambda_input = stored_input["input_data"]
                    backpack = stored_input["backpack"]
                except AlreadyInvokedException as e:
                    print("This Lambda has already been invoked (or the return data has expired). For this reason we are quitting out (indirect return data).")
                    custom_runtime.send_response(
                        request_id,
                        ""
                    )
                    return
                _side_loaded = True
            # Input data is stored in redis as a list from a fan-in
            elif lambda_input["_refinery"]["indirect"]["type"] == "redis_fan_in":
                try:
                    stored_input = gmemory._fan_in_get_results_data(
                        lambda_input["_refinery"]["indirect"]["key"]
                    )
                    lambda_input = stored_input["input_data"]
                    backpack = stored_input["backpack"]
                except AlreadyInvokedException as e:
                    print("This Lambda has already been invoked (or the return data has expired). For this reason we are quitting out (direct return data).")
                    custom_runtime.send_response(
                        request_id,
                        ""
                    )
                    return
                _side_loaded = True

        # If there's an "invoke" key it means we're doing a self-invocation fan-out
        if is_spawner_invocation:
            _spawner(
                branch_ids,
                invocation_id,
                context
            )
            custom_runtime.send_response(
                request_id,
                ""
            )
            return
        # Just directly passed input data
        if not _side_loaded and "input_data" in lambda_input["_refinery"]:
            lambda_input = lambda_input["_refinery"]["input_data"]

    _stop_clock("Loading Input Data")

    # If we don't have an execution ID, generate and set one!
    if not execution_id:
        execution_id = str(uuid.uuid4())

    # Set execution ID on Lambda context
    # This is needed so it can be accessed inside of the Lambdas
    # regular code.
    setattr(
        context,
        "execution_id",
        execution_id
    )

    return_data = {}

    if execution_mode == "REGULAR":
        _start_clock("Executing Lambda")

        print(RUNTIME_DIR, executable_path)

        process_handler = subprocess.Popen(
            [
                RUNTIME_DIR,
                executable_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            shell=False,
            universal_newlines=True,
            cwd=os.getenv("LAMBDA_TASK_ROOT") + "/",
        )

        # Write input data
        process_handler.stdin.write(json.dumps({
            "lambda_input": lambda_input,
            "backpack": backpack
        }))
        process_handler.stdin.close()

        return_data = ""

        for line in iter(process_handler.stdout.readline, ""):
            # If we're live streaming the output data, then pump it into
            # the WebSocket connection
            if live_debug and not line.startswith("<REFINERY_"):
                _stream_execution_output_to_websocket(
                    live_debug["websocket"],
                    live_debug["debug_id"],
                    line
                )

            return_data += line

        while process_handler.returncode is None:
            process_handler.poll()

        return_data = return_data.strip()

        # Close the WebSocket connection now that we're finished
        if live_debug:
            live_debug["websocket"].close()

        # If it's an inline execution we need to delete the file we just
        # executed so that it doesn't fill up the disk each run.
        if is_inline_execution:
            _clear_temporary_files()

        _stop_clock("Executing Lambda")

        if process_handler.returncode == 0:
            # We now look for the markers to indicate data is being returned.
            start_marker = "<REFINERY_OUTPUT_CUSTOM_RUNTIME_START_MARKER>"
            end_marker = "<REFINERY_OUTPUT_CUSTOM_RUNTIME_END_MARKER>"
            program_output = ""

            # If we have the marker, pull it out.
            if start_marker in return_data and end_marker in return_data:
                return_data_parts = return_data.split(start_marker)
                program_output = return_data_parts[0]
                return_data_sub_parts = return_data_parts[1].split(end_marker)
                return_data_string = return_data_sub_parts[0]
                try:
                    return_data = json.loads(
                        return_data_string
                    )
                    backpack = return_data["backpack"]
                    return_data = return_data["output"]
                except:
                    return_data = return_data_string

                # Write the output for logging
                sys.stdout.write(program_output)
                sys.stdout.flush()
            else:
                # Write the output for logging
                sys.stdout.write(return_data)
                sys.stdout.flush()
                # If there's no marker we're not returning anything.
                # Just return nothing
                return_data = ""
        else:
            error_output = return_data

            error_start_marker = "<REFINERY_ERROR_OUTPUT_CUSTOM_RUNTIME_START_MARKER>"
            error_end_marker = "<REFINERY_ERROR_OUTPUT_CUSTOM_RUNTIME_END_MARKER>"

            if error_start_marker in str(error_output) and error_end_marker in str(error_output):
                exception_parts = error_output.split(error_start_marker)
                error_output = exception_parts[0]
                exception_data_sub_parts = exception_parts[1].split(
                    error_end_marker)
                exception_string = exception_data_sub_parts[0]
            else:
                exception_string = ""

            try:
                output_data = json.loads(
                    exception_string
                )
                exception_string = output_data["output"]
                backpack = output_data["backpack"]
                error_output = error_output + exception_string
            except:
                # We pass here since the result is the same
                # Just an unmodified backpack
                pass

            _stop_clock("Executing Lambda")

            invocation_input_list = []

            # Invoke all Lambdas to be run when an exception occurs
            if len(transitions["exception"]) > 0:
                if execution_pipeline_logging_level == "LOG_ERRORS" or execution_pipeline_logging_level == "LOG_ALL":
                    _write_pipeline_logs(
                        s3_log_bucket,
                        execution_pipeline_id,
                        context.invoked_function_arn,
                        context.function_name,
                        execution_id,
                        "CAUGHT_EXCEPTION",
                        execution_details,
                        error_output,
                        backpack,
                        lambda_input,
                        ""
                    )

                for exception_transition_data in transitions["exception"]:
                    invocation_input_list.append({
                        "execution_id": execution_id,
                        "fan_out_ids": fan_out_ids,
                        "type": exception_transition_data["type"],
                        "arn": exception_transition_data["arn"],
                        "backpack": backpack,
                        "input_data": {
                            "version": _VERSION,
                            "exception_text": exception_string,
                            "input_data": json.loads(
                                json.dumps(
                                    lambda_input
                                )
                            )
                        }
                    })
            elif execution_pipeline_logging_level == "LOG_ERRORS" or execution_pipeline_logging_level == "LOG_ALL":
                _write_pipeline_logs(
                    s3_log_bucket,
                    execution_pipeline_id,
                    context.invoked_function_arn,
                    context.function_name,
                    execution_id,
                    "EXCEPTION",
                    execution_details,
                    error_output,
                    backpack,
                    lambda_input,
                    ""
                )

            # If we've got an API Gateway response coming up we'll write an error
            # to it so that it's more obvious what's happening.
            if _transition_type_in_transitions(transitions, "api_gateway_response"):
                invocation_input_list.append({
                    "backpack": backpack,
                    "execution_id": execution_id,
                    "type": "api_gateway_response",
                    "input_data": {
                            "success": False,
                        "msg": "An exception occurred while computing the response to the request. Please see the block execution logs for more information."
                    }
                })

            # If there's an exception we should stop after invoking the exception case(s).
            _parallel_invoke(branch_ids, invocation_input_list)

            # Write error to stderr for logging
            sys.stderr.write(error_output)
            sys.stderr.flush()

            return_data = ""

            # If we're doing a temporary execution we want to format the returned
            # data in the special format for the API server to pull the full data out
            # of S3.
            if is_temporary_execution:
                execution_result_details = _write_temporary_execution_results(
                    s3_log_bucket,
                    error_output,
                    ""
                )

                return_data = {
                    "_refinery": {
                        "indirect": {
                            "type": "s3",
                            "s3_bucket": execution_result_details["s3_bucket"],
                            "s3_path": execution_result_details["s3_path"]
                        }
                    }
                }

            # We only want to do this if we've been asked to fully throw exceptions
            if throw_exceptions_fully:
                custom_runtime.send_error(
                    request_id,
                    return_data,  # Just blank output for errors
                )
                return

            custom_runtime.send_response(
                request_id,
                return_data
            )
            return

        # Attempt to convert return_data into an actual
        # object if it's JSON
        try:
            return_data = json.loads(
                return_data
            )
        except:
            pass

    elif execution_mode == "API_ENDPOINT":
        # Just return the HTTP request event data
        return_data = lambda_input

    # If it's a temporary execution we can stop here
    # and just immediately return our special format
    if is_temporary_execution:
        execution_result_details = _write_temporary_execution_results(
            s3_log_bucket,
            program_output,
            return_data
        )

        return_data = {
            "_refinery": {
                "indirect": {
                    "type": "s3",
                    "s3_bucket": execution_result_details["s3_bucket"],
                    "s3_path": execution_result_details["s3_path"]
                }
            }
        }

        custom_runtime.send_response(
            request_id,
            return_data
        )

        return

    # If it's an API gateway Lambda we can end it here.
    if execution_mode == "API_ENDPOINT":
        # Used for formatting AWS API Gateway data to be more
        # usable for regular users.
        try:
            lambda_input = _improve_api_endpoint_request_data(
                lambda_input
            )
        except Exception as e:
            print(
                "[ Refinery Custom Runtime ] An exception occurred while decoding the request data.")
            print(e)
            sys.stdout.flush()

    # Stores the invocation data for "if"s and "then"s
    invocation_input_list = []

    # For fan-outs
    for fan_out_transition_data in transitions["fan-out"]:
        if type(return_data) != list:
            # Write error to stderr for logging
            sys.stderr.write(
                "Error, tried to fan-out without returning a list, returned type " +
                str(type(return_data))
            )
            sys.stderr.flush()
            custom_runtime.send_response(
                request_id,
                ""  # Just blank output for errors
            )
            return

        # If there's an empty list returned from a block in a fan-out
        # we can just skip the next transition.
        if len(return_data) == 0:
            continue

        # Generate fan-out ID
        fan_out_id = str(uuid.uuid4())

        # Add to our fan-out IDs
        new_fan_out_ids = fan_out_ids
        new_fan_out_ids.append(
            fan_out_id
        )

        # Create a list of invocation inputs
        invocation_list = []

        # Iterate over each item in the return list
        for return_item_data in return_data:
            # Create an invocation for it
            # Convert into JSON so it can be stored in redis
            invocation_list.append(
                json.dumps({
                    "backpack": backpack,
                    "execution_id": execution_id,
                    "fan_out_ids": new_fan_out_ids,
                    "type": "fan_out_execution",
                            "arn": fan_out_transition_data["arn"],
                            "input_data": json.loads(
                                json.dumps(
                                    return_item_data
                                )
                            )
                })
            )

        # Sets up atomic counter for fan-in
        invocation_id = gmemory._set_fan_in_data(
            fan_out_id,
            invocation_list
        )

        """
		Calculate the fan-out invocation speed (A.K.A. the
		number of spawners we'll spin up to invoke it all).

		There are three factors for this:
		* Remaining execution time (to invoke the spawners).
		* Execution memory (affects how invocating can be done)
		* Number of invocations to perform

		The remaining execution time is used as the ceiling
		and the number of invocations to perform is used to
		figure out the velocity.
		"""
        total_lambda_execution_time = int(math.ceil(
            time.time() - start_time)) + int(context.get_remaining_time_in_millis() / 1000)
        remaining_seconds = int(
            math.floor(
                (context.get_remaining_time_in_millis() / 1000)
            )
        )

        # Conservative estimates of how many lambdas can
        # be executed per second for each memory range.
        # These are pretty low balls but better safe than sorry!
        if int(context.memory_limit_in_mb) <= 256:
            lambdas_per_second = 2
        elif int(context.memory_limit_in_mb) <= 576:
            lambdas_per_second = 10
        elif int(context.memory_limit_in_mb) > 576:
            lambdas_per_second = 13

        # Calculate max number of Lambdas we //could// execute
        max_lambda_invocations_possible = (
            lambdas_per_second * remaining_seconds)

        # Number of invocations we actually have to execute
        number_of_executions_to_perform = len(invocation_list)

        # Number of invocations a fresh-started Lambda could do
        # Minus one for the initialization cost that may be incurred
        total_lambda_executions_per_run = (
            lambdas_per_second * (total_lambda_execution_time - 2))

        # Calculate the number of full runs it'd take to process all the invocations
        number_of_runs_to_complete = int(math.ceil(
            float(number_of_executions_to_perform) / float(total_lambda_executions_per_run)))

        # Now calculate the number of spawners to kick off.
        if number_of_runs_to_complete <= max_lambda_invocations_possible:
            # If the number of runs to complete the work is less than the
            # number of invocations possible we'll just invoke that many
            # spawner Lambda(s)!
            fan_out_invocation_speed = number_of_runs_to_complete
        else:
            # Otherwise we'll just invoke the max possible
            fan_out_invocation_speed = max_lambda_invocations_possible

        def get_seconds_to_completion(number_of_executions_to_perform, lambdas_per_second, fan_out_invocation_speed):
            return (float(number_of_executions_to_perform) / float(lambdas_per_second * fan_out_invocation_speed))

        seconds_to_complete = get_seconds_to_completion(
            number_of_executions_to_perform,
            lambdas_per_second,
            fan_out_invocation_speed
        )

        # This is the target seconds we shoot for to spawn everything.
        target_seconds = 10

        # Keep boosting
        while seconds_to_complete > target_seconds:
            seconds_to_complete = get_seconds_to_completion(
                number_of_executions_to_perform,
                lambdas_per_second,
                (fan_out_invocation_speed + 1)
            )

            # If boosting would push us over max Lambda invocations quit out
            if (fan_out_invocation_speed + 1) > max_lambda_invocations_possible:
                break

            # Meets criteria so we can up it
            fan_out_invocation_speed += 1

            # If we meet our target time then we can stop
            if seconds_to_complete <= target_seconds:
                break

        seconds_to_complete = get_seconds_to_completion(
            number_of_executions_to_perform,
            lambdas_per_second,
            fan_out_invocation_speed
        )

        # Invoke self in "spawner" mode X times
        # where X is invocation speed
        for i in range(0, fan_out_invocation_speed):
            invocation_input_list.append({
                "type": "lambda_fan_out",
                "arn": context.invoked_function_arn,
                "invocation_id": invocation_id,
                "backpack": backpack,
                # Input data is purely to ensure we get idempotency
                "input_data": {
                        "why": "idempotency"
                }
            })

    # For fan-in
    for fan_in_transition_data in transitions["fan-in"]:
        # If they do a fan-in and they haven't done a fan-out
        if len(fan_out_ids) == 0:
            break

        # Get last fan-out ID
        fan_out_id = fan_out_ids.pop()

        # First we push our returned data into the results list
        fan_in_results = gmemory._fan_in_operations(
            fan_out_id,
            return_data,
            backpack
        )

        # If we're the final invocation in the fan-in we
        # will invoke the next Lambda with the return data
        # array as the input.
        if fan_in_results:
            invocation_input_list.append({
                "backpack": backpack,
                "execution_id": execution_id,
                "fan_out_ids": fan_out_ids,
                "type": "lambda_fan_in",
                "arn": fan_in_transition_data["arn"],
                "fan_out_id": fan_out_id
            })

    # If it's just a then, just invoke the next Lambda
    for then_transition_data in transitions["then"]:
        invocation_input_list.append({
            "backpack": backpack,
            "execution_id": execution_id,
            "fan_out_ids": fan_out_ids,
            "type": then_transition_data["type"],
            "arn": then_transition_data["arn"],
            "context": context,
            "input_data": json.loads(
                json.dumps(
                    return_data
                )
            )
        })

    # For merge transitions
    for merge_transition_data in transitions["merge"]:
        invocation_input_list.append({
            "invoked_function_arn": context.invoked_function_arn,
            "merge_lambdas": merge_transition_data["merge_lambdas"],
            "backpack": backpack,
            "execution_id": execution_id,
            "fan_out_ids": fan_out_ids,
            "type": "merge",
            "arn": merge_transition_data["arn"],
            "input_data": json.loads(
                json.dumps(
                    return_data
                )
            )
        })

    # If it's an API gateway Lambda we can end it here.
    if execution_mode == "API_ENDPOINT":
        # Now we invoke all the queued Lambdas!
        _parallel_invoke(branch_ids, invocation_input_list)

        custom_runtime.send_response(
            request_id,
            _api_endpoint(
                lambda_input,
                execution_id,
                context
            )
        )
        return

    # Variable to hold if any "if" statements evaluated to true
    # if one has then we don't execute any "else" statements
    true_if_evaluation_occured = False

    # Iterate over every if
    for if_statement_data in transitions["if"]:
        try:
            expression_eval_result = eval(if_statement_data["expression"])
        except Exception as err:
            exception_string = "Your \"if\" transition's conditional logic code has thrown an exception!\n"
            exception_string += "Please note it must be valid Python 2.7 code. The exception is the following: \n"
            exception_string += traceback.format_exc()
            print(exception_string)
            sys.stdout.flush()
            custom_runtime.send_error(
                request_id,
                return_data,  # Just blank output for errors
            )
            _write_pipeline_logs(
                os.environ["LOG_BUCKET_NAME"],
                os.environ["EXECUTION_PIPELINE_ID"],
                context.invoked_function_arn,
                context.function_name,
                execution_id,
                "EXCEPTION",
                execution_details,
                exception_string,
                {},
                lambda_input,
                ""
            )
            return

        if expression_eval_result:
            invocation_input_list.append({
                "backpack": backpack,
                "execution_id": execution_id,
                "fan_out_ids": fan_out_ids,
                "type": if_statement_data["type"],
                "arn": if_statement_data["arn"],
                "context": context,
                "input_data": json.loads(
                    json.dumps(
                        return_data
                    )
                )
            })

            true_if_evaluation_occured = True

    # If else is set, call that now
    if true_if_evaluation_occured == False:
        for else_transition_data in transitions["else"]:
            invocation_input_list.append({
                "backpack": backpack,
                "execution_id": execution_id,
                "fan_out_ids": fan_out_ids,
                "type": else_transition_data["type"],
                "arn": else_transition_data["arn"],
                "input_data": json.loads(
                    json.dumps(
                        return_data
                    )
                )
            })

    # Now we invoke all the queued Lambdas!
    _parallel_invoke(branch_ids, invocation_input_list)

    # If pipeline logging is enabled
    # Write the return data of this Lambda
    if execution_pipeline_logging_level == "LOG_ALL":
        _write_pipeline_logs(
            s3_log_bucket,
            execution_pipeline_id,
            context.invoked_function_arn,
            context.function_name,
            execution_id,
            "SUCCESS",
            execution_details,
            program_output,
            backpack,
            lambda_input,
            return_data
        )

    # Return the return data as usual
    custom_runtime.send_response(
        request_id,
        json.dumps(
            return_data
        )
    )
    return


