import datetime
import json
import os
import time
import uuid

import contextlib
import sys
from io import StringIO

import boto3
from refinery_main import main


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
    for key, value in execution_details.items():
        s3_data[key] = value

    response = s3_client.put_object(
        Bucket=s3_log_bucket,
        Key=s3_path,
        Body=json.dumps(
            s3_data,
            sort_keys=True
        )
    )


@contextlib.contextmanager
def capture():
    old_out, old_err = sys.stdout, sys.stderr
    out = [StringIO(), StringIO()]

    try:
        sys.stdout, sys.stderr = out
        yield out
    finally:
        sys.stdout, sys.stderr = old_out, old_err
        out[0] = out[0].getvalue()
        out[1] = out[1].getvalue()


def lambda_handler(event, context):
    block_input = event.get("block input", {})
    backpack = event.get("backpack", {})

    sys.stdout.write("Starting lambda!!!\n")

    with capture() as out:
        return_value = main(block_input, backpack)

    sys.stdout.write("Code done running!!!\n")
    sys.stdout.write(out)

    execution_details = {
        "initialization_time": int(time.time()),
        "aws_region": os.environ["AWS_REGION"],
        "group_name": context.log_group_name,
        "stream_name": context.log_stream_name,
        "function_name": context.function_name,
        "function_version": context.function_version,
        "invoked_function_arn": context.invoked_function_arn,
        "memory_limit_in_mb": int(context.memory_limit_in_mb),
        "aws_request_id": context.aws_request_id
    }

    _write_pipeline_logs(
        os.environ["LOG_BUCKET_NAME"],
        os.environ["EXECUTION_PIPELINE_ID"],
        context.invoked_function_arn,
        context.function_name,
        event["_refinery"]["execution_id"],
        "SUCCESS",
        execution_details,
        out,
        backpack,
        block_input,
        return_value
    )

    return return_value
