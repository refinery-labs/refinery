import os
import json
import zlib
import base64
import requests


def decode_kinesis_records(records):
    inbound_records_data = []

    # Convert the data to something reasonable from the
    # standard inbound Kinesis event
    for record in records:
        record_data = record["kinesis"]["data"]

        decoded_data = zlib.decompress(
            base64.b64decode(
                record_data
            ),
            16 + zlib.MAX_WBITS
        )

        inbound_data = json.loads(
            decoded_data.decode("utf-8")
        )
        inbound_records_data.append(inbound_data)

    return inbound_records_data


def get_dict_from_log_lines(input_log_line):
    return_dict = {}
    log_line_parts = input_log_line.split("\t")

    for log_line_part in log_line_parts:
        sub_parts = log_line_part.split(": ")

        # Skip if the split parts are less than two
        if len(sub_parts) < 2:
            continue

        key = sub_parts[0]
        value = sub_parts[1]

        key = key.lower().replace(
            " ",
            "_",
        )

        # Format MB values as integers
        # These are whole numbers so they're safe
        # to convert to integers (unlike floats
        # for example).
        integer_format_keys = [
            "billed_duration",
            "memory_size",
            "max_memory_used"
        ]

        value = value.replace(
            " MB",
            ""
        ).replace(
            " ms",
            ""
        )

        if key in integer_format_keys:
            value = int(value)

        return_dict[key] = value

    return return_dict


def parse_log_event_report(log_line):
    log_line_dict = get_dict_from_log_lines(
        log_line
    )

    # Validate all these keys exist in our received data
    keys_that_must_exist = [
        "duration",
        "memory_size",
        "max_memory_used",
        "billed_duration",
        "report_requestid"
    ]

    for key_that_must_exist in keys_that_must_exist:
        if not (key_that_must_exist in log_line_dict):
            # Raise an exception if not all the keys we expect exist
            raise Exception("Missing required key in payload: " + key_that_must_exist)

    return log_line_dict


def process_inbound_data_log_event(inbound_data):
    log_events = inbound_data["logEvents"]

    # Pull out the log line we received
    log_line = log_events[0]["message"]

    # Convert millisecond timestamp to regular timestamp
    timestamp_ms = log_events[0]["timestamp"]
    timestamp = int(
        timestamp_ms / 1000
    )

    log_group = inbound_data["logGroup"]
    log_stream = inbound_data["logStream"]
    account_id = inbound_data["owner"]

    billing_log_report = parse_log_event_report(log_line)

    return {
        # Do not ever encode AWS account IDs as integers
        # You have been warned.
        "account_id": account_id,
        "log_name": log_group,
        "log_stream": log_stream,
        "lambda_name": log_group.replace(
            "/aws/lambda/",
            ""
        ),
        "raw_line": log_line,
        "timestamp": timestamp,
        "timestamp_ms": timestamp_ms,

        **billing_log_report
    }


def process_inbound_data_log_events(inbound_records_data):
    log_events = []
    for inbound_data in inbound_records_data:
        log_event = process_inbound_data_log_event(inbound_data)
        log_events.append(log_event)
    return log_events


def lambda_handler(event, context):
    records = event["Records"]

    inbound_records_data = decode_kinesis_records(records)

    log_events = process_inbound_data_log_events(inbound_records_data)

    headers = {
        'X-Service-Secret': os.environ["SERVICE_SHARED_SECRET"]
    }

    response = requests.post(
        os.environ["WEBHOOK_URL"],
        json=log_events,
        headers=headers,
        timeout=10
    )

    return log_events
