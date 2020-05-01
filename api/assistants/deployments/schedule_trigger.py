import pinject
import tornado

from tornado.concurrent import run_on_executor, futures

from botocore.exceptions import ClientError

from utils.general import log_exception
from utils.performance_decorators import emit_runtime_metrics


class ScheduleTriggerManager(object):
    aws_client_factory = None
    aws_cloudwatch_client = None
    logger = None

    # noinspection PyUnresolvedReferences
    @pinject.copy_args_to_public_fields
    def __init__(self, aws_client_factory, aws_cloudwatch_client, logger, loop=None):
        self.executor = futures.ThreadPoolExecutor(10)
        self.loop = loop or tornado.ioloop.IOLoop.current()

    @run_on_executor
    @log_exception
    @emit_runtime_metrics("schedule_trigger_manager__delete_schedule_trigger")
    def delete_schedule_trigger(self, credentials, id, type, name, arn):
        return self._delete_schedule_trigger(self.aws_client_factory, credentials, id, type, name, arn)

    @staticmethod
    def _delete_schedule_trigger(aws_client_factory, credentials, id, type, name, arn):
        events_client = aws_client_factory.get_aws_client(
            "events",
            credentials
        )

        arn_parts = arn.split("/")
        name = arn_parts[-1]

        was_deleted = False
        try:
            list_rule_targets_response = events_client.list_targets_by_rule(
                Rule=name,
            )

            target_ids = []

            for target_item in list_rule_targets_response["Targets"]:
                target_ids.append(
                    target_item["Id"]
                )

            # If there are some targets, delete them, else skip this.
            if len(target_ids) > 0:
                remove_targets_response = events_client.remove_targets(
                    Rule=name,
                    Ids=target_ids
                )

            response = events_client.delete_rule(
                Name=name,
            )

            was_deleted = True
        except ClientError as e:
            if e.response["Error"]["Code"] != "ResourceNotFoundException":
                raise

        return {
            "id": id,
            "type": type,
            "name": name,
            "arn": arn,
            "deleted": was_deleted,
        }
