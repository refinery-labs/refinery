import json
import os
import time
import uuid
from websocket import create_connection


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
        tmp_handler = os.subprocess.Popen(
            ["/bin/rm -rf /tmp/*"],
            stdout=os.subprocess.PIPE,
            stderr=os.subprocess.PIPE,
            stdin=os.subprocess.PIPE,
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


def main(event, context):
    lambda_input = event

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
