import tornado

from tornado.concurrent import run_on_executor, futures

from assistants.aws_clients.aws_clients_assistant import get_aws_client

from botocore.exceptions import ClientError

class SNSManager(object):
	def __init__(self, loop=None):
		self.executor = futures.ThreadPoolExecutor( 10 )
		self.loop = loop or tornado.ioloop.IOLoop.current()

	@run_on_executor
	def delete_sns_topic( self, credentials, id, type, name, arn ):
		return self._delete_sns_topic( credentials, id, type, name, arn )
		
	@staticmethod
	def _delete_sns_topic( credentials, id, type, name, arn ):
		sns_client = get_aws_client(
			"sns",
			credentials,
		)
		
		was_deleted = False
		
		try:
			response = sns_client.delete_topic(
				TopicArn=arn,
			)
			was_deleted = True
		except ClientError as e:
			if e.response[ "Error" ][ "Code" ] != "ResourceNotFoundException":
				raise
		
		return {
			"id": id,
			"type": type,
			"name": name,
			"arn": arn,
			"deleted": was_deleted,
		}
