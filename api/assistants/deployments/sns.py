import tornado

from tornado.concurrent import run_on_executor, futures

from botocore.exceptions import ClientError


class SnsManager( object ):
	aws_client_factory = None

	def __init__(self, aws_client_factory, loop=None):
		self.executor = futures.ThreadPoolExecutor( 10 )
		self.loop = loop or tornado.ioloop.IOLoop.current()

	@run_on_executor
	def delete_sns_topic( self, credentials, id, type, name, arn ):
		return self._delete_sns_topic( self.aws_client_factory, credentials, id, type, name, arn )
		
	@staticmethod
	def _delete_sns_topic( aws_client_factory, credentials, id, type, name, arn ):
		sns_client = aws_client_factory.get_aws_client(
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
