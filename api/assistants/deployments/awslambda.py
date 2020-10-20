import pinject
import tornado

from tornado.concurrent import run_on_executor, futures

from tasks.aws_lambda import list_lambda_event_source_mappings_by_name
from utils.general import log_exception, logit
from utils.performance_decorators import emit_runtime_metrics

from assistants.decorators import aws_exponential_backoff, RESOURCE_IN_USE_EXCEPTION, RESOURCE_NOT_FOUND_EXCEPTION
from utils.wrapped_aws_functions import lambda_delete_event_source_mapping, lambda_delete_function


class LambdaManager(object):
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
    @emit_runtime_metrics("lambda_manager__delete_lambda")
    def delete_lambda(self, credentials, id, type, name, arn):
        return self._delete_lambda(self.aws_client_factory, credentials, id, type, name, arn)

    @staticmethod
    def _delete_lambda(aws_client_factory, credentials, id, type, name, arn):
        lambda_client = aws_client_factory.get_aws_client(
            "lambda",
            credentials
        )

        # Cleanup the source mappings for when we recreate this lambda and they do not persist
        event_source_mappings = []
        if name is not None:
            event_source_mappings = list_lambda_event_source_mappings_by_name(aws_client_factory, credentials, name)

        for mapping in event_source_mappings:
            lambda_delete_event_source_mapping(lambda_client, mapping)

        lambda_delete_function(lambda_client, arn)

        return {
            "id": id,
            "type": type,
            "name": name,
            "arn": arn,
            "deleted": True,
        }
