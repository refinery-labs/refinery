from botocore.exceptions import ClientError
from json import loads, dumps


def s3_object_exists(aws_client_factory, credentials, bucket_name, object_key):
    s3_client = aws_client_factory.get_aws_client(
        "s3",
        credentials
    )

    already_exists = False
    try:
        s3_head_response = s3_client.head_object(
            Bucket=bucket_name,
            Key=object_key
        )

        # If we didn't encounter a not-found exception, it exists.
        already_exists = True
    except ClientError as e:
        pass

    return already_exists


def get_json_from_s3(aws_client_factory, credentials, s3_bucket, s3_path):
    # Create S3 client
    s3_client = aws_client_factory.get_aws_client(
        "s3",
        credentials
    )

    response = s3_client.get_object(
        Bucket=s3_bucket,
        Key=s3_path
    )

    return loads(
        response["Body"].read()
    )


def write_json_to_s3(aws_client_factory, credentials, s3_bucket, s3_path, input_data):
    # Create S3 client
    s3_client = aws_client_factory.get_aws_client(
        "s3",
        credentials
    )

    return s3_client.put_object(
        Bucket=s3_bucket,
        Key=s3_path,
        ACL="private",
        Body=dumps(input_data)
    )


def read_from_s3(aws_client_factory, credentials, s3_bucket, path):
    s3_client = aws_client_factory.get_aws_client(
        "s3",
        credentials,
    )

    # Remove leading / because they are almost always not intended
    if path.startswith("/"):
        path = path[1:]

    try:
        s3_object = s3_client.get_object(
            Bucket=s3_bucket,
            Key=path
        )
    except BaseException:
        return "{}"

    return s3_object["Body"].read()


def read_from_s3_and_return_input(aws_client_factory, credentials, s3_bucket, path):
    return_data = read_from_s3(
        aws_client_factory,
        credentials,
        s3_bucket,
        path
    )

    return {
        "s3_bucket": s3_bucket,
        "path": path,
        "body": return_data
    }


def bulk_s3_delete(aws_client_factory, credentials, s3_bucket, s3_path_list):
    s3_client = aws_client_factory.get_aws_client(
        "s3",
        credentials,
    )

    delete_data = []

    for s3_path in s3_path_list:
        delete_data.append({
            "Key": s3_path,
        })

    response = s3_client.delete_objects(
        Bucket=s3_bucket,
        Delete={
            "Objects": delete_data
        },
    )

    return response


def get_s3_pipeline_execution_logs(aws_client_factory, credentials, s3_prefix, max_results):
    return get_all_s3_paths(
        aws_client_factory,
        credentials,
        credentials["logs_bucket"],
        s3_prefix,
        max_results
    )


def get_build_packages(aws_client_factory, credentials, s3_prefix, max_results):
    return get_all_s3_paths(
        aws_client_factory,
        credentials,
        credentials["lambda_packages_bucket"],
        s3_prefix,
        max_results
    )


def get_s3_list_from_prefix(aws_client_factory, credentials, s3_bucket, s3_prefix, continuation_token, start_after):
    s3_client = aws_client_factory.get_aws_client(
        "s3",
        credentials,
    )

    s3_options = {
        "Bucket": s3_bucket,
        "Prefix": s3_prefix,
        "Delimiter": "/",
        "MaxKeys": 1000,
    }

    if continuation_token:
        s3_options["ContinuationToken"] = continuation_token

    if start_after:
        s3_options["StartAfter"] = start_after

    object_list_response = s3_client.list_objects_v2(
        **s3_options
    )

    common_prefixes = []

    # Handle the case of no prefixs (no logs written yet)
    if not ("CommonPrefixes" in object_list_response):
        return {
            "common_prefixes": [],
            "continuation_token": False
        }

    for result in object_list_response["CommonPrefixes"]:
        common_prefixes.append(
            result["Prefix"]
        )

    if "NextContinuationToken" in object_list_response:
        continuation_token = object_list_response["NextContinuationToken"]

    # Sort list of prefixs to keep then canonicalized
    # for the hash key used to determine if we need to
    # re-partition the Athena table.
    common_prefixes.sort()

    return {
        "common_prefixes": common_prefixes,
        "continuation_token": continuation_token
    }


def get_all_s3_paths(aws_client_factory, credentials, s3_bucket, prefix, max_results, **kwargs):
    s3_client = aws_client_factory.get_aws_client(
        "s3",
        credentials,
    )

    return_array = []
    continuation_token = False
    if max_results == -1:  # max_results -1 means get all results
        max_keys = 1000
    elif max_results <= 1000:
        max_keys = max_results
    else:
        max_keys = 1000

    # First check to prime it
    response = s3_client.list_objects_v2(
        Bucket=s3_bucket,
        Prefix=prefix,
        MaxKeys=max_keys,  # Max keys you can request at once
        **kwargs
    )

    # Only list up to 10k pages (I hope this never happens!)
    for _ in xrange(10000):
        if continuation_token:
            # Grab another page of results
            response = s3_client.list_objects_v2(
                Bucket=s3_bucket,
                Prefix=prefix,
                MaxKeys=max_keys,  # Max keys you can request at once
                ContinuationToken=continuation_token,
                **kwargs
            )

        if not ("Contents" in response):
            break

        for s3_object in response["Contents"]:
            return_array.append(
                s3_object["Key"]
            )

        # If the length is longer than the max results amount
        # then just return the data.
        if (max_results != -1) and max_results <= len(return_array):
            break

        if not response["IsTruncated"]:
            break

        continuation_token = response["NextContinuationToken"]

    return return_array


def get_s3_pipeline_execution_ids(aws_client_factory, credentials, timestamp_prefix, max_results, continuation_token):
    return get_all_s3_prefixes(
        aws_client_factory,
        credentials,
        credentials["logs_bucket"],
        timestamp_prefix,
        max_results,
        continuation_token
    )


def get_s3_pipeline_timestamp_prefixes(aws_client_factory, credentials, project_id, max_results, continuation_token):
    return get_all_s3_prefixes(
        aws_client_factory,
        credentials,
        credentials["logs_bucket"],
        project_id + "/",
        max_results,
        continuation_token
    )


def get_all_s3_prefixes(aws_client_factory, credentials, s3_bucket, prefix, max_results, continuation_token):
    s3_client = aws_client_factory.get_aws_client(
        "s3",
        credentials,
    )

    return_array = []
    if max_results == -1:  # max_results -1 means get all results
        max_keys = 1000
    elif max_results <= 1000:
        max_keys = max_results
    else:
        max_keys = 1000

    list_objects_params = {
        "Bucket": s3_bucket,
        "Prefix": prefix,
        "MaxKeys": max_keys,  # Max keys you can request at once
        "Delimiter": "/"
    }

    if continuation_token:
        list_objects_params["ContinuationToken"] = continuation_token

    # First check to prime it
    response = s3_client.list_objects_v2(
        **list_objects_params
    )

    # Bound this loop to only execute MAX_LOOP_ITERATION times since we
    # cannot guarantee that the condition `continuation_token == False`
    # will ever be true.
    for _ in xrange(1000):
        if continuation_token:
            list_objects_params["ContinuationToken"] = continuation_token
            # Grab another page of results
            response = s3_client.list_objects_v2(
                **list_objects_params
            )

        if "NextContinuationToken" in response:
            continuation_token = response["NextContinuationToken"]
        else:
            continuation_token = False

        # No results
        if not ("CommonPrefixes" in response):
            break

        for s3_prefix in response["CommonPrefixes"]:
            return_array.append(
                s3_prefix["Prefix"]
            )

        # If the length is longer than the max results amount
        # then just return the data.
        if (max_results != -1) and max_results <= len(return_array):
            break

        if not response["IsTruncated"]:
            break

    return {
        "prefixes": return_array,
        "continuation_token": continuation_token
    }
