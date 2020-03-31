import pinject
import tornado

from tornado.concurrent import run_on_executor, futures

from botocore.exceptions import ClientError

class LambdaManager(object):
	aws_client_factory = None

	@pinject.copy_args_to_public_fields
	def __init__(self, aws_client_factory, loop=None):
		self.executor = futures.ThreadPoolExecutor( 10 )
		self.loop = loop or tornado.ioloop.IOLoop.current()

	@run_on_executor
	def delete_lambda( self, credentials, id, type, name, arn ):
		return self._delete_lambda( self.aws_client_factory, credentials, id, type, name, arn )
		
	@staticmethod
	def _delete_lambda( aws_client_factory, credentials, id, type, name, arn ):
		lambda_client = aws_client_factory.get_aws_client(
			"lambda",
			credentials
		)
		
		was_deleted = False
		try:
			response = lambda_client.delete_function(
				FunctionName=arn,
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
