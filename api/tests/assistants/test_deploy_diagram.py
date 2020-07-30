from tornado.testing import AsyncHTTPTestCase, gen_test

from assistants.deployments.aws.aws_deployment import AwsDeployment
from tests_utils.mocks.aws import MockAWSDependenciesHolder
from tests_utils.mocks.task_spawner import MockTaskSpawnerHolder
from tests_utils.tornado_test_utils import create_future
from tests_utils.unit_test_base import ServerUnitTestBase


class TestDeployDiagram(ServerUnitTestBase, AsyncHTTPTestCase):
	mock_aws = None

	def setUp(self):
		super(TestDeployDiagram, self).setUp()

		self.mock_aws = self.app_object_graph.provide(MockAWSDependenciesHolder)
		self.mock_task_spawner = self.app_object_graph.provide(MockTaskSpawnerHolder).task_spawner

	def get_credentials(self):
		return {
			"region": "fake-region",
			"account_id": "fake-account-id",
			"account_type": "MANAGED",
			"redis_hostname": "fake-redis-hostname",
			"redis_password": "fake-redis-password",
			"redis_port": "fake-redis-port",
			"logs_bucket": "fake-logs-bucket",
			"lambda_packages_bucket": "fake-lambda-packages-bucket"
		}

	@gen_test
	def test_deploy_diagram( self ):
		ts = self.mock_task_spawner
		ts.get_aws_lambda_existence_info.return_value = create_future(False)
		ts.deploy_aws_lambda.return_value = create_future()
		ts.create_rest_api.return_value = create_future("test-api-gateway-id")
		ts.clean_lambda_iam_policies.return_value = create_future()
		ts.create_resource.return_value = create_future("test-api-resource-id")
		ts.create_method.return_value = create_future()
		ts.link_api_method_to_lambda.return_value = create_future()
		ts.deploy_api_gateway_to_stage.return_value = create_future()
		ts.create_project_id_log_table.return_value = create_future()

		self.mock_aws.api_gateway_manager.get_resources.return_value = create_future([
			{
				"id": "test-resource-1",
				"resourceMethods": {
					"GET": {
						"methodIntegration": {
							"uri": "test-lambda-uri"
						}
					},
				},
				"path": "/"
			},
			{
				"id": "test-resource-2",
				"resourceMethods": {
					"POST": {
						"methodIntegration": {
							"uri": "test-lambda-uri"
						}
					}
				},
				"path": "/asdf"
			}
		])
		self.mock_aws.api_gateway_manager.delete_rest_api_resource_method = create_future()
		self.mock_aws.api_gateway_manager.delete_rest_api_resource = create_future()
		self.mock_aws.api_gateway_manager.get_stages = create_future([
			{
				"stageName": "test"
			}
		])
		self.mock_aws.api_gateway_manager.delete_stage = create_future()

		simple_deployment = self.load_fixture("simple_deployment.json", load_json=True)
		simple_project_config = self.load_fixture("simple_project_config.json", load_json=True)
		latest_simple_deployment = None

		deployment_diagram: AwsDeployment = AwsDeployment(
			"test-id", "test", simple_project_config, latest_simple_deployment)

		exceptions = yield deployment_diagram.deploy_diagram(
			simple_deployment,
		)

		assert len(exceptions) == 0

	@gen_test
	def test_deploy_diagram_with_previous_deploy( self ):
		ts = self.mock_task_spawner
		ts.get_aws_lambda_existence_info.return_value = create_future(True)
		ts.list_lambda_event_source_mappings.return_value = create_future([])
		ts.get_lambda_uri_for_api_method.return_value = "Untitled_API_Endpoint_Block89765a6a-dc1a-4aff-b001-6e2a6e5a677a"
		ts.deploy_api_gateway_to_stage.return_value = create_future()
		ts.create_project_id_log_table.return_value = create_future()

		self.mock_aws.api_gateway_manager.get_resources.return_value = create_future([
			{
				"id": "test-resource-1",
				"path": "/"
			},
			{
				"id": "test-resource-1",
				"path": "/replaceme"
			},
			{
				"id": "test-resource-2",
				"resourceMethods": {
					"GET": {
						"methodIntegration": {
							"uri": "Untitled_API_Endpoint_Block89765a6a-dc1a-4aff-b001-6e2a6e5a677a"
						}
					}
				},
				"path": "/replaceme/stonelightningslayer"
			}
		])
		self.mock_aws.api_gateway_manager.api_gateway_exists.return_value = create_future(True)

		simple_deployment = self.load_fixture("simple_deployment.json", load_json=True)
		simple_project_config = self.load_fixture("simple_project_config.json", load_json=True)
		latest_simple_deployment = self.load_fixture("simple_deployment_previous_deploy.json", load_json=True)

		deployment_diagram: AwsDeployment = AwsDeployment(
			"test-id", "test", simple_project_config, latest_simple_deployment)

		exceptions = yield deployment_diagram.deploy_diagram(
			simple_deployment
		)

		assert len(exceptions) == 0
