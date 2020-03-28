import time
import tornado
import botocore

from tornado.concurrent import run_on_executor, futures

from assistants.aws_clients.aws_clients_assistant import get_aws_client
from utils.general import logit
from tornado import gen

from botocore.exceptions import ClientError

class PreTerraformManager(object):
	"""
	There are some steps that need to be done pre-terraform because
	terraform can not handle certain situations where specific AWS
	resources do not exist.

	One such example is AWSServiceRoleForECS which is a service-linked
	role for AWS ECS. It is normally automatically created when you attempt
	to create a new ECS cluster. However, due to AWS's eventual-consistency
	nature, terraform will choke on setting up the ECS resources because the
	AWSServiceRoleForECS role will not be immediately available. Because of 
	this terraform will attempt to use it when it's not yet ready and will
	choke out.

	The specific bug can be found here:
	https://github.com/terraform-providers/terraform-provider-aws/issues/11417

	To mitigate this, we use the Boto3 API to create the AWSServiceRoleForECS
	role ahead of time before we run terraform. We then wait for the propogation
	to finish before applying the actual terraform config. This mitigates the
	problem from occuring.
	"""
	def __init__(self, loop=None):
		self.executor = futures.ThreadPoolExecutor( 10 )
		self.loop = loop or tornado.ioloop.IOLoop.current()

	@run_on_executor
	def ensure_ecs_service_linked_role_exists( self, credentials ):
		return PreTerraformManager._ensure_ecs_service_linked_role_exists( credentials )

	@staticmethod
	def _ensure_ecs_service_linked_role_exists( credentials ):
		logit( "Checking if ECS service-linked role exists..." )

		# First check to see if the role exists
		ecs_service_linked_role_exists = PreTerraformManager._check_if_ecs_service_linked_role_exists(
			credentials
		)

		if ecs_service_linked_role_exists == True:
			logit( "ECS service-linked role exists! We're good to go." )
			return

		logit( "ECS service-linked role does not exist, creating it..." )
		PreTerraformManager._create_ecs_service_linked_role(
			credentials
		)

		logit( "ECS service-linked role created, waiting a bit before retrying operation..." )

		# Wait a bit for propogation
		time.sleep( 3 )

		return PreTerraformManager._ensure_ecs_service_linked_role_exists(
			credentials
		)

	@run_on_executor
	def check_if_ecs_service_linked_role_exists( self, credentials ):
		return PreTerraformManager._check_if_ecs_service_linked_role_exists( credentials )

	@staticmethod
	def _check_if_ecs_service_linked_role_exists( credentials ):
		iam_client = get_aws_client(
			"iam",
			credentials
		)

		try:
			linked_role_get_response = iam_client.get_role(
				RoleName="AWSServiceRoleForECS"
			)
		except botocore.exceptions.ClientError as boto_error:
			if boto_error.response[ "Error" ][ "Code" ] != "NoSuchEntity":
				# If it's not the exception we expect then throw
				raise
			return False

		return True

	@run_on_executor
	def create_ecs_service_linked_role( self, credentials ):
		return PreTerraformManager._create_ecs_service_linked_role( credentials )
		
	@staticmethod
	def _create_ecs_service_linked_role( credentials ):
		iam_client = get_aws_client(
			"iam",
			credentials
		)

		created_service_linked_role_response = iam_client.create_service_linked_role(
			AWSServiceName="ecs.amazonaws.com",
			Description="Role to enable Amazon ECS to manage your cluster."
		)
