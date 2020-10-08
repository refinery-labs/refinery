import random
import time
from functools import wraps

from botocore.exceptions import ClientError

NOT_FOUND_EXCEPTION = "NotFoundException"
RESOURCE_IN_USE_EXCEPTION = "ResourceInUseException"
RESOURCE_NOT_FOUND_EXCEPTION = "ResourceNotFoundException"
TOO_MANY_REQUESTS_EXCEPTION = "TooManyRequestsException"


class ExponentialBackoffException(Exception):
    pass


def aws_exponential_backoff(allowed_errors=None, breaking_errors=None, max_attempts=5):
    if breaking_errors is None:
        breaking_errors = []
    if allowed_errors is None:
        allowed_errors = []
    allowed_client_errors = allowed_errors + [TOO_MANY_REQUESTS_EXCEPTION]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0

            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except ClientError as e:
                    error_code = e.response["Error"]["Code"]
                    if error_code in breaking_errors:
                        return None

                    if error_code not in allowed_client_errors:
                        raise

                    attempts += 1
                    time.sleep(attempts * 2 + random.randint(0, 5))
            raise ExponentialBackoffException()
        return wrapper

    return decorator

