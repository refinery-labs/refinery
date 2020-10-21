from __future__ import annotations

import time
from typing import TYPE_CHECKING

from assistants.decorators import aws_exponential_backoff
from assistants.deployments.aws.response_types import LambdaEventSourceMapping
from assistants.deployments.ecs_builders import BuilderManager
from assistants.deployments.shared_files import (
    add_shared_files_symlink_to_zip,
    add_shared_files_to_zip
)
from assistants.task_spawner.exceptions import InvalidLanguageException
from base64 import b64decode
from botocore.exceptions import ClientError
from json import dumps, loads

from models import InlineExecutionLambda
from pyconstants.project_constants import LAMBDA_SUPPORTED_LANGUAGES
from tasks.build.ruby import build_ruby_264_lambda
from tasks.build.golang import get_go_112_base_code
from tasks.build.nodejs import build_nodejs_10163_lambda, build_nodejs_810_lambda, build_nodejs_10201_lambda
from tasks.build.php import build_php_73_lambda
from tasks.build.python import build_python36_lambda, build_python27_lambda
from tasks.s3 import s3_object_exists
from utils.general import logit, log_exception
from utils.wrapped_aws_functions import lambda_list_event_source_mappings, api_gateway_get_rest_api, \
    lambda_list_functions, lambda_put_function_concurrency, lambda_invoke, LambdaLogType, LambdaInvocationType, \
    lambda_delete_function, lambda_publish_version, lambda_update_function_code, lambda_update_function_configuration, \
    lambda_get_policy, lambda_remove_permission

if TYPE_CHECKING:
    from assistants.deployments.aws.lambda_function import LambdaWorkflowState


def get_lambda_arns(aws_client_factory, credentials):
    lambda_client = aws_client_factory.get_aws_client(
        "lambda",
        credentials
    )

    # Now we throttle all of the user's Lambdas so none will execute
    # First we pull all of the user's Lambdas
    lambda_list_params = {
        "MaxItems": 50,
    }

    # The list of Lambda ARNs
    lambda_arn_list = []

    # Don't list more than 200 pages of Lambdas (I hope this is never happens!)
    for _ in range(200):
        lambda_functions_response = lambda_list_functions(lambda_client, **lambda_list_params)

        for lambda_function_data in lambda_functions_response["Functions"]:
            lambda_arn_list.append(
                lambda_function_data["FunctionArn"]
            )

        # Only do another loop if we have more results
        if not ("NextMarker" in lambda_functions_response):
            break

        lambda_list_params["Marker"] = lambda_functions_response["NextMarker"]

    # Iterate over list of Lambda ARNs and set concurrency to zero for all
    for lambda_arn in lambda_arn_list:
        lambda_put_function_concurrency(
            lambda_client,
            FunctionName=lambda_arn,
            ReservedConcurrentExecutions=0
        )

    return lambda_arn_list


def warm_up_lambda(aws_client_factory, credentials, arn, warmup_concurrency_level):
    lambda_client = aws_client_factory.get_aws_client(
        "lambda",
        credentials
    )
    response = lambda_invoke(
        lambda_client,
        arn=arn,
        invocation_type=LambdaInvocationType.EVENT,
        log_type=LambdaLogType.TAIL,
        payload=dumps({
            "_refinery": {
                "warmup": warmup_concurrency_level,
            }
        })
    )


def execute_aws_lambda(aws_client_factory, credentials, arn, input_data):
    lambda_client = aws_client_factory.get_aws_client("lambda", credentials)
    response = lambda_invoke(
        lambda_client,
        arn=arn,
        invocation_type=LambdaInvocationType.REQUEST_RESPONSE,
        payload=dumps(input_data)
    )

    full_response = response["Payload"].read()

    # Decode it all the way
    try:
        full_response = loads(
            loads(
                full_response
            )
        )
    except BaseException:
        pass

    if type(full_response) in [dict, list]:
        # make the response pretty if we can
        full_response = dumps(
            full_response,
            indent=4
        )
    elif isinstance(full_response, bytes):
        full_response = full_response.decode('utf-8')
    else:
        full_response = str(full_response)

    # Detect from response if it was an error
    is_error = False

    if "FunctionError" in response:
        is_error = True

    log_output = b64decode(
        response["LogResult"]
    ).decode("utf-8")

    # Strip the Lambda stuff from the output
    if "RequestId:" in log_output:
        log_lines = log_output.split("\n")
        returned_log_lines = []

        for log_line in log_lines:
            if log_line.startswith("START RequestId: "):
                continue

            if log_line.startswith("END RequestId: "):
                continue

            if log_line.startswith("REPORT RequestId: "):
                continue

            if log_line.startswith("XRAY TraceId: "):
                continue

            if "START RequestId: " in log_line:
                log_line = log_line.split("START RequestId: ")[0]

            if "END RequestId: " in log_line:
                log_line = log_line.split("END RequestId: ")[0]

            if "REPORT RequestId: " in log_line:
                log_line = log_line.split("REPORT RequestId: ")[0]

            if "XRAY TraceId: " in log_line:
                log_line = log_line.split("XRAY TraceId: ")[0]

            returned_log_lines.append(
                log_line
            )

        log_output = "\n".join(returned_log_lines)

    # Mark truncated if logs are not complete
    truncated = True
    if "START RequestId: " in log_output and "END RequestId: " in log_output:
        truncated = False

    return {
        "truncated": truncated,
        "arn": arn,
        "version": response["ExecutedVersion"],
        "status_code": response["StatusCode"],
        "logs": log_output,
        "is_error": is_error,
        "returned_data": full_response,
    }


@aws_exponential_backoff()
def update_lambda_environment_variables(aws_client_factory, credentials, func_name, environment_variables):
    lambda_client = aws_client_factory.get_aws_client("lambda", credentials)

    # Generate environment variables data structure
    env_data = {}
    for env_pair in environment_variables:
        env_data[env_pair["key"]] = env_pair["value"]

    response = lambda_client.update_function_configuration(
        FunctionName=func_name,
        Environment={
            "Variables": env_data
        },
    )

    return response


def build_lambda(app_config, aws_client_factory, credentials, lambda_object):
    logit("Building Lambda " + lambda_object.language +
          " with libraries: " + str(lambda_object.libraries), "info")
    if not (lambda_object.language in LAMBDA_SUPPORTED_LANGUAGES):
        raise Exception("Error, this language '" +
                        lambda_object.language + "' is not yet supported by refinery!")

    if lambda_object.language == "python2.7":
        package_zip_data = build_python27_lambda(
            app_config,
            aws_client_factory,
            credentials,
            lambda_object.code,
            lambda_object.libraries
        )
    elif lambda_object.language == "python3.6":
        package_zip_data = build_python36_lambda(
            app_config,
            aws_client_factory,
            credentials,
            lambda_object.code,
            lambda_object.libraries
        )
    elif lambda_object.language == "php7.3":
        package_zip_data = build_php_73_lambda(
            app_config,
            aws_client_factory,
            credentials,
            lambda_object.code,
            lambda_object.libraries
        )
    elif lambda_object.language == "nodejs8.10":
        package_zip_data = build_nodejs_810_lambda(
            app_config,
            aws_client_factory,
            credentials,
            lambda_object.code,
            lambda_object.libraries
        )
    elif lambda_object.language == "nodejs10.16.3":
        package_zip_data = build_nodejs_10163_lambda(
            app_config,
            aws_client_factory,
            credentials,
            lambda_object.code,
            lambda_object.libraries
        )
    elif lambda_object.language == "nodejs10.20.1":
        package_zip_data = build_nodejs_10201_lambda(
            app_config,
            aws_client_factory,
            credentials,
            lambda_object.code,
            lambda_object.libraries
        )
    elif lambda_object.language == "go1.12":
        lambda_object.code = get_go_112_base_code(
            app_config,
            lambda_object.code
        )
        package_zip_data = BuilderManager._get_go112_zip(
            aws_client_factory,
            credentials,
            lambda_object
        )
    elif lambda_object.language == "ruby2.6.4":
        package_zip_data = build_ruby_264_lambda(
            app_config,
            aws_client_factory,
            credentials,
            lambda_object.code,
            lambda_object.libraries
        )
    else:
        raise InvalidLanguageException(
            "Unknown language supplied to build Lambda with"
        )

    # Add symlink if it's an inline execution
    if lambda_object.is_inline_execution:
        package_zip_data = add_shared_files_symlink_to_zip(
            package_zip_data
        )
    else:
        # If it's an inline execution we don't add the shared files folder because
        # we'll be live injecting them into /tmp/
        # Add shared files to Lambda package as well.
        package_zip_data = add_shared_files_to_zip(
            package_zip_data,
            lambda_object.shared_files_list
        )

    return package_zip_data


@aws_exponential_backoff()
def set_lambda_reserved_concurrency(aws_client_factory, credentials, arn, reserved_concurrency_count):
    # Create Lambda client
    lambda_client = aws_client_factory.get_aws_client(
        "lambda",
        credentials
    )

    set_concurrency_response = lambda_client.put_function_concurrency(
        FunctionName=arn,
        ReservedConcurrentExecutions=int(reserved_concurrency_count)
    )


@aws_exponential_backoff()
def upload_aws_lambda_code_to_s3(app_config, aws_client_factory, credentials, lambda_object, s3_package_zip_path):
    # Create S3 client
    s3_client = aws_client_factory.get_aws_client(
        "s3",
        credentials
    )

    # Check if we've already deployed this exact same Lambda before
    already_exists = s3_object_exists(
        aws_client_factory,
        credentials,
        credentials["lambda_packages_bucket"],
        s3_package_zip_path
    )

    # Check to see if it's in the S3 cache
    if not already_exists:
        # Build the Lambda package .zip and return the zip data for it
        lambda_zip_package_data = build_lambda(
            app_config,
            aws_client_factory,
            credentials,
            lambda_object
        )

        # Write it the cache
        s3_client.put_object(
            Key=s3_package_zip_path,
            Bucket=credentials["lambda_packages_bucket"],
            Body=lambda_zip_package_data,
        )


@log_exception
def deploy_aws_lambda(app_config, aws_client_factory, db_session_maker, lambda_manager, credentials, lambda_object: LambdaWorkflowState):
    """
    Here we do caching to see if we've done this exact build before
    (e.g. the same language, code, and libraries). If we have an the
    previous zip package is still in S3 we can just return that.

    The zip key is {{SHA256_OF_LANG-CODE-LIBRARIES}}.zip
    """
    s3_package_zip_path = lambda_object.get_s3_package_hash() + ".zip"

    upload_aws_lambda_code_to_s3(app_config, aws_client_factory, credentials, lambda_object, s3_package_zip_path)

    lambda_deploy_result = _deploy_aws_lambda(
        aws_client_factory,
        credentials,
        lambda_object,
        s3_package_zip_path,
    )

    # If it's an inline execution we can cache the
    # built Lambda and re-used it for future executions
    # that share the same configuration when run.
    if lambda_object.is_inline_execution:
        logit("Caching inline execution to speed up future runs...")
        cache_inline_lambda_execution(
            aws_client_factory,
            db_session_maker,
            lambda_manager,
            credentials,
            lambda_object,
            lambda_deploy_result["CodeSize"]
        )

    return lambda_deploy_result


@aws_exponential_backoff(allowed_errors=["ResourceConflictException"])
def _deploy_aws_lambda(aws_client_factory, credentials, lambda_object: LambdaWorkflowState, s3_package_zip_path):
    # Generate environment variables data structure
    env_data = {}
    for key, value in lambda_object.environment_variables.items():
        env_data[key] = value

    # Create Lambda client
    lambda_client = aws_client_factory.get_aws_client(
        "lambda",
        credentials
    )

    try:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#Lambda.Client.create_function
        response = lambda_client.create_function(
            FunctionName=lambda_object.name,
            Runtime="provided",
            Role=lambda_object.role,
            Handler="lambda._init",
            Code={
                "S3Bucket": credentials["lambda_packages_bucket"],
                "S3Key": s3_package_zip_path,
            },
            Description="A Lambda deployed by refinery",
            Timeout=int(lambda_object.max_execution_time),
            MemorySize=int(lambda_object.memory),
            Publish=True,
            VpcConfig={},
            Environment={
                "Variables": env_data
            },
            Tags=lambda_object.tags_dict,
            Layers=lambda_object.layers,
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceConflictException":
            lambda_client = aws_client_factory.get_aws_client("lambda", credentials)

            # Delete the existing lambda
            delete_response = lambda_delete_function(
                lambda_client,
                lambda_object.name
            )

        raise

    return response


@aws_exponential_backoff()
def publish_new_aws_lambda_version(app_config, aws_client_factory, credentials, lambda_object: LambdaWorkflowState):
    """
    Here we do caching to see if we've done this exact build before
    (e.g. the same language, code, and libraries). If we have an the
    previous zip package is still in S3 we can just return that.

    The zip key is {{SHA256_OF_LANG-CODE-LIBRARIES}}.zip
    """

    s3_package_zip_path = lambda_object.get_s3_package_hash() + ".zip"

    upload_aws_lambda_code_to_s3(app_config, aws_client_factory, credentials, lambda_object, s3_package_zip_path)

    # Create Lambda client
    lambda_client = aws_client_factory.get_aws_client(
        "lambda",
        credentials
    )

    lambda_packages_bucket = credentials["lambda_packages_bucket"]

    response = lambda_update_function_code(
        lambda_client,
        s3_bucket=lambda_packages_bucket,
        function_name=lambda_object.name,
        s3_key=s3_package_zip_path
    )

    # Generate environment variables data structure
    env_data = {}
    for key, value in lambda_object.environment_variables.items():
        env_data[key] = value

    lambda_update_function_configuration(
        lambda_client,
        env_data=env_data,
        function_name=lambda_object.name,
        layers=lambda_object.layers,
        memory_size=int(lambda_object.memory),
        role=lambda_object.role,
        timeout=int(lambda_object.max_execution_time),
    )

    response = lambda_publish_version(lambda_client, lambda_object.arn, response.get('CodeSha256'))

    new_lambda_version = response.get('Version')

    return new_lambda_version


def list_lambda_event_source_mappings(aws_client_factory, credentials, lambda_object: LambdaWorkflowState):
    return list_lambda_event_source_mappings_by_name(aws_client_factory, credentials, lambda_object.name)


# TODO we shouldn't need this, we should only be using workflow state objects
def list_lambda_event_source_mappings_by_name(aws_client_factory, credentials, lambda_name):
    lambda_client = aws_client_factory.get_aws_client(
        "lambda",
        credentials
    )

    marker = None
    source_mappings = []

    while True:
        marker_param = dict(Marker=marker) if marker is not None else dict()

        response = lambda_list_event_source_mappings(
            lambda_client,
            FunctionName=lambda_name,
            **marker_param
        )

        mappings = response["EventSourceMappings"]

        source_mappings.extend(
            [
                LambdaEventSourceMapping(mapping["UUID"], mapping["EventSourceArn"], mapping["State"])
                for mapping in mappings
            ]
        )

        marker = response.get("NextMarker")
        if marker is None:
            break

    return source_mappings


def get_cached_inline_execution_lambda_entries(db_session_maker, credentials):
    # Check how many inline execution Lambdas we already have
    # saved in AWS. If it's too many we need to clean up!
    # Get the oldest saved inline execution from the stack and
    # delete it from AWS. This way we don't fill up the 75GB
    # per-account limitation!
    dbsession = db_session_maker()
    existing_inline_execution_lambdas_objects = dbsession.query(
        InlineExecutionLambda
    ).filter_by(
        aws_account_id=credentials["id"]
    ).order_by(
        InlineExecutionLambda.last_used_timestamp.asc()
    ).all()

    existing_inline_execution_lambdas = []

    for existing_inline_execution_lambdas_object in existing_inline_execution_lambdas_objects:
        existing_inline_execution_lambdas.append(
            existing_inline_execution_lambdas_object.to_dict()
        )

    dbsession.close()

    logit(
        "Number of existing Lambdas cached for inline executions: " +
        str(len(existing_inline_execution_lambdas_objects))
    )

    return existing_inline_execution_lambdas


def delete_cached_inline_execution_lambda(aws_client_factory, db_session_maker, lambda_manager, credentials, arn, lambda_uuid):
    # TODO: Call instance method not the static one
    # noinspection PyProtectedMember
    lambda_manager._delete_lambda(
        aws_client_factory,
        credentials,
        False,
        False,
        None,
        arn
    )

    # Delete the Lambda from the database now that we've
    # deleted it from AWS.
    dbsession = db_session_maker()
    dbsession.query(InlineExecutionLambda).filter_by(
        id=lambda_uuid
    ).delete()
    dbsession.commit()
    dbsession.close()


def add_inline_execution_lambda_entry(db_session_maker, credentials, inline_execution_hash_key, arn, lambda_size):
    # Add Lambda to inline execution database so we know we can
    # re-use it at a later time.
    dbsession = db_session_maker()
    inline_execution_lambda = InlineExecutionLambda()
    inline_execution_lambda.unique_hash_key = inline_execution_hash_key
    inline_execution_lambda.arn = arn
    inline_execution_lambda.size = lambda_size
    inline_execution_lambda.aws_account_id = credentials["id"]
    dbsession.add(inline_execution_lambda)
    dbsession.commit()
    dbsession.close()


def cache_inline_lambda_execution(aws_client_factory, db_session_maker, lambda_manager, credentials, lambda_object, lambda_size):
    # Maximum amount of inline execution Lambdas to leave deployed
    # at a time in AWS. This is a tradeoff between speed and storage
    # amount consumed in AWS.
    max_number_of_inline_execution_lambdas = 20

    # Pull previous database entries for inline execution Lambdas we're caching
    existing_inline_execution_lambdas = get_cached_inline_execution_lambda_entries(
        db_session_maker,
        credentials
    )

    if existing_inline_execution_lambdas and len(existing_inline_execution_lambdas) > max_number_of_inline_execution_lambdas:
        number_of_lambdas_to_delete = len(
            existing_inline_execution_lambdas) - max_number_of_inline_execution_lambdas

        logit("Deleting #" + str(number_of_lambdas_to_delete) +
              " old cached inline execution Lambda(s) from AWS...")

        lambdas_to_delete = existing_inline_execution_lambdas[:number_of_lambdas_to_delete]

        for lambda_to_delete in lambdas_to_delete:
            logit("Deleting '" + lambda_to_delete["arn"] + "' from AWS...")

            delete_cached_inline_execution_lambda(
                aws_client_factory,
                db_session_maker,
                lambda_manager,
                credentials,
                lambda_to_delete["arn"],
                lambda_to_delete["id"]
            )

    add_inline_execution_lambda_entry(
        db_session_maker,
        credentials,
        lambda_object.get_content_hash(),
        lambda_object.arn,
        lambda_size
    )


def clean_lambda_iam_policies(aws_client_factory, credentials, lambda_name):
    lambda_client = aws_client_factory.get_aws_client(
        "lambda",
        credentials
    )

    api_gateway_client = aws_client_factory.get_aws_client(
        "apigateway",
        credentials
    )

    logit("Cleaning up IAM policies from no-longer-existing API Gateways attached to Lambda...")
    try:
        response = lambda_get_policy(
            lambda_client,
            function_name=lambda_name,
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            return {}
        raise

    existing_lambda_statements = loads(
        response["Policy"]
    )["Statement"]

    for statement in existing_lambda_statements:
        # Try to extract API gateway
        try:
            source_arn = statement["Condition"]["ArnLike"]["AWS:SourceArn"]
            arn_parts = source_arn.split(":")
        except BaseException:
            continue

        # Make sure it's an API Gateway policy
        if not source_arn.startswith("arn:aws:execute-api:"):
            continue

        try:
            api_gateway_id = arn_parts[5]
            api_gateway_data = api_gateway_get_rest_api(
                api_gateway_client,
                rest_api_id=api_gateway_id
            )
        except BaseException:
            logit("API Gateway does not exist, deleting IAM policy...")

            delete_permission_response = lambda_remove_permission(
                lambda_client,
                function_name=lambda_name,
                statement_id=statement["Sid"]
            )

    return {}
