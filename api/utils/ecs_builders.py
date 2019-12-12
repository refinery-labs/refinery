import traceback
import functools
import tornado
import boto3
import copy
import time
import json
import re

from tornado.concurrent import run_on_executor, futures
from utils.aws_client import get_aws_client, STS_CLIENT
from botocore.exceptions import ClientError
from utils.general import logit
from tornado import gen

CLUSTER_NAME = "refinery_builders"
TASK_DEFINITION = "refinery_builders_task_family"
AGENT_SECRET = "CHANGEMEBEFOREDEPLOYINGTOPROD"

class AWSECSManager(object):
	def __init__(self, loop=None):
		self.executor = futures.ThreadPoolExecutor( 10 )
		self.loop = loop or tornado.ioloop.IOLoop.current()

	@staticmethod
	def _get_security_group_id_by_group_name( credentials, security_group_name ):
		ec2_client = get_aws_client(
			"ec2",
			credentials
		)

		response = ec2_client.describe_security_groups(
			GroupNames=[
				security_group_name,
			]
		)

		security_group_ids = []

		if not "SecurityGroups" in response:
			return None

		for security_group_metadata in response[ "SecurityGroups" ]:
			return security_group_metadata[ "GroupId" ]

		return None

	@staticmethod
	def _get_all_subnets( credentials ):
		ec2_client = get_aws_client(
			"ec2",
			credentials
		)

		response = ec2_client.describe_subnets(
			MaxResults=1000
		)

		subnet_ids = []

		if not "Subnets" in response:
			return subnet_ids

		for subnet_metadata in response[ "Subnets" ]:
			subnet_ids.append(
				subnet_metadata[ "SubnetId" ]
			)

		return subnet_ids

	def enable_long_form_arns():
		"""
		This code will be irrelevant as of 2019-12-31 23:59:59 -0800

		However, before then we'll need to have this to enabled long-form
		ARNs for tasks and services since AWS is going through a migration.
		"""
		ecs_client = boto3.client('ecs')

		print( "Enabling long form ARN format for tasks..." )
		response = ecs_client.put_account_setting_default(
			name="taskLongArnFormat",
			value="enabled"
		)

	@staticmethod
	def _start_builder_ecs_task( credentials ):
		ecs_client = get_aws_client(
			"ecs",
			credentials
		)

		subnet_ids = AWSECSManager._get_all_subnets( credentials )
		security_group_id = AWSECSManager._get_security_group_id_by_group_name(
			credentials,
			"refinery_builders_security_group"
		)

		if len(subnet_ids) == 0:
			raise Exception( "No subnets exist! Connect start a task without a subnet!" )

		try:
			response = ecs_client.run_task(
				taskDefinition=TASK_DEFINITION,
				cluster=CLUSTER_NAME,
				count=1,
				enableECSManagedTags=True,
				launchType="FARGATE",
				networkConfiguration={
					"awsvpcConfiguration": {
						"subnets": subnet_ids,
						"securityGroups": [
							security_group_id,
						],
						"assignPublicIp": "ENABLED"
					}
				},
				tags=[
					{
						"key": "RefineryResource",
						"value": "true"
					},
				],
				overrides={
					"containerOverrides": [
						{
							"name": "refinery-builders",
							"environment": [
								{
									"name": "AGENT_SECRET",
									"value": AGENT_SECRET
								}
							]
						}
					]
				}
			)
		except ClientError as e:
			error_message = e.response[ "Error" ][ "Message" ]

			if error_message == "Long arn format must be enabled for ECS managed tags.":
				enable_long_form_arns()
				return AWSECSManager._start_builder_ecs_task( credentials )

			# If it's not the expected error then re-raise
			raise

		"""
		Pull out and return relevant ECS task details
		"""
		return response[ "tasks" ][0][ "taskArn" ]

	@staticmethod
	def _get_running_task_arns( credentials ):
		ecs_client = get_aws_client(
			"ecs",
			credentials
		)

		running_response = ecs_client.list_tasks(
		    cluster=CLUSTER_NAME,
		    maxResults=100,
		    desiredStatus="RUNNING",
		    launchType="FARGATE"
		)

		pending_response = ecs_client.list_tasks(
		    cluster=CLUSTER_NAME,
		    maxResults=100,
		    desiredStatus="PENDING",
		    launchType="FARGATE"
		)

		task_arns = []

		if not "taskArns" in running_response and not "taskArns" in pending_response:
			return []

		for task_arn in running_response[ "taskArns" ]:
			task_arns.append(
				task_arn
			)

		for task_arn in pending_response[ "taskArns" ]:
			task_arns.append(
				task_arn
			)
		
		return task_arns

	@staticmethod
	def _get_tasks_metadata_list( credentials, arn_list ):
		ecs_client = get_aws_client(
			"ecs",
			credentials
		)

		response = ecs_client.describe_tasks(
			cluster=CLUSTER_NAME,
			tasks=arn_list
		)

		if not "tasks" in response:
			return []

		return response[ "tasks" ]

	@staticmethod
	def _get_public_ips_from_private_ip_addresses( credentials, private_ip_addresses ):
		ec2_client = get_aws_client(
			"ec2",
			credentials
		)

		remaining_attempts = 20

		while remaining_attempts > 0:
			print( "Querying for public IP address from private IP..." )
			response = ec2_client.describe_network_interfaces(
				Filters=[
					{
						# Filter by private IPs since it's one of the only fucking
						# things we can use from the task description to get the public IP.
						# Which should've been included in the task description response
						# but isn't for some probably bullshit reason.
						"Name": "addresses.private-ip-address",
						"Values": private_ip_addresses
					}
				]
			)

			if "NetworkInterfaces" in response and len( response[ "NetworkInterfaces" ] ) > 0:
				break

			time.sleep(1)
			remaining_attempts = remaining_attempts - 1

			if remaining_attempts == 0:
				return []

		ip_addresses = []

		for interface_metadata in response[ "NetworkInterfaces" ]:
			ip_addresses.append(
				interface_metadata[ "Association" ][ "PublicIp" ]
			)

		return ip_addresses

	@run_on_executor
	def get_build_container_ips( self, credentials ):
		return AWSECSManager._get_build_container_ips(
			credentials
		)

	@staticmethod
	def _get_build_container_ips( credentials ):
		"""
		Searchs for an already-running build container.

		If one exists and is running, we use it. Otherwise
		we launch up a new container.

		(The containers will automatically terminate themselves
		after not doing any work for a given period of time).
		"""
		logit( "Pulling all running containers IPs..." )

		logit( "Pulling all existing task ARNs..." )

		# First check if we have any already-running containers
		existing_task_arns = AWSECSManager._get_running_task_arns(
			credentials
		)

		if len( existing_task_arns ) == 0:
			logit( "No existing tasks found, starting one and retrying action..." )
			AWSECSManager._start_builder_ecs_task( credentials )

			# Eventual consistency so we'll wait a bit
			time.sleep(2)
			return AWSECSManager._get_build_container_ips( credentials )

		logit( "Existing tasks found, pulling metadata for tasks..." )

		# Pull the metadata for all running and pending tasks
		task_info_list = AWSECSManager._get_tasks_metadata_list(
			credentials,
			existing_task_arns
		)

		build_container_private_ips = []

		for task_info in task_info_list:
			if task_info[ "lastStatus" ] == "RUNNING":
				build_container_private_ips.append(
					task_info[ "containers" ][0][ "networkInterfaces" ][0][ "privateIpv4Address" ]
				)

		if len( build_container_private_ips ) == 0:
			logit( "No RUNNING build instances found, waiting briefly and retrying action..." )
			time.sleep(2)
			return AWSECSManager._get_build_container_ips( credentials )

		# Exchange interface IDs for interface public IPs
		build_container_instance_ips = AWSECSManager._get_public_ips_from_private_ip_addresses(
			credentials,
			build_container_private_ips
		)

		return build_container_instance_ips

aws_ecs_manager = AWSECSManager()