import os
import json
import zlib
import base64
import requests

def lambda_handler(event, context):
    # Convert the data to something reasonable from the
    # standard inbound Kinesis event
    decoded_data = zlib.decompress(
        base64.b64decode(
            event["records"][0]["data"]
        ),
        16+zlib.MAX_WBITS
    )
    inbound_data = json.loads(
        decoded_data.decode( "utf-8" )
    )

    print(inbound_data)

    # Pull out the log line we received
    log_line = inbound_data["logEvents"][0]["message"]

    log_line_dict = get_dict_from_log_lines(
        log_line
    )

    # Convert millisecond timestamp to regular timestamp
    timestamp_ms = inbound_data[ "logEvents" ][0][ "timestamp" ]
    timestamp = int(
        timestamp_ms / 1000
    )

    # This is the data that is sent in the webhook to the server
    post_payload = {
        # Do not ever encode AWS account IDs as integers
        # You have been warned.
        "account_id": inbound_data[ "owner" ],
        "log_name": inbound_data[ "logGroup" ],
        "log_stream": inbound_data[ "logStream" ],
        "lambda_name": inbound_data[ "logGroup" ].replace(
            "/aws/lambda/",
            ""
        ),
        "raw_line": log_line,
        "timestamp": timestamp,
        "timestamp_ms": timestamp_ms
    }

    # Validate all these keys exist in our received data
    keys_that_must_exist = [
        "duration", 
        "memory_size",
        "max_memory_used",
        "billed_duration",
        "report_requestid"
    ]

    for key_that_must_exist in keys_that_must_exist:
        if not ( key_that_must_exist in log_line_dict ):
            # Raise an exception if not all the keys we expect exist
            raise Exception( "Missing required key in payload: " + key_that_must_exist )
        
        post_payload[ key_that_must_exist ] = log_line_dict[ key_that_must_exist ]
        
    print(
        json.dumps(
            post_payload
        )
    )

    # Send HTTP request with the data to webhook
    response = requests.post(
        os.environ[ "WEBHOOK_URL" ],
        json=post_payload,
        timeout=10
    )

    return post_payload

def get_dict_from_log_lines( input_log_line ):
    return_dict = {}
    log_line_parts = input_log_line.split( "\t" )

    for log_line_part in log_line_parts:
        sub_parts = log_line_part.split( ": " )

        # Skip if the split parts are less than two
        if len( sub_parts ) < 2:
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
            value = int( value )

        return_dict[ key ] = value

    return return_dict
