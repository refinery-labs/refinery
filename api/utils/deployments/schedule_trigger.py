import tornado

from tornado.concurrent import run_on_executor, futures
from utils.aws_client import get_aws_client
from utils.general import logit
from tornado import gen

from botocore.exceptions import ClientError

class ScheduleTriggerManager(object):
	def __init__(self, loop=None):
		self.executor = futures.ThreadPoolExecutor( 10 )
		self.loop = loop or tornado.ioloop.IOLoop.current()

	@run_on_executor
	def delete_schedule_trigger( self, credentials, id, type, name, arn ):
		return self._delete_schedule_trigger( credentials, id, type, name, arn )
		
	@staticmethod
	def _delete_schedule_trigger( credentials, id, type, name, arn ):
		events_client = get_aws_client(
			"events",
			credentials
		)

		arn_parts = arn.split( "/" )
		name = arn_parts[-1]
		
		was_deleted = False
		try:
			list_rule_targets_response = events_client.list_targets_by_rule(
				Rule=name,
			)
			
			target_ids = []
			
			for target_item in list_rule_targets_response[ "Targets" ]:
				target_ids.append(
					target_item[ "Id" ]
				)

			# If there are some targets, delete them, else skip this.
			if len( target_ids ) > 0:
				remove_targets_response = events_client.remove_targets(
					Rule=name,
					Ids=target_ids
				)
			
			response = events_client.delete_rule(
				Name=name,
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

schedule_trigger_manager = ScheduleTriggerManager()