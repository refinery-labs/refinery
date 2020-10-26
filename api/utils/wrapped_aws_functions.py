from __future__ import annotations

# The various functions in this file are just wrapped AWS functions with retry logic configured
from enum import Enum
from typing import AnyStr, List, Type, Any, Generic, Dict, Union, Optional, TYPE_CHECKING

from assistants.decorators import aws_exponential_backoff, NOT_FOUND_EXCEPTION, RESOURCE_IN_USE_EXCEPTION, \
    RESOURCE_NOT_FOUND_EXCEPTION

if TYPE_CHECKING:
    from assistants.deployments.aws.api_endpoint import ApiEndpointWorkflowState


@aws_exponential_backoff()
def api_gateway_create_rest_api(
        api_gateway_client,
        name: AnyStr,
        description: AnyStr,
        version: int,
        api_key_source: AnyStr,
        endpoint_configuration: Dict[AnyStr, List[AnyStr]],
        binary_media_types: List[AnyStr],
        tags: Dict[AnyStr, AnyStr],
        **kwargs
):
    return api_gateway_client.create_rest_api(
        name=name,
        description=description,
        version=version,
        apiKeySource=api_key_source,
        endpointConfiguration=endpoint_configuration,
        binaryMediaTypes=binary_media_types,
        tags=tags,
        **kwargs
    )


@aws_exponential_backoff()
def api_gateway_create_deployment(api_gateway_client, rest_api_id: AnyStr, stage_name: AnyStr):
    return api_gateway_client.create_deployment(
        restApiId=rest_api_id,
        stageName=stage_name,
        stageDescription="API Gateway deployment deployed via refinery",
        description="API Gateway deployment deployed via refinery"
    )


@aws_exponential_backoff()
def api_gateway_create_resource(api_gateway_client, rest_api_id: AnyStr, parent_id: AnyStr, path_part: AnyStr):
    return api_gateway_client.create_resource(
        restApiId=rest_api_id,
        parentId=parent_id,
        pathPart=path_part
    )


@aws_exponential_backoff(breaking_errors=[NOT_FOUND_EXCEPTION])
def api_gateway_delete_stage(api_gateway_client, rest_api_id: AnyStr, stage_name: AnyStr, **kwargs):
    return api_gateway_client.delete_stage(restApiId=rest_api_id, stageName=stage_name, **kwargs)


@aws_exponential_backoff(breaking_errors=[NOT_FOUND_EXCEPTION])
def api_gateway_delete_rest_api(api_gateway_client, rest_api_id: AnyStr):
    return api_gateway_client.delete_rest_api(
        restApiId=rest_api_id,
    )


@aws_exponential_backoff(breaking_errors=[NOT_FOUND_EXCEPTION])
def api_gateway_delete_rest_api_resource(api_gateway_client, rest_api_id: AnyStr, resource_id: AnyStr):
    return api_gateway_client.delete_resource(
        restApiId=rest_api_id,
        resourceId=resource_id,
    )


@aws_exponential_backoff(breaking_errors=[NOT_FOUND_EXCEPTION])
def api_gateway_delete_rest_api_resource_method(
        api_gateway_client,
        rest_api_id: AnyStr,
        resource_id: AnyStr,
        method: AnyStr
):
    return api_gateway_client.delete_method(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod=method,
    )


@aws_exponential_backoff()
def api_gateway_get_rest_api(api_gateway_client, rest_api_id: AnyStr, **kwargs):
    return api_gateway_client.get_rest_api(restApiId=rest_api_id, **kwargs)


@aws_exponential_backoff()
def api_gateway_get_resources(api_gateway_client, rest_api_id: AnyStr, embed: List[AnyStr], limit: int = 500, **kwargs):
    return api_gateway_client.get_resources(restApiId=rest_api_id, limit=limit, embed=embed, **kwargs)


@aws_exponential_backoff()
def api_gateway_get_stages(api_gateway_client, rest_api_id: AnyStr, **kwargs):
    return api_gateway_client.get_stages(restApiId=rest_api_id, **kwargs)


@aws_exponential_backoff(max_attempts=10)
def api_gateway_put_integration(api_gateway_client, rest_api_id, resource_id, api_endpoint, lambda_uri):
    return api_gateway_client.put_integration(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod=api_endpoint.http_method,
        type="AWS_PROXY",
        # MUST be POST: https://github.com/boto/boto3/issues/572#issuecomment-239294381
        integrationHttpMethod="POST",
        uri=lambda_uri,
        connectionType="INTERNET",
        timeoutInMillis=29000  # 29 seconds
    )


@aws_exponential_backoff(max_attempts=10)
def api_gateway_put_integration_response(api_gateway_client, rest_api_id, resource_id, api_endpoint):
    return api_gateway_client.put_integration_response(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod=api_endpoint.http_method,
        statusCode="200",
        contentHandling="CONVERT_TO_TEXT"
    )


@aws_exponential_backoff(max_attempts=10)
def api_gateway_put_method(
        api_gateway_client,
        rest_api_id: AnyStr,
        resource_id: AnyStr,
        http_method: AnyStr,
        api_key_required: bool,
        method_name: AnyStr
):
    return api_gateway_client.put_method(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod=http_method,
        authorizationType="NONE",
        apiKeyRequired=api_key_required,
        operationName=method_name,
    )


@aws_exponential_backoff()
def lambda_check_if_function_exists(aws_client_factory, credentials, lambda_object):
    lambda_client = aws_client_factory.get_aws_client(
        "lambda",
        credentials
    )

    try:
        response = lambda_client.get_function(
            FunctionName=lambda_object.name
        )
    except lambda_client.exceptions.ResourceNotFoundException:
        return False

    return True


@aws_exponential_backoff()
def lambda_create_event_source_mapping(
        lambda_client,
        event_source_arn: AnyStr,
        function_name: AnyStr,
        enabled: bool,
        batch_size: int,
        **kwargs
):
    return lambda_client.create_event_source_mapping(
        EventSourceArn=event_source_arn,
        FunctionName=function_name,
        Enabled=enabled,
        BatchSize=batch_size,
        **kwargs
    )


@aws_exponential_backoff()
def delete_aws_lambda(aws_client_factory, credentials, arn_or_name):
    lambda_client = aws_client_factory.get_aws_client("lambda", credentials)
    return lambda_client.delete_function(FunctionName=arn_or_name)


@aws_exponential_backoff(allowed_errors=[RESOURCE_IN_USE_EXCEPTION])
def lambda_delete_event_source_mapping(lambda_client, mapping):
    return lambda_client.delete_event_source_mapping(
        UUID=mapping.uuid
    )


@aws_exponential_backoff(breaking_errors=[RESOURCE_NOT_FOUND_EXCEPTION])
def lambda_delete_function(lambda_client, arn: AnyStr):
    return lambda_client.delete_function(
        FunctionName=arn,
    )


@aws_exponential_backoff(breaking_errors=[RESOURCE_NOT_FOUND_EXCEPTION])
def lambda_get_layer_version(lambda_client, layer_name: AnyStr, version: int):
    return lambda_client.get_layer_version(LayerName=layer_name, VersionNumber=version)


@aws_exponential_backoff()
def lambda_get_policy(lambda_client, function_name: AnyStr):
    return lambda_client.get_policy(FunctionName=function_name)


class LambdaInvocationType(Enum):
    EVENT = 'Event'
    REQUEST_RESPONSE = 'RequestResponse',
    DRY_RUN = 'DryRun'


class LambdaLogType(Enum):
    NONE = 'None',
    TAIL = 'Tail'


@aws_exponential_backoff()
def lambda_invoke(
        lambda_client,
        arn: AnyStr,
        invocation_type: LambdaInvocationType,
        payload: AnyStr,
        log_type: LambdaLogType = LambdaLogType.TAIL
):
    return lambda_client.invoke(
        FunctionName=arn,
        InvocationType=str(invocation_type.value[0]),
        LogType=str(log_type.value),
        Payload=payload
    )


@aws_exponential_backoff()
def lambda_list_event_source_mappings(lambda_client, **kwargs):
    return lambda_client.list_event_source_mappings(**kwargs)


@aws_exponential_backoff()
def lambda_list_functions(lambda_client, **kwargs):
    return lambda_client.list_functions(**kwargs)


@aws_exponential_backoff()
def lambda_remove_permission(lambda_client, function_name: AnyStr, statement_id: AnyStr):
    return lambda_client.remove_permission(FunctionName=function_name, StatementId=statement_id)


@aws_exponential_backoff()
def lambda_publish_layer_version(
        lambda_client,
        layer_name: AnyStr,
        description: AnyStr,
        s3_bucket: AnyStr,
        s3_object_key: AnyStr
):
    response = lambda_client.publish_layer_version(
        LayerName="RefineryManagedLayer_" + layer_name,
        Description=description,
        Content={
            "S3Bucket": s3_bucket,
            "S3Key": s3_object_key,
        },
        CompatibleRuntimes=[
            "python2.7",
            "provided",
        ],
        LicenseInfo="See layer contents for license information."
    )

    return {
        "sha256": response["Content"]["CodeSha256"],
        "size": response["Content"]["CodeSize"],
        "version": response["Version"],
        "layer_arn": response["LayerArn"],
        "layer_version_arn": response["LayerVersionArn"],
        "created_date": response["CreatedDate"]
    }

@aws_exponential_backoff()
def lambda_publish_version(
        lambda_client,
        function_name: AnyStr,
        code_sha256: AnyStr
):
    return lambda_client.publish_version(
        FunctionName=function_name,
        CodeSha256=code_sha256
    )


@aws_exponential_backoff()
def lambda_put_function_concurrency(lambda_client, **kwargs):
    return lambda_client.put_function_concurrency(**kwargs)


@aws_exponential_backoff()
def lambda_update_function_code(lambda_client, function_name: AnyStr, s3_bucket: AnyStr, s3_key: AnyStr):
    return lambda_client.update_function_code(
        FunctionName=function_name,
        S3Bucket=s3_bucket,
        S3Key=s3_key
    )


@aws_exponential_backoff()
def lambda_update_function_configuration(
        lambda_client,
        env_data: Dict[AnyStr, AnyStr],
        function_name: AnyStr,
        layers: List[AnyStr],
        memory_size: int,
        role: AnyStr,
        timeout: int,
):
    return lambda_client.update_function_configuration(
        FunctionName=function_name,
        Role=role,
        Timeout=timeout,
        MemorySize=memory_size,
        Environment={
            "Variables": env_data
        },
        Layers=layers,
    )


@aws_exponential_backoff()
def sns_create_topic(sns_client, name: AnyStr, tags: Dict[AnyStr, AnyStr]):
    return sns_client.create_topic(Name=name, Tags=tags)


@aws_exponential_backoff(breaking_errors=[RESOURCE_NOT_FOUND_EXCEPTION])
def sns_delete_topic(sns_client, arn):
    return sns_client.delete_topic(
        TopicArn=arn,
    )


@aws_exponential_backoff()
def sns_get_topic_attributes(sns_client, arn: AnyStr):
    return sns_client.get_topic_attributes(TopicArn=arn)


@aws_exponential_backoff()
def sns_list_subscriptions_by_topic(sns_client, topic_arn: AnyStr, next_token: Optional[Dict[AnyStr, AnyStr]]):

    next_token_param = dict(NextToken=next_token) if next_token is not None else dict()

    return sns_client.list_subscriptions_by_topic(TopicArn=topic_arn, **next_token_param)


@aws_exponential_backoff()
def sns_subscribe(sns_client, **kwargs):
    return sns_client.subscribe(**kwargs)


@aws_exponential_backoff()
def sqs_create_queue(sqs_client, queue_name: AnyStr, attributes: Dict[AnyStr, AnyStr], **kwargs):
    return sqs_client.create_queue(QueueName=queue_name, Attributes=attributes, **kwargs)


@aws_exponential_backoff()
def sqs_get_queue_url(sqs_client, queue_name: AnyStr, **kwargs):
    return sqs_client.get_queue_url(QueueName=queue_name, **kwargs)


@aws_exponential_backoff(max_attempts=10)
def try_to_put_api_integration(api_gateway_client, rest_api_id, resource_id, api_endpoint: ApiEndpointWorkflowState, lambda_uri):
    return api_gateway_client.put_integration(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod=api_endpoint.http_method,
        type="AWS_PROXY",
        # MUST be POST: https://github.com/boto/boto3/issues/572#issuecomment-239294381
        integrationHttpMethod="POST",
        uri=lambda_uri,
        connectionType="INTERNET",
        timeoutInMillis=29000  # 29 seconds
    )


@aws_exponential_backoff(max_attempts=10)
def try_to_put_http_api_integration(api_gateway_client, rest_api_id, resource_id, api_endpoint: ApiEndpointWorkflowState, http_url):
    return api_gateway_client.put_integration(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod=api_endpoint.http_method,
        type="HTTP_PROXY",
        integrationHttpMethod=api_endpoint.http_method,
        uri=http_url,
        connectionType="INTERNET",
        timeoutInMillis=29000  # 29 seconds
    )


@aws_exponential_backoff(max_attempts=10)
def try_to_put_integration_response(api_gateway_client, rest_api_id, resource_id, api_endpoint):
    return api_gateway_client.put_integration_response(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod=api_endpoint.http_method,
        statusCode="200",
        contentHandling="CONVERT_TO_TEXT"
    )
