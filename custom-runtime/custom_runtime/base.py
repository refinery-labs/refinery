
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

import traceback
import time
import json
import sys
import os


from .clock import _start_clock, _stop_clock
from .init import _init
from .utils import _write_pipeline_logs
from .constants import http


class CustomRuntime():
    """
    This custom runtime will run a given script with a custom interpreter.

    The executed script is expected to return data in the following format:

    {
            "output": "Running script...\nDone!",
            "return_data": "123",
    }
    """

    def __init__(self):
        runtime_endpoint = os.getenv("AWS_LAMBDA_RUNTIME_API")
        handler = os.getenv("_HANDLER")
        handler_parts = handler.split(".")
        handler_file = handler_parts[0]
        handler_function = handler_parts[1]
        self.base_invocation_uri = "http://" + \
            runtime_endpoint + "/2018-06-01/runtime/invocation"

    def process_next_event(self):
        event_data = self.get_next_invocation()

        context_dict = {
            "function_name": os.getenv("AWS_LAMBDA_FUNCTION_NAME"),
            "function_version": os.getenv("AWS_LAMBDA_FUNCTION_VERSION"),
            "invoked_function_arn": event_data["invoked_arn"],
            "memory_limit_in_mb": os.getenv("AWS_LAMBDA_FUNCTION_MEMORY_SIZE"),
            "aws_request_id": event_data["request_id"],
            "log_group_name": os.getenv("AWS_LAMBDA_LOG_GROUP_NAME"),
            "log_stream_name": os.getenv("AWS_LAMBDA_LOG_STREAM_NAME"),
            "deadline_ms": event_data["deadline_ms"]
        }

        # Create a context object
        class ContextObject:
            def __init__(self, context_obj_dict):
                # Set values of context object to context dict
                for key, value in context_obj_dict.iteritems():
                    setattr(self, key, value)

                # Set inner dict
                self.context_dict = context_dict

            def get_remaining_time_in_millis(self):
                return self.deadline_ms - int(time.time() * 1000)

        _start_clock("Context Object Initialization")
        new_context = ContextObject(context_dict)
        _stop_clock("Context Object Initialization")

        lambda_input = event_data["event_data"]

        try:
            lambda_input = json.loads(
                lambda_input
            )
        except:
            pass

        # Construct log details for debugging
        execution_details = {
            "initialization_time": int(time.time()),
            "aws_region": os.environ["AWS_REGION"],
            "group_name": new_context.log_group_name,
            "stream_name": new_context.log_stream_name,
            "function_name": new_context.function_name,
            "function_version": new_context.function_version,
            "invoked_function_arn": new_context.invoked_function_arn,
            "memory_limit_in_mb": int(new_context.memory_limit_in_mb),
            "aws_request_id": new_context.aws_request_id
        }

        # Run through the custom Refinery runtime.
        try:
            return _init(
                self,
                event_data["request_id"],
                lambda_input,
                new_context,
                execution_details
            )
        except Exception as err:
            exception_string = "You've found a bug in the Refinery custom runtime!\n"
            exception_string += "Please report the following exception to us: \n"
            exception_string += traceback.format_exc()
            print(exception_string)
            sys.stdout.flush()

            _write_pipeline_logs(
                os.environ["LOG_BUCKET_NAME"],
                os.environ["EXECUTION_PIPELINE_ID"],
                new_context.invoked_function_arn,
                new_context.function_name,
                lambda_input["_refinery"]["execution_id"],
                "EXCEPTION",
                execution_details,
                exception_string,
                {},
                lambda_input,
                ""
            )

            # Return successful state
            self.send_response(
                event_data["request_id"],
                ""
            )
            return

    def get_next_invocation(self):
        response = http.request(
            "GET",
            self.base_invocation_uri + "/next"
        )

        return {
            "deadline_ms": int(response.headers["Lambda-Runtime-Deadline-Ms"]),
            "invoked_arn": response.headers["Lambda-Runtime-Invoked-Function-Arn"],
            "request_id": response.headers["Lambda-Runtime-Aws-Request-Id"],
            "event_data": response.data
        }

    def send_response(self, request_id, return_data):
        http.request(
            "POST",
            self.base_invocation_uri + "/" + request_id + "/response",
            body=json.dumps(
                return_data
            ),
            headers={
                "Content-Type": "application/json",
            }
        )

    def send_error(self, request_id, error_data):
        http.request(
            "POST",
            self.base_invocation_uri + "/" + request_id + "/error",
            body=json.dumps(
                error_data
            ),
            headers={
                "Content-Type": "application/json",
            }
        )
