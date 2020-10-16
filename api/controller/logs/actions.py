import datetime
import re
import time

from tornado import gen

from models import CachedExecutionLogsShard
from pyconstants.project_constants import REGEX_WHITELISTS
from utils.general import logit
from utils.locker import AcquireFailure
from utils.mapper import execution_pipeline_id_dict_to_frontend_format
from utils.mapper import execution_log_query_results_to_pipeline_id_dict


@gen.coroutine
def delete_logs(task_spawner, credentials, project_id):
    for _ in range(1000):
        # Delete 1K logs at a time
        log_paths = yield task_spawner.get_s3_pipeline_execution_logs(
            credentials,
            project_id + "/",
            1000
        )

        logit("Deleting #" + str(len(log_paths)) + " log files for project ID " + project_id + "...")

        if len(log_paths) == 0:
            break

        yield task_spawner.bulk_s3_delete(
            credentials,
            credentials["logs_bucket"],
            log_paths
        )


def chunk_list(input_list, chunk_size):
    """
    Chunk an input list into a list of lists
    of size chunk_size. (e.g. 10 lists of size 100)
    """
    def _chunk_list(input_list, chunk_size):
        for i in range(0, len(input_list), chunk_size):
            yield input_list[i:i + chunk_size]
    return list(_chunk_list(
        input_list,
        chunk_size
    ))


@gen.coroutine
def write_remaining_project_execution_log_pages(task_spawner, credentials, data_to_write_list):
    # How many logs to write to S3 in parallel
    parallel_write_num = 5

    # Futures for the writes
    s3_write_futures = []

    # Write results to S3
    for i in range(0, parallel_write_num):
        if len(data_to_write_list) == 0:
            break

        data_to_write = data_to_write_list.pop(0)
        s3_write_futures.append(
            task_spawner.write_json_to_s3(
                credentials,
                credentials["logs_bucket"],
                data_to_write["s3_path"],
                data_to_write["chunked_data"]
            )
        )

        # If we've hit our parallel write number
        # We should yield and wait for the results
        s3_write_futures_number = len(s3_write_futures)
        if s3_write_futures_number >= 5:
            logit("Writing batch of #" + str(s3_write_futures_number) + " page(s) of search results to S3...")
            yield s3_write_futures

            # Clear list of futures
            s3_write_futures = []

    # If there are remaining futures we need to yield them
    s3_write_futures_number = len(s3_write_futures)
    if s3_write_futures_number > 0:
        logit("Writing remaining batch of #" + str(s3_write_futures_number) + " page(s) of search results to S3...")
        yield s3_write_futures


@gen.coroutine
def do_update_athena_table_partitions(task_spawner, db_session_maker, task_locker, credentials, project_id):
    dbsession = db_session_maker()

    yield update_athena_table_partitions(task_spawner, credentials, project_id)


@gen.coroutine
def update_athena_table_partitions(task_spawner, credentials, project_id):
    """
    Check all the partitions that are in the Athena project table and
    check S3 to see if there are any partitions which need to be added to the
    table. If there are then kick off a query to load the new partitions.
    """
    project_id = re.sub(REGEX_WHITELISTS["project_id"], "", project_id)
    query_template = "SHOW PARTITIONS PRJ_{{PROJECT_ID_REPLACE_ME}}"

    query = query_template.replace(
        "{{PROJECT_ID_REPLACE_ME}}",
        project_id.replace(
            "-",
            "_"
        )
    )

    logit("Retrieving table partitions... ", "debug")
    results = yield task_spawner.perform_athena_query(
        credentials,
        query,
        True
    )

    athena_known_shards = []

    for result in results:
        for key, shard_string in result.items():
            if not (shard_string in athena_known_shards):
                athena_known_shards.append(
                    shard_string
                )

    athena_known_shards.sort()

    # S3 pulled shards
    s3_pulled_shards = []

    continuation_token = False

    s3_prefix = project_id + "/"

    latest_athena_known_shard = False
    if len(athena_known_shards) > 0:
        latest_athena_known_shard = s3_prefix + athena_known_shards[-1]

    # For loops which do not have a discreet conditional break, we enforce
    # an upper bound of iterations.
    MAX_LOOP_ITERATIONS = 1000

    # Bound this loop to only execute MAX_LOOP_ITERATION times since we
    # cannot guarantee that the condition `continuation_token == False`
    # will ever be true.
    for _ in range(MAX_LOOP_ITERATIONS):
        s3_list_results = yield task_spawner.get_s3_list_from_prefix(
            credentials,
            credentials["logs_bucket"],
            s3_prefix,
            continuation_token,
            latest_athena_known_shard
        )

        s3_shards = s3_list_results["common_prefixes"]
        continuation_token = s3_list_results["continuation_token"]

        # Add all new shards to the list
        for s3_shard in s3_shards:
            if not (s3_shard in s3_pulled_shards):
                s3_pulled_shards.append(
                    s3_shard
                )

        # No further to go, we've exhausted the continuation token
        if continuation_token == False:
            break

    # The list of shards which have not been imported into Athena
    new_s3_shards = []

    for s3_pulled_shard in s3_pulled_shards:
        # Clean it up so it's just dt=2019-07-15-04-45
        s3_pulled_shard = s3_pulled_shard.replace(
            project_id,
            ""
        )
        s3_pulled_shard = s3_pulled_shard.replace(
            "/",
            ""
        )

        if not (s3_pulled_shard in athena_known_shards):
            new_s3_shards.append(
                s3_pulled_shard
            )

    # If we have new partitions let's load them.
    if len(new_s3_shards) > 0:
        yield load_further_partitions(
            task_spawner,
            credentials,
            project_id,
            new_s3_shards
        )

    raise gen.Return()


@gen.coroutine
def load_further_partitions(task_spawner, credentials, project_id, new_shards_list):
    project_id = re.sub(REGEX_WHITELISTS["project_id"], "", project_id)

    query_template = "ALTER TABLE PRJ_{{PROJECT_ID_REPLACE_ME}} ADD IF NOT EXISTS\n"

    query = query_template.replace(
        "{{PROJECT_ID_REPLACE_ME}}",
        project_id.replace(
            "-",
            "_"
        )
    )

    for new_shard in new_shards_list:
        query += "PARTITION (dt = '" + new_shard.replace("dt=", "") + "') "
        query += "LOCATION 's3://" + credentials["logs_bucket"] + "/"
        query += project_id + "/" + new_shard + "/'\n"

    logit("Updating previously un-indexed partitions... ", "debug")
    yield task_spawner.perform_athena_query(
        credentials,
        query,
        False
    )


def get_five_minute_dt_from_dt(input_datetime):
    round_to = (60 * 5)

    seconds = (input_datetime.replace(tzinfo=None) - input_datetime.min).seconds
    rounding = (seconds + round_to / 2) // round_to * round_to
    nearest_datetime = input_datetime + datetime.timedelta(0, rounding - seconds, - input_datetime.microsecond)
    return nearest_datetime


def dt_to_shard(input_dt):
    return input_dt.strftime("%Y-%m-%d-%H-%M")


@gen.coroutine
def get_execution_stats_since_timestamp(db_session_maker, task_spawner, credentials, project_id, oldest_timestamp):
    # Database session for pulling cached data
    dbsession = db_session_maker()

    # Grab a shard dt ten minutes in the future just to make sure
    # we've captured everything appropriately
    newest_shard_dt = get_five_minute_dt_from_dt(
        datetime.datetime.now() + datetime.timedelta(minutes=5)
    )
    newest_shard_dt_shard = dt_to_shard(newest_shard_dt)

    # Shard dt that we can be sure is actually done and the results
    # pulled from S3 can be cached in the database.
    assured_cachable_dt = get_five_minute_dt_from_dt(
        datetime.datetime.now() - datetime.timedelta(minutes=5)
    )
    assured_cachable_dt_shard = dt_to_shard(assured_cachable_dt)

    # Generate the shard dt for the oldest_timestamp
    oldest_shard_dt = get_five_minute_dt_from_dt(
        datetime.datetime.fromtimestamp(
            oldest_timestamp
        )
    )
    oldest_shard_dt_shard = dt_to_shard(oldest_shard_dt)

    # Standard S3 prefix before date for all S3 shards
    s3_prefix = project_id + "/dt="

    example_shard = s3_prefix + oldest_shard_dt_shard

    all_s3_shards = []

    common_prefixes = []

    continuation_token = False

    # For loops which do not have a discreet conditional break, we enforce
    # an upper bound of iterations.
    MAX_LOOP_ITERATIONS = 1000

    # Bound this loop to only execute MAX_LOOP_ITERATION times since we
    # cannot guarantee that the condition `continuation_token == False`
    # will ever be true.
    for _ in range(MAX_LOOP_ITERATIONS):
        # List shards in the S3 bucket starting at the oldest available shard
        # That's because S3 buckets will start at the oldest time and end at
        # the latest time (due to inverse binary UTF-8 sort order)
        s3_list_results = yield task_spawner.get_s3_list_from_prefix(
            credentials,
            credentials["logs_bucket"],
            s3_prefix,
            continuation_token,
            example_shard
        )

        current_common_prefixes = s3_list_results["common_prefixes"]
        continuation_token = s3_list_results["continuation_token"]

        # Add all new shards to the list
        for common_prefix in current_common_prefixes:
            if not (common_prefix in common_prefixes):
                common_prefixes.append(
                    common_prefix
                )

        # No further to go, we've exhausted the continuation token
        if continuation_token == False:
            break

    for shard_full_path in common_prefixes:
        # Clean it up so it's just dt=2019-07-15-04-45
        shard_full_path = shard_full_path.replace(
            project_id,
            ""
        )
        shard_full_path = shard_full_path.replace(
            "/",
            ""
        )

        if not (shard_full_path in all_s3_shards):
            all_s3_shards.append(
                shard_full_path
            )

    """
	execution_log_results example:
	[
		{
			"arn": "arn:aws:lambda:us-west-2:532121572788:function:Untitled_Code_Block_RFNItzJNn2",
			"count": "1",
			"dt": "2019-07-15-13-35",
			"execution_pipeline_id": "46b0fdd3-266d-4c6f-af7c-79198a112e96",
			"function_name": "Untitled_Code_Block_RFNItzJNn2",
			"log_id": "22e4625e-46d1-401a-b935-bcde17f8b667",
			"project_id": "08757409-4bc8-4a29-ade7-371b1a46f99e",
			"timestamp": 1563197795,
			"type": "SUCCESS"
		}
		{
			"arn": "arn:aws:lambda:us-west-2:532121572788:function:Untitled_Code_Block_RFNItzJNn3",
			"count": "1",
			"dt": "2019-07-15-13-35",
			"execution_pipeline_id": "46b0fdd3-266d-4c6f-af7c-79198a112e96",
			"function_name": "Untitled_Code_Block_RFNItzJNn3",
			"log_id": "40b02027-c856-4d2b-bd63-c62f300944e5",
			"project_id": "08757409-4bc8-4a29-ade7-371b1a46f99e",
			"timestamp": 1563197795,
			"type": "SUCCESS"
		}
	]
	"""
    # Array of all of the metadata for each execution
    execution_log_results = []

    start_time = time.time()

    # Before we do the next step we can save ourselves a lot of time
    # by pulling all of the cached shard data from the database.
    # All of the remaining shards we can go and scan out of S3.
    cached_execution_shards = dbsession.query(CachedExecutionLogsShard).filter(
        CachedExecutionLogsShard.project_id == project_id
    ).filter(
        CachedExecutionLogsShard.date_shard.in_(
            all_s3_shards
        )
    ).all()

    logit("--- Pulling shards from database: %s seconds ---" % (time.time() - start_time), "debug")

    # Take the list of cached_execution_shards and remove all of the
    # cached results contained in it from the list of shards we need to
    # go scan S3 for.
    cached_execution_log_results = []

    logit(
        "Number of cached shards in the DB we can skip S3 scanning for: " + str(len(cached_execution_shards)),
        "debug"
    )

    """
    for cached_execution_shard in cached_execution_shards:
        cached_execution_shard_dict = cached_execution_shard.to_dict()

        # Add the cached shard data to the cached executions
        cached_execution_log_results = cached_execution_log_results + cached_execution_shard_dict["shard_data"]

        # Remove this from the shards to go scan since we already have it
        if cached_execution_shard_dict["date_shard"] in all_s3_shards:
            all_s3_shards.remove(cached_execution_shard_dict["date_shard"])
    """

    logit("Number of un-cached shards in S3 we have to scan: " + str(len(all_s3_shards)), "debug")

    for s3_shard in all_s3_shards:
        full_shard = project_id + "/" + s3_shard

        start_time = time.time()
        execution_logs = yield task_spawner.get_s3_pipeline_execution_logs(
            credentials,
            full_shard,
            -1
        )
        logit("--- Pulling keys from S3: %s seconds ---" % (time.time() - start_time), "debug")

        start_time = time.time()
        for execution_log in execution_logs:
            execution_log_results.append(
                get_execution_metadata_from_s3_key(
                    credentials["region"],
                    credentials["account_id"],
                    execution_log
                )
            )
        logit("--- Parsing S3 keys: %s seconds ---" % (time.time() - start_time), "debug")

    # We now got over all the execution log results to see what can be cached. The way
    # we do this is we go over each execution log result and we check if the "dt" shard
    # is less than or equal to the time specified in the assured_cachable_dt. If it is,
    # we than add it to our cachable_dict (format below) and at the end we store all of
    # the results in the database so that we never have to pull those shards again.
    """
	{
		"{{CACHEABLE_DT_SHARD}}": [
			{
				"arn": "arn:aws:lambda:us-west-2:532121572788:function:Untitled_Code_Block_RFNItzJNn2",
				"count": "1",
				"dt": "2019-07-15-13-35",
				"execution_pipeline_id": "46b0fdd3-266d-4c6f-af7c-79198a112e96",
				"function_name": "Untitled_Code_Block_RFNItzJNn2",
				"log_id": "22e4625e-46d1-401a-b935-bcde17f8b667",
				"project_id": "08757409-4bc8-4a29-ade7-371b1a46f99e",
				"timestamp": 1563197795,
				"type": "SUCCESS"
			}
			{
				"arn": "arn:aws:lambda:us-west-2:532121572788:function:Untitled_Code_Block_RFNItzJNn3",
				"count": "1",
				"dt": "2019-07-15-13-35",
				"execution_pipeline_id": "46b0fdd3-266d-4c6f-af7c-79198a112e96",
				"function_name": "Untitled_Code_Block_RFNItzJNn3",
				"log_id": "40b02027-c856-4d2b-bd63-c62f300944e5",
				"project_id": "08757409-4bc8-4a29-ade7-371b1a46f99e",
				"timestamp": 1563197795,
				"type": "SUCCESS"
			}
		]
		"2019-07-15-13-35": "",
	}
	"""
    cachable_dict = {}

    for execution_log_result in execution_log_results:
        # Check if dt share is within the cachable range
        current_execution_log_result_dt = execution_log_result["dt"]
        shard_as_dt = datetime.datetime.strptime(
            current_execution_log_result_dt,
            "%Y-%m-%d-%H-%M"
        )

        if shard_as_dt <= assured_cachable_dt:
            if not (current_execution_log_result_dt in cachable_dict):
                cachable_dict[current_execution_log_result_dt] = []

            cachable_dict[current_execution_log_result_dt].append(
                execution_log_result
            )

    # Now we add in the cached shard data
    execution_log_results = execution_log_results + cached_execution_log_results

    start_time = time.time()
    execution_pipeline_dict = execution_log_query_results_to_pipeline_id_dict(
        execution_log_results
    )
    logit("--- Converting to execution_pipeline_dict: %s seconds ---" % (time.time() - start_time), "debug")

    start_time = time.time()
    frontend_format = execution_pipeline_id_dict_to_frontend_format(
        execution_pipeline_dict
    )
    logit("--- Converting to front-end-format: %s seconds ---" % (time.time() - start_time), "debug")

    start_time = time.time()
    # We now store all cachable shard data in the database so we don't have
    # to rescan those shards in S3.
    for date_shard_key, cachable_execution_list in cachable_dict.items():
        new_execution_log_shard = CachedExecutionLogsShard()
        new_execution_log_shard.date_shard = "dt=" + date_shard_key
        new_execution_log_shard.shard_data = cachable_execution_list
        new_execution_log_shard.project_id = project_id
        dbsession.add(new_execution_log_shard)

    # Write the cache data to the database
    dbsession.commit()
    dbsession.close()
    logit("--- Caching results in database: %s seconds ---" % (time.time() - start_time), "debug")

    raise gen.Return(frontend_format)


def get_execution_metadata_from_s3_key(aws_region, account_id, input_s3_key):
    # 08757409-4bc8-4a29-ade7-371b1a46f99e/dt=2019-07-15-18-00/e4e3571e-ab59-4790-8072-3049805301c3/SUCCESS~Untitled_Code_Block_RFNItzJNn2~3233e08a-baf0-4f8f-a4c2-ee2d3153f75b~1563213635
    s3_key_parts = input_s3_key.split(
        "/"
    )

    log_file_name = s3_key_parts[-1]
    log_file_name_parts = log_file_name.split("~")

    return_data = {
        "arn": "arn:aws:lambda:" + aws_region + ":" + account_id + ":function:" + log_file_name_parts[1],
        "project_id": s3_key_parts[0],
        "dt": s3_key_parts[1].replace("dt=", ""),
        "execution_pipeline_id": s3_key_parts[2],
        "type": log_file_name_parts[0],
        "function_name": log_file_name_parts[1],
        "log_id": log_file_name_parts[2],
        "timestamp": int(log_file_name_parts[3]),
        "count": "1"
    }

    return return_data
