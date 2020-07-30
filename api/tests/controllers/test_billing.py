import time

from tornado.testing import AsyncHTTPTestCase, gen_test
from mock import MagicMock, patch

from assistants.aws_account_management.account_usage_manager import AwsUsageData, AwsAccountUsageManager
from controller.billing import RealtimeLambdaBillingWatchdog
from models import Project, AWSAccount, User
from models.lambda_execution_monthly_report import LambdaExecutionMonthlyReport
from models.users import RefineryUserTier
from tests_utils.mocks.app_config import AppConfigHolder
from tests_utils.mocks.aws import MockAWSDependenciesHolder
from tests_utils.tornado_test_utils import create_future
from tests_utils.unit_test_base import ServerUnitTestBase


class TestBilling(ServerUnitTestBase, AsyncHTTPTestCase):
    mock_aws = None
    mock_task_spawner = None

    def setUp(self):
        super().setUp()

        self.app_config = self.app_object_graph.provide(AppConfigHolder).app_config
        self.mock_aws: MockAWSDependenciesHolder = self.app_object_graph.provide(MockAWSDependenciesHolder)

    def create_test_project(self, project_id, user):
        project = Project()
        project.id = project_id
        project.users = [user]
        return self.create_and_save_obj(project)

    def create_test_aws_account(self, org_id, account_id="testid"):
        aws_account = AWSAccount()
        aws_account.account_type = "MANAGED"
        aws_account.organization_id = org_id
        aws_account.aws_account_status = "IN_USE"
        aws_account.s3_bucket_suffix = ""
        aws_account.region = "us-west-2"
        aws_account.account_id = account_id
        return self.create_and_save_obj(aws_account)

    def mock_free_tier_freeze_calls(self, monthly_usage_reports, aws_usage_data):
        self.mock_aws.aws_account_usage_manager.get_or_create_lambda_monthly_report.side_effect = monthly_usage_reports
        self.mock_aws.aws_account_usage_manager.get_aws_usage_data.side_effect = aws_usage_data

        self.mock_aws.aws_account_freezer.handle_user_over_limit.return_value = create_future(dict())

    def get_aws_account_from_id(self, aws_account_id):
        return self.dbsession.query(AWSAccount).filter(AWSAccount.id == aws_account_id).first()

    @gen_test(timeout=10)
    def test_free_tier_freeze_from_lambda_execution_details(self):
        """
        * PAID user has any amount of used gb seconds, do not freeze
        * organization has any PAID user and any amount of used gb seconds, do not freeze
        * FREE user uses < max allowed gb seconds, do not freeze
        * FREE user uses > max allowed gb seconds, freeze account
        * first request: FREE user uses < max allowed gb seconds, second request: FREE user has used > max allowed gb seconds (compounded from previous request)
        :return:
        """

        lambda_execution_details_request = self.load_fixture("multiple_accounts_lambda_execution_details.json", load_json=True)

        user1 = self.create_test_user(email="user1@email.com", tier=RefineryUserTier.FREE)
        user2 = self.create_test_user(email="user2@email.com", tier=RefineryUserTier.FREE)
        user3 = self.create_test_user(email="user3@email.com", tier=RefineryUserTier.PAID)

        org1 = self.create_test_user_organization(user1.id)
        org2 = self.create_test_user_organization(user2.id)
        org3 = self.create_test_user_organization(user3.id)

        aws_account1 = self.create_test_aws_account(org1.id, "123451104803")
        aws_account2 = self.create_test_aws_account(org2.id, "753651104803")
        aws_account3 = self.create_test_aws_account(org3.id, "666666666666")

        aws_account1_dict = aws_account1.to_dict()
        aws_account2_dict = aws_account2.to_dict()

        monthly_usage_reports = [
            LambdaExecutionMonthlyReport(aws_account1.id, 9)
        ]
        aws_usage_data = [
            AwsUsageData(
                gb_seconds=2,
                remaining_gb_seconds=0,
                executions=2,
                is_over_limit=True
            )
        ]
        self.mock_free_tier_freeze_calls(monthly_usage_reports, aws_usage_data)

        watchdog = RealtimeLambdaBillingWatchdog(self._app, MagicMock(), object_graph=self.app_object_graph)

        for account_id, lambda_execution_reports in lambda_execution_details_request.items():
            yield watchdog.process_lambda_execution_reports(account_id, lambda_execution_reports)

        self.mock_aws.aws_account_freezer.handle_user_over_limit.assert_any_call(aws_account1_dict)
        self.mock_aws.aws_account_freezer.handle_user_over_limit.assert_any_call(aws_account2_dict)

    @gen_test(timeout=10)
    def test_paid_tier_not_frozen_from_lambda_execution_details(self):
        lambda_execution_details_request = self.load_fixture("multiple_accounts_lambda_execution_details.json", load_json=True)

        user = self.create_test_user(email="user@email.com", tier=RefineryUserTier.PAID)

        org = self.create_test_user_organization(user.id)

        aws_account = self.create_test_aws_account(org.id, "123451104803")

        watchdog = RealtimeLambdaBillingWatchdog(self._app, MagicMock(), object_graph=self.app_object_graph)

        for account_id, lambda_execution_reports in lambda_execution_details_request.items():
            yield watchdog.process_lambda_execution_reports(account_id, lambda_execution_reports)

        self.mock_aws.aws_account_usage_manager.get_or_create_lambda_monthly_report.assert_not_called()
        self.mock_aws.aws_account_freezer.handle_user_over_limit.assert_not_called()

    @gen_test(timeout=10)
    def test_free_tier_frozen_after_multiple_reports(self):
        lambda_execution_details_request = self.load_fixture("below_free_tier_usage_lambda_execution_details.json", load_json=True)

        user = self.create_test_user(email="user@email.com", tier=RefineryUserTier.FREE)

        org = self.create_test_user_organization(user.id)

        aws_account = self.create_test_aws_account(org.id, "123451104803")
        aws_account_dict = aws_account.to_dict()

        monthly_usage_reports = [
            LambdaExecutionMonthlyReport(aws_account.id, 0),
            LambdaExecutionMonthlyReport(aws_account.id, 10)
        ]
        aws_usage_data = [
            AwsUsageData(
                gb_seconds=2,
                remaining_gb_seconds=8,
                executions=1,
                is_over_limit=False
            ),
            AwsUsageData(
                gb_seconds=10,
                remaining_gb_seconds=0,
                executions=2,
                is_over_limit=True
            )
        ]
        self.mock_free_tier_freeze_calls(monthly_usage_reports, aws_usage_data)

        watchdog = RealtimeLambdaBillingWatchdog(self._app, MagicMock(), object_graph=self.app_object_graph)

        for account_id, lambda_execution_reports in lambda_execution_details_request.items():
            yield watchdog.process_lambda_execution_reports(account_id, lambda_execution_reports)

        assert self.mock_aws.aws_account_usage_manager.get_or_create_lambda_monthly_report.call_count == 1
        self.mock_aws.aws_account_freezer.handle_user_over_limit.assert_not_called()

        for account_id, lambda_execution_reports in lambda_execution_details_request.items():
            yield watchdog.process_lambda_execution_reports(account_id, lambda_execution_reports)

        assert self.mock_aws.aws_account_usage_manager.get_or_create_lambda_monthly_report.call_count == 2
        self.mock_aws.aws_account_freezer.handle_user_over_limit.assert_any_call(aws_account_dict)

    @patch('assistants.aws_account_management.account_usage_manager.datetime')
    @gen_test(timeout=10)
    def test_free_tier_new_month_new_report(self, datetime):
        from datetime import date

        datetime.today.side_effect = [date(2020, 1, 1), date(2020, 2, 1)]

        user = self.create_test_user(email="user@email.com", tier=RefineryUserTier.FREE)

        org = self.create_test_user_organization(user.id)

        aws_account = self.create_test_aws_account(org.id, "123451104803")

        monthly_report = LambdaExecutionMonthlyReport(aws_account.id, 0)
        monthly_report.timestamp = int(date(2020, 1, 2).strftime('%s'))
        print(monthly_report.timestamp)
        self.dbsession.add(monthly_report)
        self.dbsession.commit()

        aws_account_usage_manager: AwsAccountUsageManager = self.app_object_graph.provide(AwsAccountUsageManager)
        stored_monthly_report = aws_account_usage_manager.get_or_create_lambda_monthly_report(
            self.dbsession,
            aws_account.id,
            1,
            1
        )

        assert stored_monthly_report.id == monthly_report.id

        stored_monthly_report = aws_account_usage_manager.get_or_create_lambda_monthly_report(
            self.dbsession,
            aws_account.id,
            1,
            1
        )

        assert stored_monthly_report.id != monthly_report.id
