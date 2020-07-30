import pinject

from mock import MagicMock

from assistants.aws_account_management.account_freezer import AwsAccountFreezer
from assistants.aws_account_management.account_usage_manager import AwsAccountUsageManager
from assistants.aws_account_management.preterraform import PreterraformManager
from assistants.deployments.api_gateway import ApiGatewayManager
from assistants.deployments.awslambda import LambdaManager
from assistants.deployments.schedule_trigger import ScheduleTriggerManager
from assistants.deployments.sns import SnsManager
from assistants.deployments.sqs import SqsManager


class MockAWSDependenciesHolder:
    aws_cost_explorer = None
    aws_organization_client = None
    aws_cloudwatch_client = None
    sts_client = None
    api_gateway_manager: ApiGatewayManager = None
    lambda_manager: LambdaManager = None
    schedule_trigger_manager: ScheduleTriggerManager = None
    sns_manager: SnsManager = None
    sqs_manager: SqsManager = None
    preterraform_manager: PreterraformManager = None
    aws_account_freezer: AwsAccountFreezer = None
    aws_account_usage_manager: AwsAccountUsageManager = None

    @pinject.copy_args_to_public_fields
    def __init__(
        self,
        aws_cost_explorer,
        aws_organization_client,
        aws_cloudwatch_client,
        aws_client_factory,
        sts_client,
        api_gateway_manager,
        lambda_manager,
        schedule_trigger_manager,
        sns_manager,
        sqs_manager,
        preterraform_manager,
        aws_account_freezer,
        aws_account_usage_manager
    ):
        pass


class MockAWSDependencies(pinject.BindingSpec):
    @pinject.provides("aws_cost_explorer")
    def provide_aws_cost_explorer(self):
        return MagicMock()

    @pinject.provides("aws_organization_client")
    def provide_aws_organization_client(self):
        return MagicMock()

    @pinject.provides("aws_cloudwatch_client")
    def provide_aws_cloudwatch_client(self):
        return MagicMock()

    @pinject.provides("aws_client_factory")
    def provide_aws_client_factory(self):
        return MagicMock()

    @pinject.provides("aws_account_freezer")
    def provide_aws_account_freezer(self):
        return MagicMock()

    @pinject.provides("aws_account_usage_manager")
    def provide_aws_account_usage_manager(self):
        return MagicMock()

    @pinject.provides("api_gateway_manager")
    def provide_api_gateway_manager(self):
        return MagicMock()

    @pinject.provides("lambda_manager")
    def provide_lambda_manager(self):
        return MagicMock()

    @pinject.provides("schedule_trigger_manager")
    def provide_schedule_trigger_manager(self):
        return MagicMock()

    @pinject.provides("sns_manager")
    def provide_sns_manager(self):
        return MagicMock()

    @pinject.provides("sqs_manager")
    def provide_sqs_manager(self):
        return MagicMock()

    @pinject.provides("preterraform_manager")
    def provide_preterraform_manager(self):
        return MagicMock()

    @pinject.provides("sts_client")
    def provide_sts_client(self):
        return MagicMock()
