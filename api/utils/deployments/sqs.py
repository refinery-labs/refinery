import tornado

from tornado.concurrent import run_on_executor, futures
from utils.aws_client import get_aws_client
from utils.general import logit
from tornado import gen

from botocore.exceptions import ClientError

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

class SQSManager(object):
	def __init__(self, loop=None):
		self.executor = futures.ThreadPoolExecutor( 10 )
		self.loop = loop or tornado.ioloop.IOLoop.current()

	@run_on_executor
	def delete_sqs_queue( self, credentials, id, type, name, arn ):
		return self._delete_sqs_queue(
			credentials,
			id,
			type,
			name,
			arn
		)
		
	@staticmethod
	def _delete_sqs_queue( credentials, id, type, name, arn ):
		sqs_client = get_aws_client(
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
			"id": id,
			"type": type,
			"name": name,
			"arn": arn,
			"deleted": was_deleted,
		}
