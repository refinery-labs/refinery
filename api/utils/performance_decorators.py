import time

import uuid
from datetime import datetime
import os

epoch = datetime.utcfromtimestamp(0)


def unix_time_millis(dt):
    return (dt - epoch).total_seconds() * 1000.0


def is_debug_environment():
    if "debug" in os.environ:
        return str(os.environ.get("debug")).lower() == "true"

    if "is_debug" in os.environ:
        return str(os.environ.get("is_debug")).lower() == "true"

    return False


def emit_runtime_metrics(metric_name):
    """
    Decorator that emits metrics to Cloudwatch about an invocation.
    Designed to provide an easier debugging experience for production issues, as well as to create alerts.
    :param metric_name: Name of the metric that will be emitted.
    :type metric_name: basestring
    :return: Decorated function
    """
    debug = is_debug_environment()

    env_name = "Development"

    if not debug:
        env_name = "Production"

    def decorator(func):
        def wrapper(*args, **kwargs):
            self = args[0]

            logger = self.logger

            cloudwatch_client = self.aws_cloudwatch_client

            # Unique ID of the task being invoked to aid debugging
            task_uuid = str(uuid.uuid4())

            start = datetime.utcnow()
            start_ms = time.time() * 1000.0

            logger("[Begin Task] [ID " + task_uuid + "]: " + metric_name + " @ " + str(start_ms / 1000))

            # Call the wrapped function
            result = func(*args, **kwargs)

            end_ms = time.time() * 1000.0

            elapsed_ms = end_ms - start_ms

            # Best effort to log the metric to Cloudwatch
            try:
                cloudwatch_client.put_metric_data(
                    Namespace="Refinery-Performance-Metrics__" + env_name,
                    MetricData=[
                        {
                            "MetricName": "task_invocation",
                            "Dimensions": [
                                {
                                    "Name": "Task Name",
                                    "Value": metric_name
                                }
                            ],
                            # Time that this was created at
                            "Timestamp": start,
                            # Time that it took for the request to process
                            "Value": elapsed_ms,
                            "Unit": "Milliseconds"
                        }
                    ]
                )
            except Exception as e:
                # Gotta catch em' all!
                logger("Unable to emit metric " + metric_name + ": " + repr(e), "warning")

            logger(
                "[End Task]   [ID " + task_uuid + "]: " + metric_name + " @ " + str(end_ms / 1000) + " -- " + str(elapsed_ms) + "ms"
            )

            return result

        return wrapper

    return decorator
