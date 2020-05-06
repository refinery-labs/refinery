def execution_pipeline_id_dict_to_frontend_format(execution_pipeline_id_dict):

    final_return_format = []

    # Now convert it into the usable front-end format
    for execution_pipeline_id, aggregate_data in execution_pipeline_id_dict.items():
        block_executions = []

        for block_arn, execution_status_counts in aggregate_data["block_executions"].items():
            block_executions.append({
                "arn": block_arn,
                "SUCCESS": execution_status_counts["SUCCESS"],
                "CAUGHT_EXCEPTION": execution_status_counts["CAUGHT_EXCEPTION"],
                "EXCEPTION": execution_status_counts["EXCEPTION"],
            })

        final_return_format.append({
            "execution_pipeline_id": execution_pipeline_id,
            "block_executions": block_executions,
            "execution_pipeline_totals": {
                "SUCCESS": aggregate_data["SUCCESS"],
                "CAUGHT_EXCEPTION": aggregate_data["CAUGHT_EXCEPTION"],
                "EXCEPTION": aggregate_data["EXCEPTION"],
            },
            "timestamp": aggregate_data["timestamp"]
        })

    return final_return_format


def execution_log_query_results_to_pipeline_id_dict(query_results):
    """
    This is the final format we return from the input query
    results (the list returned from Athena):

    {
            "{{execution_pipeline_id}}": {
                    "SUCCESS": 0,
                    "EXCEPTION": 2,
                    "CAUGHT_EXCEPTION": 10,
                    "block_executions": {
                            "{{arn}}": {
                                    "SUCCESS": 0,
                                    "EXCEPTION": 2,
                                    "CAUGHT_EXCEPTION": 10,
                            }
                    }
            }
    }
    """
    execution_pipeline_id_dict = {}

    for query_result in query_results:
        # If this is the first execution ID we've encountered then set that key
        # up with the default object structure
        if not (query_result["execution_pipeline_id"] in execution_pipeline_id_dict):
            execution_pipeline_id_dict[query_result["execution_pipeline_id"]] = {
                "SUCCESS": 0,
                "EXCEPTION": 0,
                "CAUGHT_EXCEPTION": 0,
                "timestamp": int(query_result["timestamp"]),
                "block_executions": {}
            }

        # If the timestamp is more recent that what is in the
        # execution pipeline data then update the field with the value
        # This is because we'd sort that by time (most recent) on the front end
        execution_pipeline_timestamp = execution_pipeline_id_dict[
            query_result["execution_pipeline_id"]]["timestamp"]
        if int(query_result["timestamp"]) > execution_pipeline_timestamp:
            execution_pipeline_timestamp = int(query_result["timestamp"])

        # If this is the first ARN we've seen for this execution ID we'll set it up
        # with the default object template as well.
        block_executions = execution_pipeline_id_dict[
            query_result["execution_pipeline_id"]]["block_executions"]
        if not (query_result["arn"] in block_executions):
            block_executions[query_result["arn"]] = {
                "SUCCESS": 0,
                "EXCEPTION": 0,
                "CAUGHT_EXCEPTION": 0
            }

        # Convert execution count to integer
        execution_int_count = int(query_result["count"])

        # Add execution count to execution ID totals
        execution_pipeline_id_dict[query_result["execution_pipeline_id"]
                                   ][query_result["type"]] += execution_int_count

        # Add execution count to ARN execution totals
        block_executions[query_result["arn"]
                         ][query_result["type"]] += execution_int_count

    return execution_pipeline_id_dict
