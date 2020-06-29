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
