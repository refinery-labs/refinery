import json

import pinject
from mock import patch, MagicMock
from tornado.concurrent import Future

from assistants.task_spawner.task_spawner_assistant import TaskSpawner
from models import User, EmailAuthToken, Organization, Project, AWSAccount
from tests_utils.unit_test_base import ServerUnitTestBase

from tornado.testing import AsyncHTTPTestCase, gen_test


class MockAWSDependenciesHolder:
	aws_cost_explorer = None
	aws_organization_client = None
	api_gateway_manager = None
	lambda_manager = None
	schedule_trigger_manager = None
	sns_manager = None
	sqs_manager = None
	preterraform_manager = None

	@pinject.copy_args_to_public_fields
	def __init__(
		self,
		aws_cost_explorer,
		aws_organization_client,
		api_gateway_manager,
		lambda_manager,
		schedule_trigger_manager,
		sns_manager,
		sqs_manager,
		preterraform_manager
	):
		pass


class MockAWSDependencies(pinject.BindingSpec):
	@pinject.provides("aws_cost_explorer")
	def provide_aws_cost_explorer( self ):
		return MagicMock()

	@pinject.provides("aws_organization_client")
	def provide_aws_organization_client( self ):
		return MagicMock()

	@pinject.provides("api_gateway_manager")
	def provide_api_gateway_manager( self ):
		return MagicMock()

	@pinject.provides("lambda_manager")
	def provide_lambda_manager( self ):
		return MagicMock()

	@pinject.provides("schedule_trigger_manager")
	def provide_schedule_trigger_manager( self ):
		return MagicMock()

	@pinject.provides("sns_manager")
	def provide_sns_manager( self ):
		return MagicMock()

	@pinject.provides("sqs_manager")
	def provide_sqs_manager( self ):
		return MagicMock()

	@pinject.provides("preterraform_manager")
	def provide_preterraform_manager( self ):
		return MagicMock()


class MockTaskSpawnerHolder:
	task_spawner = None

	@pinject.copy_args_to_public_fields
	def __init__(self, task_spawner):
		pass


class MockTaskSpawner(pinject.BindingSpec):
	task_spawner = None

	@pinject.provides("task_spawner")
	def provide_task_spawner( self ):
		self.task_spawner = MagicMock()
		return self.task_spawner


class TestAWS( ServerUnitTestBase, AsyncHTTPTestCase ):
	mock_aws = None
	mock_task_spawner = None

	def __init__(self, *args, **kwargs):
		super(TestAWS, self).__init__(*args, **kwargs)

		mock_aws_deps = MockAWSDependencies()
		mock_task_spawner_deps = MockTaskSpawner()
		self.binding_specs = [mock_aws_deps, mock_task_spawner_deps]

	def setUp(self):
		super(TestAWS, self).setUp()

		self.mock_aws = self.app_object_graph.provide(MockAWSDependenciesHolder)
		self.mock_task_spawner = self.app_object_graph.provide(MockTaskSpawnerHolder).task_spawner

	def get_user_from_id( self, user_id ):
		return self.dbsession.query( User ).filter( User.id == user_id ).first()

	def create_test_user( self ):
		user = User()
		user.email = "test@test.com"
		return self.create_and_save_obj( user )

	def create_test_project( self, project_id, user ):
		project = Project()
		project.id = project_id
		project.users = [user]
		return self.create_and_save_obj( project )

	def create_test_aws_account( self, org ):
		aws_account = AWSAccount()
		aws_account.organization_id = org.id
		aws_account.aws_account_status = "IN_USE"
		aws_account.s3_bucket_suffix = ""
		aws_account.region = "us-west-2"
		aws_account.account_id = "testid"
		return self.create_and_save_obj(aws_account)

	@staticmethod
	def create_future( result=None ):
		future = Future()
		future.set_result(result)
		return future

	def mock_simple_deployment_calls( self ):
		self.mock_aws.lambda_manager.delete_lambda.return_value = dict()
		self.mock_aws.sns_manager.delete_sns_topic.return_value = dict()
		self.mock_aws.sqs_manager.delete_sqs_queue.return_value = dict()
		self.mock_aws.schedule_trigger_manager.delete_schedule_trigger.return_value = dict()
		# TODO api_gateway_manager teardown

		self.mock_task_spawner.deploy_aws_lambda.return_value = self.create_future(dict(
			FunctionArn="test_arn"
		))

		self.mock_task_spawner.create_rest_api.return_value = self.create_future(dict(
			id="test_id"
		))

		self.mock_task_spawner.clean_lambda_iam_policies.return_value = self.create_future()

		self.mock_aws.api_gateway_manager.get_resources.side_effect = [
			self.create_future([
				dict(path="/", id="test_id")
			]),
			self.create_future()
		]

		self.mock_task_spawner.create_resource.return_value = self.create_future(dict(id="test_id"))

		self.mock_task_spawner.create_method.return_value = self.create_future()
		self.mock_task_spawner.link_api_method_to_lambda.return_value = self.create_future()
		self.mock_task_spawner.add_integration_response.return_value = self.create_future()
		self.mock_task_spawner.deploy_api_gateway_to_stage.return_value = self.create_future()
		self.mock_task_spawner.create_project_id_log_table.return_value = self.create_future()

	@patch('controller.base.BaseHandler.get_secure_session_data')
	@gen_test(timeout=10)
	def test_simple_deployment(self, get_secure_session_data):
		simple_deployment_request = self.load_fixture( "simple_deployment_request.json", load_json=True )

		user = self.create_test_user()
		project = self.create_test_project(simple_deployment_request["project_id"], user)
		org = self.create_test_user_organization(user.id)
		aws_account = self.create_test_aws_account(org)

		get_secure_session_data.return_value = dict(
			user_id=user.id
		)

		self.mock_simple_deployment_calls()

		response = yield self.http_client.fetch(
			self.get_url("/api/v1/aws/deploy_diagram"),
			method='POST',
			body=json.dumps(simple_deployment_request),
			headers={
				"X-CSRF-Validation-Header": "True"
			}
		)
		json_resp = json.loads(response.body)
		assert json_resp['success'] == True
