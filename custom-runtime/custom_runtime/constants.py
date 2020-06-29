
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

import boto3
import os
import urllib3
from .memory import RefineryMemory


# For requests to AWS custom runtime API
http = urllib3.PoolManager()


_VERSION = "1.0.0"


# Make global to enable caching of redis connection
gmemory = RefineryMemory(
    os.environ["REDIS_HOSTNAME"],
    os.environ["REDIS_PASSWORD"],
    os.environ["REDIS_PORT"],
)


S3_CLIENT = boto3.client(
    "s3"
)
