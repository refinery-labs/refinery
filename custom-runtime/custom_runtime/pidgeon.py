
"""
Copyright (C) Refinery Labs Inc. - All Rights Reserved

NOTICE: All information contained herein is, and remains
the property of Refinery Labs Inc. and its suppliers,
if any. The intellectual and technical concepts contained
herein are proprietary to Refinery Labs Inc.
and its suppliers and may be covered by U.S. and Foreign Patents,
patents in process, and are protected by trade secret or copyright law.
Dissemination of this information or reproduction of this material
is strictly forbidden unless prior written permission is obtained
from Refinery Labs Inc.
"""

import json
import uuid
from .exc import AlreadyInvokedException, InvokeQueueEmptyException


_QUEUE_METADATA_EXPIRATION = (60 * 60 * 24)


class RefineryMemory:
    # https://docs.aws.amazon.com/lambda/latest/dg/concurrent-executions.html#throttling-behavior
    return_data_timeout = (60 * 60 * 6)

    json_types = [
        list,
        dict
    ]

    regular_types = [
        str,
        int,
        float,
        complex,
        bool,
    ]

    def __init__(self):
        pass

    def _get_input_data_from_redis(self, key, **kwargs):
        pass

    def _get_queue_input_from_redis(self, queue_insert_id, pop_number):
        pass

    def _get_queue_url(self, queue_insert_id):
        pass

    def _get_queue_backpack(self, queue_insert_id):
        pass

    def _set_queue_data(self, queue_url, queue_items, backpack):
        pass

    def _set_fan_in_data(self, fan_out_id, invocation_list, **kwargs):
        pass

    def _get_invocation_input_from_queue(self, invocation_id):
        pass

    def _fan_in_get_results_data(self, fan_out_id, **kwargs):
        pass

    def _fan_in_operations(self, fan_out_id, return_data, backpack, **kwargs):
        pass

    def _bulk_store_input_data(self, lambda_invocation_list):
        pass

    def _merge_store_result(self, execution_id, branch_ids, target_lambda_arn, current_lambda_arn, merge_lambda_arns, backpack, return_data):
        pass
