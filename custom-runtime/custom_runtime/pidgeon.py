
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


import uuid
from httplib import HTTPSConnection, HTTPConnection
from json import loads, dumps
from urlparse import urlparse, urljoin
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

    def __init__(self, pidgeon_url, pidgeon_auth):
        self.pidgeon_url = pidgeon_url
        self.pidgeon_auth = pidgeon_auth

    def _call_pidgeon_block(self, path, **kwargs):
        kwargs.update({"auth": self.pidgeon_auth})
        data = dumps(kwargs)
        parts = urlparse(self.pidgeon_url)
        is_https = self.pidgeon_url.startswith("https")
        host = parts.netloc
        port = 443 if is_https else 80
        cls = HTTPSConnection if is_https else HTTPConnection
        path = urljoin(parts.path, path)

        if ":" in parts.netloc:
            host, port = parts.netloc.split(':')

        conn = cls(host, port)
        conn.request("POST", path, data)

        resp = conn.getresponse()

        return loads(resp.read())

    def _get_input_data_from_redis(self, key, **kwargs):
        return self._call_pidgeon_block(
            "/block/state/get",
            key=key
        )

    def _get_queue_input_from_redis(self, queue_insert_id, pop_number):
        pass

    def _get_queue_url(self, queue_insert_id):
        return self._call_pidgeon_block(
            "/block/state/get",
            key="SQS_TARGET_QUEUE_URL_" + queue_insert_id
        )


    def _get_queue_backpack(self, queue_insert_id):
        return self._call_pidgeon_block(
            "/block/state/get",
            key="SQS_BACKPACK_DATA_" + queue_insert_id
        )

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
