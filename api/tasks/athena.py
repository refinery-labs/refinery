from csv import DictReader
from datetime import datetime
from tasks.s3 import read_from_s3
from pyconstants.project_constants import REGEX_WHITELISTS
from pystache import render
from time import sleep
from utils.general import logit
from re import sub
from utils.mapper import (
    execution_log_query_results_to_pipeline_id_dict,
    execution_pipeline_id_dict_to_frontend_format
)



try:
    # for Python 2.x
    # noinspection PyCompatibility
    from StringIO import StringIO
except ImportError:
    # for Python 3.x
    from io import StringIO


def get_athena_results_from_s3(aws_client_factory, credentials, s3_bucket, s3_path):
    csv_data = read_from_s3(
        aws_client_factory,
        credentials,
        s3_bucket,
        s3_path
    )

    csv_handler = StringIO(csv_data)
    csv_reader = DictReader(
        csv_handler,
        delimiter=",",
        quotechar='"'
    )

    return_array = []

    for row in csv_reader:
        return_array.append(
            row
        )

    return return_array


def perform_athena_query(aws_client_factory, credentials, query, return_results):
    athena_client = aws_client_factory.get_aws_client(
        "athena",
        credentials,
    )

    output_base_path = "s3://refinery-lambda-logging-" + \
        credentials["s3_bucket_suffix"] + "/athena/"

    # Start the query
    query_start_response = athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={
            "Database": "refinery"
        },
        ResultConfiguration={
            "OutputLocation": output_base_path,
            "EncryptionConfiguration": {
                "EncryptionOption": "SSE_S3"
            }
        },
        WorkGroup="refinery_workgroup"
    )

    # Ensure we have an execution ID to follow
    if not ("QueryExecutionId" in query_start_response):
        logit(query_start_response)
        raise Exception("No query execution ID in response!")

    query_execution_id = query_start_response["QueryExecutionId"]

    QUERY_FAILED_STATES = [
        "CANCELLED",
        "FAILED"
    ]

    query_status_results = {}

    # Max amount of times we'll attempt to query the execution
    # status. If the counter hits zero we break out.
    max_counter = 60

    # Poll for query status
    # For loops which do not have a discreet conditional break, we enforce
    # an upper bound of iterations.
    MAX_LOOP_ITERATIONS = 10000

    query_status_result = None

    # Bound this loop to only execute MAX_LOOP_ITERATION times since we
    # cannot guarantee that the condition `continuation_token == False`
    # will ever be true.
    for _ in xrange(MAX_LOOP_ITERATIONS):
        # Check the status of the query
        query_status_result = athena_client.get_query_execution(
            QueryExecutionId=query_execution_id
        )

        query_execution_results = {}
        query_execution_status = "RUNNING"

        if "QueryExecution" in query_status_result:
            query_execution_status = query_status_result["QueryExecution"]["Status"]["State"]

        if query_execution_status in QUERY_FAILED_STATES:
            logit(query_status_result)
            raise Exception("Athena query failed!")

        if query_execution_status == "SUCCEEDED":
            break

        sleep(1)

        # Decrement counter
        max_counter = max_counter - 1

        if max_counter <= 0:
            break

    s3_object_location = query_status_result["QueryExecution"]["ResultConfiguration"]["OutputLocation"]

    # Sometimes we don't care about the result
    # In those cases we just return the S3 path in case the caller
    # Wants to grab the results themselves later
    if not return_results:
        return s3_object_location

    # Get S3 bucket and path from the s3 location string
    # s3://refinery-lambda-logging-uoits4nibdlslbq97qhfyb6ngkvzyewf/athena/
    s3_path = s3_object_location.replace(
        "s3://refinery-lambda-logging-" + credentials["s3_bucket_suffix"],
        ""
    )

    return get_athena_results_from_s3(
        aws_client_factory,
        credentials,
        "refinery-lambda-logging-" + credentials["s3_bucket_suffix"],
        s3_path
    )



GET_BLOCK_EXECUTIONS = """
    SELECT type, id, function_name, timestamp, dt
    FROM "refinery"."{{{project_id_table_name}}}"
    WHERE project_id = '{{{project_id}}}' AND
    arn = '{{{arn}}}' AND
    execution_pipeline_id = '{{{execution_pipeline_id}}}' AND
    dt > '{{{oldest_timestamp}}}'
    ORDER BY type, timestamp DESC
"""


def get_block_executions(aws_client_factory, credentials, project_id, execution_pipeline_id, arn, oldest_timestamp):
    project_id = sub(REGEX_WHITELISTS["project_id"], "", project_id)
    timestamp_datetime = datetime.fromtimestamp(oldest_timestamp)

    # Since there's no parameterized querying for Athena we're gonna get ghetto with
    # the SQL injection mitigation. Joe, if you ever join this company or review this code
    # I blame this all on Free even though the git blame will say otherwise.
    query_template_data = {
        "execution_pipeline_id": sub(REGEX_WHITELISTS["execution_pipeline_id"], "", execution_pipeline_id),
        "project_id_table_name": "PRJ_" + project_id.replace("-", "_"),
        "arn": sub(REGEX_WHITELISTS["arn"], "", arn),
        "project_id": sub(REGEX_WHITELISTS["project_id"], "", project_id),
        "oldest_timestamp": timestamp_datetime.strftime("%Y-%m-%d-%H-%M"),
    }

    query = render(GET_BLOCK_EXECUTIONS, query_template_data)

    # Query for project execution logs
    logit("Performing Athena query...")
    query_results = perform_athena_query(
        aws_client_factory,
        credentials,
        query,
        True
    )

    logit("Processing Athena results...")

    # Format query results
    for query_result in query_results:
        # For the front-end
        query_result["log_id"] = query_result["id"]
        query_result["timestamp"] = int(query_result["timestamp"])
        del query_result["id"]

        # Generate a log path from the available data
        # example: PROJECT_ID/dt=DATE_SHARD/EXECUTION_PIPELINE_ID/TYPE~NAME~LOG_ID~TIMESTAMP

        log_file_path = project_id + "/dt=" + query_result["dt"]
        log_file_path += "/" + execution_pipeline_id + "/"
        log_file_path += query_result["type"] + "~"
        log_file_path += query_result["function_name"] + "~"
        log_file_path += query_result["log_id"] + "~"
        log_file_path += str(query_result["timestamp"])

        query_result["s3_key"] = log_file_path

        del query_result["dt"]

    logit("Athena results have been processed.")

    return query_results


# We set case sensitivity (because of nested JSON) and to ignore malformed JSON (just in case)
CREATE_PROJECT_ID_LOG_TABLE = """
    CREATE EXTERNAL TABLE IF NOT EXISTS refinery.{{REPLACE_ME_PROJECT_TABLE_NAME}} (
        `arn` string,
        `aws_region` string,
        `aws_request_id` string,
        `function_name` string,
        `function_version` string,
        `group_name` string,
        `id` string,
        `initialization_time` int,
        `invoked_function_arn` string,
        `memory_limit_in_mb` int,
        `name` string,
        `project_id` string,
        `stream_name` string,
        `timestamp` int,
        `type` string,
        `program_output` string,
        `input_data` string,
        `backpack` string,
        `return_data` string,
        `execution_pipeline_id` string
    )
    PARTITIONED BY (dt string)
    ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
    WITH SERDEPROPERTIES (
        'serialization.format' = '1',
        'ignore.malformed.json' = 'true',
        'case.insensitive' = 'false'
    ) LOCATION 's3://refinery-lambda-logging-{{S3_BUCKET_SUFFIX}}/{{REPLACE_ME_PROJECT_ID}}/'
    TBLPROPERTIES ('has_encrypted_data'='false');
"""


def create_project_id_log_table(aws_client_factory, credentials, project_id):
    project_id = sub(REGEX_WHITELISTS["project_id"], "", project_id)
    table_name = "PRJ_" + project_id.replace("-", "_")


    # Replace with the formatted Athena table name
    query = CREATE_PROJECT_ID_LOG_TABLE.replace(
        "{{REPLACE_ME_PROJECT_TABLE_NAME}}",
        table_name
    )

    # Replace with the actually project UUID
    query = query.replace(
        "{{REPLACE_ME_PROJECT_ID}}",
        project_id
    )

    # Replace the S3 bucket name with the actual
    # bucket
    query = query.replace(
        "{{S3_BUCKET_SUFFIX}}",
        credentials["s3_bucket_suffix"]
    )

    # Perform the table creation query
    return perform_athena_query(
        aws_client_factory,
        credentials,
        query,
        False
    )



GET_PROJECT_EXECUTION_LOGS = """
    SELECT arn, type, execution_pipeline_id, timestamp, dt, COUNT(*) as count
    FROM "refinery"."{{{project_id_table_name}}}"
    WHERE dt >= '{{{oldest_timestamp}}}'
    GROUP BY arn, type, execution_pipeline_id, timestamp, dt ORDER BY timestamp LIMIT 100000
"""


def get_project_execution_logs(aws_client_factory, credentials, project_id, oldest_timestamp):
    timestamp_datetime = datetime.fromtimestamp(oldest_timestamp)
    project_id = sub(REGEX_WHITELISTS["project_id"], "", project_id)

    query_template_data = {
        "project_id_table_name": "PRJ_" + project_id.replace("-", "_"),
        "oldest_timestamp": timestamp_datetime.strftime("%Y-%m-%d-%H-%M")
    }

    query = render(
        GET_PROJECT_EXECUTION_LOGS,
        query_template_data
    )

    # Query for project execution logs
    query_results = perform_athena_query(
        aws_client_factory,
        credentials,
        query,
        True
    )

    # Convert the Athena query results into an execution pipeline ID with the
    # results sorted into a dictionary with the key being the execution pipeline ID
    # and the value being an object with information about the total executions for
    # the execution pipeline ID and the block ARN execution totals contained within
    # that execution pipeline.
    execution_pipeline_id_dict = execution_log_query_results_to_pipeline_id_dict(
        query_results
    )

    return execution_pipeline_id_dict_to_frontend_format(
        execution_pipeline_id_dict
    )
