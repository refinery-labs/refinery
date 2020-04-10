import uuid

from jsonschema import validate as validate_schema
from tornado import gen

from controller import BaseHandler
from controller.decorators import authenticated, disable_on_overdue_payment
from controller.logs.actions import chunk_list, write_remaining_project_execution_log_pages, \
	get_execution_stats_since_timestamp, do_update_athena_table_partitions
from controller.logs.schemas import *


class GetProjectExecutionLogObjects( BaseHandler ):
	@authenticated
	@disable_on_overdue_payment
	@gen.coroutine
	def post( self ):
		"""
		Return contents of provided list of S3 object paths.
		"""
		validate_schema( self.json, GET_PROJECT_EXECUTION_LOG_OBJECT_SCHEMAS )

		self.logger( "Retrieving requested log files..." )

		credentials = self.get_authenticated_user_cloud_configuration()

		results_list = []

		for log_to_fetch in self.json[ "logs_to_fetch" ]:
			s3_key = log_to_fetch[ "s3_key" ]
			log_id = log_to_fetch[ "log_id" ]

			log_data = yield self.task_spawner.get_json_from_s3(
				credentials,
				credentials[ "logs_bucket" ],
				s3_key
			)

			results_list.append({
				"log_data": log_data,
				"log_id": log_id
			})

		self.write({
			"success": True,
			"result": {
				"results": results_list
			}
		})


class GetProjectExecutionLogs( BaseHandler ):
	@authenticated
	@disable_on_overdue_payment
	@gen.coroutine
	def post( self ):
		"""
		Get log data for a list of log paths.
		"""
		validate_schema( self.json, GET_PROJECT_EXECUTION_LOGS_SCHEMA )

		self.logger( "Retrieving requested logs..." )

		credentials = self.get_authenticated_user_cloud_configuration()

		results = yield self.task_spawner.get_block_executions(
			credentials,
			self.json[ "project_id" ],
			self.json[ "execution_pipeline_id" ],
			self.json[ "arn" ],
			self.json[ "oldest_timestamp" ]
		)

		# Split out shards
		chunked_results = chunk_list(
			results,
			50
		)

		# The final return format
		final_return_data = {
			"results": [],
			"pages": []
		}

		# Take the first 50 results and stuff it into "results"
		if len( chunked_results ) > 0:
			# Pop first list of list of lists
			final_return_data[ "results" ] = chunked_results.pop(0)

		# We batch up the work to do but we don't yield on it until
		# after we write the response. This allows for fast response times
		# and by the time they actually request a later page we've already
		# written it.
		data_to_write_list = []

		# Turn the rest into S3 chunks which can be loaded later
		# by the frontend on demand.
		for chunked_result in chunked_results:
			result_uuid = str( uuid.uuid4() )
			s3_path = "log_pagination_result_pages/" + result_uuid + ".json"
			data_to_write_list.append({
				"s3_path": s3_path,
				"chunked_data": chunked_result
			})

			# We just add the UUID to the response as if we've
			# already written it
			final_return_data[ "pages" ].append(
				result_uuid
			)

		# Clear that memory ASAP
		del chunked_results

		self.write({
			"success": True,
			"result": final_return_data
		})

		# Write the remaining results
		yield write_remaining_project_execution_log_pages(
			self.task_spawner,
			credentials,
			data_to_write_list
		)


class GetProjectExecutionLogsPage( BaseHandler ):
	@authenticated
	@disable_on_overdue_payment
	@gen.coroutine
	def post( self ):
		"""
		Get a page of results which was previously written in a
		chunk to S3 as JSON. This is to allow lazy-loading of results
		for logs of a given Code Block in an execution ID.
		"""
		validate_schema( self.json, GET_PROJECT_EXECUTION_LOGS_PAGE_SCHEMA )

		self.logger( "Retrieving results page of log results from S3..." )

		credentials = self.get_authenticated_user_cloud_configuration()

		success = False
		results = []

		# Try grabbing the logs twice because the front-end is being
		# all sensitive again :)
		for i in range( 0, 2 ):
			try:
				results = yield self.task_spawner.get_json_from_s3(
					credentials,
					credentials[ "logs_bucket" ],
					"log_pagination_result_pages/" + self.json[ "id" ] + ".json"
				)
				success = True
				break
			except Exception as e:
				self.logger( "Error occurred while reading results page from S3, potentially it's expired?" )
				self.logger( e )
				results = []

			self.logger( "Retrying again just in case it's not propogated yet..." )

		self.write({
			"success": success,
			"result": {
				"results": results
			}
		})


class GetProjectExecutions( BaseHandler ):
	@authenticated
	@disable_on_overdue_payment
	@gen.coroutine
	def post( self ):
		"""
		Get past execution ID(s) for a given deployed project
		and their respective metadata.
		"""
		validate_schema( self.json, GET_PROJECT_EXECUTIONS_SCHEMA )

		project_id = self.json[ "project_id" ]

		credentials = self.get_authenticated_user_cloud_configuration()

		# We do this to always keep Athena partitioned for the later
		# steps of querying
		do_update_athena_table_partitions(
			self.task_spawner,
			self.db_session_maker,
			self.task_locker,
			credentials,
			project_id
		)

		# Ensure user is owner of the project
		if not self.is_owner_of_project( self.json[ "project_id" ] ):
			self.write({
				"success": False,
				"code": "ACCESS_DENIED",
				"msg": "You do not have priveleges to access that project's executions!",
			})
			raise gen.Return()

		self.logger( "Pulling the relevant logs for the project ID specified...", "debug" )

		# Pull the logs
		execution_pipeline_totals = yield get_execution_stats_since_timestamp(
			self.db_session_maker,
			self.task_spawner,
			credentials,
			project_id,
			self.json[ "oldest_timestamp" ]
		)

		self.write({
			"success": True,
			"result": execution_pipeline_totals
		})

