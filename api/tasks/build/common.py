from hashlib import sha256
from json import dumps
from pyexceptions.builds import BuildException
from tasks.s3 import read_from_s3
from tasks.cloudwatch import get_lambda_cloudwatch_logs
from time import sleep
from utils.general import logit


def get_final_zip_package_path(language, libraries_object):
    hash_input = bytes(language + "-" + dumps(libraries_object, sort_keys=True), encoding='UTF-8')
    hash_key = sha256(
        hash_input
    ).hexdigest()
    final_s3_package_zip_path = hash_key + ".zip"

    return final_s3_package_zip_path


def get_codebuild_artifact_zip_data(aws_client_factory, credentials, build_id, final_s3_package_zip_path):
    s3_client = aws_client_factory.get_aws_client(
        "s3",
        credentials
    )

    # Wait until the codebuild is finished
    # This is pieced out so that we can also kick off codebuilds
    # without having to pull the final zip result
    finalize_codebuild(
        aws_client_factory,
        credentials,
        build_id,
        final_s3_package_zip_path
    )

    return read_from_s3(
        aws_client_factory,
        credentials,
        credentials["lambda_packages_bucket"],
        final_s3_package_zip_path
    )


def finalize_codebuild(aws_client_factory, credentials, build_id, final_s3_package_zip_path):
    codebuild_client = aws_client_factory.get_aws_client(
        "codebuild",
        credentials
    )

    s3_client = aws_client_factory.get_aws_client(
        "s3",
        credentials
    )

    build_info = {}

    # Generate output artifact location from the build ID
    build_id_parts = build_id.split(":")
    output_artifact_path = build_id_parts[1] + "/package.zip"

    build_status = None

    # Loop until we have the build information (up to ~2 minutes)
    for _ in range(50):
        # Check the status of the build we just kicked off
        codebuild_build_status_response = codebuild_client.batch_get_builds(
            ids=[
                build_id
            ]
        )
        build_info = codebuild_build_status_response["builds"][0]
        build_status = build_info["buildStatus"]

        if build_status != "IN_PROGRESS":
            break

        logit("Build ID " + build_id +
              " is still in progress, querying the status again in 2 seconds...")
        sleep(2)

    if build_status != "SUCCEEDED":
        # Pull log group
        log_group_name = build_info["logs"]["groupName"]

        # Pull stream name
        log_stream_name = build_info["logs"]["streamName"]

        log_output = get_lambda_cloudwatch_logs(
            aws_client_factory,
            credentials,
            log_group_name,
            log_stream_name
        )

        msg = "Build ID " + build_id + " failed with status code '" + build_status + "'!"
        raise BuildException(msg, log_output)

    # We now copy this artifact to a location with a deterministic hash name
    # so that we can query for its existence and cache previously-build packages.
    s3_copy_response = s3_client.copy_object(
        Bucket=credentials["lambda_packages_bucket"],
        CopySource={
            "Bucket": credentials["lambda_packages_bucket"],
            "Key": output_artifact_path
        },
        Key=final_s3_package_zip_path
    )

    return True
