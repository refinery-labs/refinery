import tornado

from tornado.concurrent import run_on_executor, futures
from utils.aws_client import get_aws_client
from utils.general import logit
from tornado import gen

from botocore.exceptions import ClientError

class LambdaManager(object):
	def __init__(self, loop=None):
		self.executor = futures.ThreadPoolExecutor( 10 )
		self.loop = loop or tornado.ioloop.IOLoop.current()

	@run_on_executor
	def delete_lambda( self, credentials, id, type, name, arn ):
		return self._delete_lambda( credentials, id, type, name, arn )
		
	@staticmethod
	def _delete_lambda( credentials, id, type, name, arn ):
		lambda_client = get_aws_client(
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
