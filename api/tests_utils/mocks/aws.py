import pinject

from mock import MagicMock


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
    def provide_aws_cost_explorer(self):
        return MagicMock()

    @pinject.provides("aws_organization_client")
    def provide_aws_organization_client(self):
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
