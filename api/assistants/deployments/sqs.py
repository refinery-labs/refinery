import pinject
import tornado

from tornado.concurrent import run_on_executor, futures

from botocore.exceptions import ClientError

from utils.general import log_exception
from utils.performance_decorators import emit_runtime_metrics


def get_sqs_arn_from_url( input_queue_url ):
	stripped_queue_url = input_queue_url.replace(
		"https://",
		""
	)
	queue_dot_parts = stripped_queue_url.split( "." )
	region = queue_dot_parts[0]
	queue_slash_parts = stripped_queue_url.split( "/" )
	account_id = queue_slash_parts[1]
	queue_name = queue_slash_parts[2]

	return "arn:aws:sqs:" + region + ":" + account_id + ":" + queue_name


class SqsManager( object ):
	aws_client_factory = None
	aws_cloudwatch_client = None
	logger = None

	@pinject.copy_args_to_public_fields
	def __init__(self, aws_client_factory, aws_cloudwatch_client, logger, loop=None):
		self.executor = futures.ThreadPoolExecutor( 10 )
		self.loop = loop or tornado.ioloop.IOLoop.current()

	@run_on_executor
	@log_exception
	@emit_runtime_metrics( "sqs_manager__delete_sqs_queue" )
	def delete_sqs_queue( self, credentials, _id, _type, name, arn ):
		return self._delete_sqs_queue(
			self.aws_client_factory,
			credentials,
			_id,
			_type,
			name,
			arn
		)
		
	@staticmethod
	def _delete_sqs_queue( aws_client_factory, credentials, _id, _type, name, arn ):
		sqs_client = aws_client_factory.get_aws_client(
			"sqs",
			credentials,
		)
		
		was_deleted = False

		queue_parts = arn.split( ":" )
		queue_name = queue_parts[-1]
		
		try:
			queue_url_response = sqs_client.get_queue_url(
				QueueName=queue_name,
			)
			
			response = sqs_client.delete_queue(
				QueueUrl=queue_url_response[ "QueueUrl" ],
			)
		except ClientError as e:
			acceptable_errors = [
				"ResourceNotFoundException",
				"AWS.SimpleQueueService.NonExistentQueue"
			]
			
			if not ( e.response[ "Error" ][ "Code" ] in acceptable_errors ):
				raise
		
		return {
			"id": _id,
			"type": _type,
			"name": name,
			"arn": arn,
			"deleted": was_deleted,
		}
