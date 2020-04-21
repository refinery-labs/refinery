from utils.performance_decorators import emit_runtime_metrics
from tornado.concurrent import run_on_executor, futures
from tasks.athena import (
    perform_athena_query,
    get_athena_results_from_s3,
    get_block_executions,
    create_project_id_log_table,
    get_project_execution_logs
)
from tasks.s3 import (
    read_from_s3,
    get_json_from_s3,
    write_json_to_s3,
    s3_object_exists,
    read_from_s3_and_return_input,
    bulk_s3_delete,
    get_s3_pipeline_execution_logs,
    get_build_packages,
    get_s3_list_from_prefix,
    get_s3_pipeline_execution_ids,
    get_s3_pipeline_timestamp_prefixes
)
from tasks.role import (
    get_assume_role_credentials,
    create_third_party_aws_lambda_execute_role
)
from tasks.terraform import (
    write_terraform_base_files,
    terraform_configure_aws_account,
    terraform_apply,
    terraform_plan
)
from tasks.email import (
    send_email,
    send_registration_confirmation_email,
    send_authentication_email
)
from tasks.aws_account import (
    unfreeze_aws_account,
    freeze_aws_account,
    create_new_sub_aws_account
    recreate_aws_console_account
)
from tasks.stripe import (
    get_account_cards,
    get_stripe_customer_information,
    associate_card_token_with_customer_account,
    stripe_create_customer,
    delete_card_from_account
    set_stripe_customer_default_payment_source
)
from tasks.billing import (
    get_sub_account_billing_data,
    generate_managed_accounts_invoices,
    pull_current_month_running_account_totals,
    enforce_account_limits,
    get_sub_account_month_billing_data,
    get_sub_account_billing_data,
    get_sub_account_billing_forecast
)
from tasks.aws_lambda import (
    check_if_layer_exists,
    create_lambda_layer,
    warm_up_lambda,
    execute_aws_lambda,
    delete_aws_lambda,
    update_lambda_environment_variables,
    set_lambda_reserved_concurrency,
    deploy_aws_lambda,
    get_aws_lambda_existence_info,
    get_lambda_cloudwatch_logs,
    clean_lambda_iam_policies
)
from tasks.build.common import (
    get_final_zip_package_path,
    get_codebuild_artifact_zip_data,
    finalize_codebuild
)
from tasks.build.ruby import start_ruby264_codebuild
from tasks.build.nodejs import start_node810_codebuild
from tasks.build.python import (
    start_python_36_codebuild,
    start_python27_codebuild,
    get_python36_lambda_base_zip,
    get_python27_lambda_base_zip
)
from tasks.build.common import (
    get_final_zip_package_path,
    get_codebuild_artifact_zip_data
)
from tasks.build.php import (
    start_php73_codebuild
)
from tasks.cloudwatch import (
    create_cloudwatch_rule,
    create_cloudwatch_group,
    add_rule_target,
    get_cloudwatch_existence_info
)
from tasks.sns import (
    create_sns_topic,
    subscribe_lambda_to_sns_topic,
    get_sns_existence_info
)
from tasks.sqs import (
    create_sqs_queue,
    map_sqs_to_lambda,
    get_sqs_existence_info
)
from tasks.api_gateway import (
    create_rest_api,
    deploy_api_gateway_to_stage,
    create_resource
    create_method,
    add_integration_response,
    link_api_method_to_lambda
)

try:
    # for Python 2.x
    # noinspection PyCompatibility
    from StringIO import StringIO
except ImportError:
    # for Python 3.x
    from io import StringIO


# noinspection PyTypeChecker,SqlResolve
class TaskSpawner(object):
    app_config = None
    db_session_maker = None
    aws_cloudwatch_client = None
    aws_cost_explorer = None
    aws_organization_client = None
    aws_lambda_client = None
    api_gateway_manager = None
    lambda_manager = None
    logger = None
    schedule_trigger_manager = None
    sns_manager = None
    preterraform_manager = None
    aws_client_factory = None  # type: AwsClientFactory
    sts_client = None

    # noinspection PyUnresolvedReferences
    @pinject.copy_args_to_public_fields
    def __init__(
        self,
        app_config,
        db_session_maker,
        aws_cloudwatch_client,
        aws_cost_explorer,
        aws_organization_client,
        aws_lambda_client,
        api_gateway_manager,
        lambda_manager,
        logger,
        schedule_trigger_manager,
        sns_manager,
        preterraform_manager,
        aws_client_factory,
        sts_client,
        loop=None
    ):
        self.executor = futures.ThreadPoolExecutor(60)
        self.loop = loop or tornado.ioloop.IOLoop.current()

    @run_on_executor
    @emit_runtime_metrics("create_third_party_aws_lambda_execute_role")
    def create_third_party_aws_lambda_execute_role(self, credentials):
        return create_third_party_aws_lambda_execute_role(
            self.aws_client_factory,
            credentials
        )

    @run_on_executor
    @emit_runtime_metrics("get_json_from_s3")
    def get_json_from_s3(self, credentials, s3_bucket, s3_path):
        return get_json_from_s3(
            aws_client_factory,
            credentials,
            s3_bucket,
            s3_path
        )

    @run_on_executor
    @emit_runtime_metrics("write_json_to_s3")
    def write_json_to_s3(self, credentials, s3_bucket, s3_path, input_data):
        return write_json_to_s3(
            aws_client_factory,
            credentials,
            s3_bucket,
            s3_path,
            input_data
        )

    @run_on_executor
    @emit_runtime_metrics("get_block_executions")
    def get_block_executions(self, credentials, project_id, execution_pipeline_id, arn, oldest_timestamp):
        return get_block_executions(
            self.aws_client_factory,
            credentials,
            project_id,
            execution_pipeline_id,
            arn,
            oldest_timestamp
        )

    @run_on_executor
    @emit_runtime_metrics("get_project_execution_logs")
    def get_project_execution_logs(self, credentials, project_id, oldest_timestamp):
        return get_project_execution_logs(
            self.aws_client_factory,
            credentials,
            project_id,
            oldest_timestamp
        )

    @staticmethod
    @run_on_executor
    @emit_runtime_metrics("create_project_id_log_table")
    def create_project_id_log_table(self, credentials, project_id):
        return create_project_id_log_table(
            self.aws_client_factory,
            credentials,
            project_id
        )

    @run_on_executor
    @emit_runtime_metrics("perform_athena_query")
    def perform_athena_query(self, credentials, query, return_results):
        return perform_athena_query(
            self.aws_client_factory,
            credentials,
            query,
            return_results
        )

    @run_on_executor
    @emit_runtime_metrics("get_athena_results_from_s3")
    def get_athena_results_from_s3(self, credentials, s3_bucket, s3_path):
        return get_athena_results_from_s3(
            self.aws_client_factory,
            credentials,
            s3_bucket,
            s3_path
        )

    @run_on_executor
    @emit_runtime_metrics("get_assume_role_credentials")
    def get_assume_role_credentials(self, aws_account_id, session_lifetime):
        return get_assume_role_credentials(
            self.app_config,
            self.sts_client,
            aws_account_id,
            session_lifetime
        )

    @run_on_executor
    @emit_runtime_metrics("create_new_sub_aws_account")
    def create_new_sub_aws_account(self, account_type, aws_account_id):
        return create_new_sub_aws_account(
            self.app_config,
            self.db_session_maker,
            self.aws_organization_client,
            self.sts_client,
            account_type,
            aws_account_id
        )

    @run_on_executor
    @emit_runtime_metrics("terraform_configure_aws_account")
    def terraform_configure_aws_account(self, aws_account_dict):
        return terraform_configure_aws_account(
            self.aws_client_factory,
            self.app_config,
            self.preterraform_manager,
            self.sts_client,
            aws_account_dict
        )

    @run_on_executor
    @emit_runtime_metrics("write_terraform_base_files")
    def write_terraform_base_files(self, aws_account_dict):
        return write_terraform_base_files(
            self.app_config,
            self.sts_client,
            aws_account_dict
        )

    @run_on_executor
    @emit_runtime_metrics("terraform_apply")
    def terraform_apply(self, aws_account_data, refresh_terraform_state=True):
        return terraform_apply(
            self.aws_client_factory,
            self.app_config,
            self.preterraform_manager,
            self.sts_client,
            aws_account_data,
            refresh_terraform_state
        )

    @run_on_executor
    @emit_runtime_metrics("terraform_plan")
    def terraform_plan(self, aws_account_data, refresh_terraform_state=True):
        return terraform_plan(
            self.app_config,
            self.sts_client,
            aws_account_data,
            refresh_terraform_state
        )

    @run_on_executor
    @emit_runtime_metrics("unfreeze_aws_account")
    def unfreeze_aws_account(self, credentials):
        return unfreeze_aws_account(
            self.aws_client_factory,
            credentials
        )

    @run_on_executor
    @emit_runtime_metrics("freeze_aws_account")
    def freeze_aws_account(self, credentials):
        return freeze_aws_account(
            self.app_config,
            self.aws_client_factory,
            self.db_session_maker,
            credentials
        )

    @run_on_executor
    @emit_runtime_metrics("recreate_aws_console_account")
    def recreate_aws_console_account(self, credentials, rotate_password, force_continue=False):
        return recreate_aws_console_account(
            self.app_config,
            self.aws_client_factory,
            credentials,
            rotate_password,
            force_continue=force_continue
        )

    @run_on_executor
    @emit_runtime_metrics("send_email")
    def send_email(self, to_email_string, subject_string, message_text_string, message_html_string):
        return send_email(
            self.app_config,
            to_email_string,
            subject_string,
            message_text_string,
            message_html_string
        )

    @run_on_executor
    @emit_runtime_metrics("send_registration_confirmation_email")
    def send_registration_confirmation_email(self, email_address, auth_token):
        return send_registration_confirmation_email(
            self.app_config,
            email_address,
            auth_token
        )

    @run_on_executor
    @emit_runtime_metrics("send_internal_registration_confirmation_email")
    def send_internal_registration_confirmation_email(self, customer_email_address, customer_name, customer_phone):
        return send_internal_registration_confirmation_email(
            self.app_config,
            customer_email_address,
            customer_name,
            customer_phone
        )

    @run_on_executor
    @emit_runtime_metrics("send_authentication_email")
    def send_authentication_email(self, email_address, auth_token):
        return send_authentication_email(email_address, auth_token)

    @run_on_executor
    @emit_runtime_metrics("stripe_create_customer")
    def stripe_create_customer(self, email, name, phone_number, source_token, metadata_dict):
        return stripe_create_customer(
            email,
            name,
            phone_number,
            source_token,
            metadata_dict
        )

    @run_on_executor
    @emit_runtime_metrics("associate_card_token_with_customer_account")
    def associate_card_token_with_customer_account(self, stripe_customer_id, card_token):
        return associate_card_token_with_customer_account(
            stripe_customer_id,
            card_token
        )

    @run_on_executor
    @emit_runtime_metrics("get_account_cards")
    def get_account_cards(self, stripe_customer_id):
        return get_account_cards(stripe_customer_id)

    @run_on_executor
    @emit_runtime_metrics("get_stripe_customer_information")
    def get_stripe_customer_information(self, stripe_customer_id):
        return get_stripe_customer_information(stripe_customer_id)

    @run_on_executor
    @emit_runtime_metrics("set_stripe_customer_default_payment_source")
    def set_stripe_customer_default_payment_source(self, stripe_customer_id, card_id):
        return set_stripe_customer_default_payment_source(
            stripe_customer_id,
            card_id
        )

    @run_on_executor
    @emit_runtime_metrics("delete_card_from_account")
    def delete_card_from_account(self, stripe_customer_id, card_id):
        return delete_card_from_account(stripe_customer_id, card_id)

    @run_on_executor
    @emit_runtime_metrics("generate_managed_accounts_invoices")
    def generate_managed_accounts_invoices(self, start_date_string, end_date_string):
        return generate_managed_accounts_invoices(
            self.aws_client_factory,
            self.aws_cost_explorer,
            self.app_config,
            self.db_session_maker,
            start_date_string,
            end_date_string
        )

    @run_on_executor
    @emit_runtime_metrics("pull_current_month_running_account_totals")
    def pull_current_month_running_account_totals(self):
        return pull_current_month_running_account_totals(
            self.aws_cost_explorer
        )

    @run_on_executor
    @emit_runtime_metrics("enforce_account_limits")
    def enforce_account_limits(self, aws_account_running_cost_list):
        return enforce_account_limits(
            self.app_config,
            self.aws_client_factory,
            self.db_session_maker,
            aws_account_running_cost_list
        )

    @run_on_executor
    @emit_runtime_metrics("get_sub_account_month_billing_data")
    def get_sub_account_month_billing_data(self, account_id, account_type, billing_month, use_cache):
        return get_sub_account_billing_data(
            self.app_config,
            self.db_session_maker,
            self.aws_cost_explorer,
            self.aws_client_factory,
            account_id,
            account_type,
            billing_month,
            use_cache
        )

    @run_on_executor
    @emit_runtime_metrics("mark_account_needs_closing")
    def mark_account_needs_closing(self, email):
        return mark_account_needs_closing(self.db_session_maker, email)

    @run_on_executor
    @emit_runtime_metrics("do_account_cleanup")
    def do_account_cleanup(self):
        return do_account_cleanup(
            self.app_config,
            self.db_session_maker,
            self.aws_lambda_client
        )

    @run_on_executor
    @emit_runtime_metrics("get_sub_account_billing_forecast")
    def get_sub_account_billing_forecast(self, account_id, start_date, end_date, granularity):
        return get_sub_account_billing_forecast(
            self.app_config,
            self.aws_cost_explorer,
            account_id,
            start_date,
            end_date,
            granularity
        )

    @run_on_executor
    @emit_runtime_metrics("check_if_layer_exists")
    def check_if_layer_exists(self, credentials, layer_name):
        return check_if_layer_exists(
            self.aws_client_factory,
            credentials,
            layer_name
        )

    @run_on_executor
    @emit_runtime_metrics("create_lambda_layer")
    def create_lambda_layer(self, credentials, layer_name, description, s3_bucket, s3_object_key):
        return create_lambda_layer(
            self.aws_client_factory,
            credentials,
            layer_name,
            description,
            s3_bucket,
            s3_object_key
        )

    @run_on_executor
    @emit_runtime_metrics("warm_up_lambda")
    def warm_up_lambda(self, credentials, arn, warmup_concurrency_level):
        return warm_up_lambda(
            self.aws_client_factory,
            credentials,
            arn,
            warmup_concurrency_level
        )

    @run_on_executor
    @emit_runtime_metrics("execute_aws_lambda")
    def execute_aws_lambda(self, credentials, arn, input_data):
        return execute_aws_lambda(
            self.aws_client_factory,
            credentials,
            arn,
            input_data
        )

    @run_on_executor
    @emit_runtime_metrics("delete_aws_lambda")
    def delete_aws_lambda(self, credentials, arn_or_name):
        return TaskSpawner._delete_aws_lambda(
            self.aws_client_factory,
            credentials,
            arn_or_name
        )

    @run_on_executor
    @emit_runtime_metrics("update_lambda_environment_variables")
    def update_lambda_environment_variables(self, credentials, func_name, environment_variables):
        return update_lambda_environment_variables(
            self.aws_client_factory,
            credentials,
            func_name,
            environment_variables
        )

    @run_on_executor
    @emit_runtime_metrics("set_lambda_reserved_concurrency")
    def set_lambda_reserved_concurrency(self, credentials, arn, reserved_concurrency_count):
        return set_lambda_reserved_concurrency(
            self.aws_client_factory,
            credentials,
            arn,
            reserved_concurrency_count
        )

    @run_on_executor
    @log_exception
    @emit_runtime_metrics("deploy_aws_lambda")
    def deploy_aws_lambda(self, credentials, lambda_object):
        return deploy_aws_lambda(
            self.app_config,
            self.aws_client_factory,
            self.db_session_maker,
            self.lambda_manager,
            credentials,
            lambda_object
        )

    @run_on_executor
    @emit_runtime_metrics("get_final_zip_package_path")
    def get_final_zip_package_path(self, language, libraries):
        return get_final_zip_package_path(language, libraries)

    @run_on_executor
    @emit_runtime_metrics("start_python36_codebuild")
    def start_python36_codebuild(self, credentials, libraries_object):
        return start_python36_codebuild(
            self.aws_client_factory,
            credentials,
            libraries_object
        )

    @run_on_executor
    @emit_runtime_metrics("start_python27_codebuild")
    def start_python27_codebuild(self, credentials, libraries_object):
        return start_python27_codebuild(
            self.aws_client_factory,
            credentials,
            libraries_object
        )

    @run_on_executor
    @emit_runtime_metrics("start_ruby264_codebuild")
    def start_ruby264_codebuild(self, credentials, libraries_object):
        return start_ruby264_codebuild(
            self.aws_client_factory,
            credentials,
            libraries_object
        )

    @run_on_executor
    @emit_runtime_metrics("start_node810_codebuild")
    def start_node810_codebuild(self, credentials, libraries_object):
        return start_node810_codebuild(
            self.aws_client_factory,
            credentials,
            libraries_object
        )

    @run_on_executor
    @emit_runtime_metrics("s3_object_exists")
    def s3_object_exists(self, credentials, bucket_name, object_key):
        return s3_object_exists(
            self.aws_client_factory,
            credentials,
            bucket_name,
            object_key
        )

    @run_on_executor
    @emit_runtime_metrics("get_codebuild_artifact_zip_data")
    def get_codebuild_artifact_zip_data(self, credentials, build_id, final_s3_package_zip_path):
        return get_codebuild_artifact_zip_data(
            self.aws_client_factory,
            credentials,
            build_id,
            final_s3_package_zip_path
        )

    @run_on_executor
    @emit_runtime_metrics("finalize_codebuild")
    def finalize_codebuild(self, credentials, build_id, final_s3_package_zip_path):
        return finalize_codebuild(
            self.aws_client_factory,
            credentials,
            build_id,
            final_s3_package_zip_path
        )

    @run_on_executor
    @emit_runtime_metrics("start_php73_codebuild")
    def start_php73_codebuild(self, credentials, libraries_object):
        return start_php73_codebuild(
            self.aws_client_factory,
            credentials,
            libraries_object
        )

    @run_on_executor
    @emit_runtime_metrics("start_node10163_codebuild")
    def start_node10163_codebuild(self, credentials, libraries_object):
        return TaskSpawner._start_node810_codebuild(
            self.aws_client_factory,
            credentials,
            libraries_object
        )

    @run_on_executor
    @emit_runtime_metrics("create_cloudwatch_group")
    def create_cloudwatch_group(self, credentials, group_name, tags_dict, retention_days):
        return create_cloudwatch_group(
            self.aws_client_factory,
            credentials,
            group_name,
            tags_dict,
            retention_days
        )

    @run_on_executor
    @emit_runtime_metrics("create_cloudwatch_rule")
    def create_cloudwatch_rule(self, credentials, id, name, schedule_expression, description, input_string):
        return create_cloudwatch_rule(
            self.aws_client_factory,
            credentials,
            id,
            name,
            schedule_expression,
            description,
            input_string
        )

    @run_on_executor
    @emit_runtime_metrics("add_rule_target")
    def add_rule_target(self, credentials, rule_name, target_id, target_arn, input_string):
        return add_rule_target(
            self.aws_client_factory,
            credentials,
            rule_name,
            target_id,
            target_arn,
            input_string
        )

    @run_on_executor
    @emit_runtime_metrics("create_sns_topic")
    def create_sns_topic(self, credentials, id, topic_name):
        return create_sns_topic(
            self.aws_client_factory,
            credentials,
            id,
            topic_name
        )

    @run_on_executor
    @emit_runtime_metrics("subscribe_lambda_to_sns_topic")
    def subscribe_lambda_to_sns_topic(self, credentials, topic_arn, lambda_arn):
        return subscribe_lambda_to_sns_topic(
            self.aws_client_factory,
            credentials,
            topic_arn,
            lambda_arn
        )

    @run_on_executor
    @emit_runtime_metrics("create_sqs_queue")
    def create_sqs_queue(self, credentials, id, queue_name, batch_size, visibility_timeout):
        return create_sqs_queue(
            self.aws_client_factory,
            credentials,
            id,
            queue_name,
            batch_size,
            visibility_timeout
        )

    @run_on_executor
    @emit_runtime_metrics("map_sqs_to_lambda")
    def map_sqs_to_lambda(self, credentials, sqs_arn, lambda_arn, batch_size):
        return map_sqs_to_lambda(
            self.aws_client_factory,
            credentials,
            sqs_arn,
            lambda_arn,
            batch_size
        )

    @run_on_executor
    @emit_runtime_metrics("read_from_s3_and_return_input")
    def read_from_s3_and_return_input(self, credentials, s3_bucket, path):
        return read_from_s3_and_return_input(
            self.aws_client_factory,
            credentials,
            s3_bucket,
            path
        )

    @run_on_executor
    @emit_runtime_metrics("read_from_s3")
    def read_from_s3(self, credentials, s3_bucket, path):
        return read_from_s3(
            self.aws_client_factory,
            credentials,
            s3_bucket,
            path
        )

    @staticmethod
    @run_on_executor
    @emit_runtime_metrics("bulk_s3_delete")
    def bulk_s3_delete(self, credentials, s3_bucket, s3_path_list):
        return bulk_s3_delete(
            self.aws_client_factory,
            credentials,
            s3_bucket,
            s3_path_list
        )

    @run_on_executor
    @emit_runtime_metrics("get_s3_pipeline_execution_logs")
    def get_s3_pipeline_execution_logs(self, credentials, s3_prefix, max_results):
        return get_s3_pipeline_execution_logs(
            self.aws_client_factory,
            credentials,
            s3_prefix,
            max_results
        )

    @run_on_executor
    @emit_runtime_metrics("get_build_packages")
    def get_build_packages(self, credentials, s3_prefix, max_results):
        return get_build_packages(
            self.aws_client_factory,
            credentials,
            s3_prefix,
            max_results
        )

    @run_on_executor
    @emit_runtime_metrics("get_s3_list_from_prefix")
    def get_s3_list_from_prefix(self, credentials, s3_bucket, s3_prefix, continuation_token, start_after):
        return get_s3_list_from_prefix(
            self.aws_client_factory,
            credentials,
            s3_bucket,
            s3_prefix,
            continuation_token,
            start_after
        )

    @run_on_executor
    @emit_runtime_metrics("get_s3_pipeline_execution_ids")
    def get_s3_pipeline_execution_ids(self, credentials, timestamp_prefix, max_results, continuation_token):
        return get_s3_pipeline_execution_ids(
            self.aws_client_factory,
            credentials,
            timestamp_prefix,
            max_results,
            continuation_token
        )

    @run_on_executor
    @emit_runtime_metrics("get_s3_pipeline_timestamp_prefixes")
    def get_s3_pipeline_timestamp_prefixes(self, credentials, project_id, max_results, continuation_token):
        return get_s3_pipeline_timestamp_prefixes(
            self.aws_client_factory,
            credentials,
            project_id,
            max_results,
            continuation_token
        )

    @run_on_executor
    @emit_runtime_metrics("get_aws_lambda_existence_info")
    def get_aws_lambda_existence_info(self, credentials, _id, _type, lambda_name):
        return get_aws_lambda_existence_info(self.aws_client_factory, credentials, _id, _type, lambda_name)

    @run_on_executor
    @emit_runtime_metrics("get_lambda_cloudwatch_logs")
    def get_lambda_cloudwatch_logs(self, credentials, log_group_name, stream_id):
        return get_lambda_cloudwatch_logs(self.aws_client_factory, credentials, log_group_name, stream_id)

    @run_on_executor
    @emit_runtime_metrics("get_cloudwatch_existence_info")
    def get_cloudwatch_existence_info(self, credentials, _id, _type, name):
        return get_cloudwatch_existence_info(self.aws_client_factory, credentials, _id, _type, name)

    @run_on_executor
    @emit_runtime_metrics("get_sqs_existence_info")
    def get_sqs_existence_info(self, credentials, _id, _type, name):
        return get_sqs_existence_info(self.aws_client_factory, credentials, _id, _type, name)

    @run_on_executor
    @emit_runtime_metrics("get_sns_existence_info")
    def get_sns_existence_info(self, credentials, _id, _type, name):
        return get_sns_existence_info(self.aws_client_factory, credentials, _id, _type, name)

    @run_on_executor
    @emit_runtime_metrics("create_rest_api")
    def create_rest_api(self, credentials, name, description, version):
        return create_rest_api(
            self.aws_client_factory,
            credentials,
            name,
            description,
            version
        )

    @run_on_executor
    @emit_runtime_metrics("deploy_api_gateway_to_stage")
    def deploy_api_gateway_to_stage(self, credentials, rest_api_id, stage_name):
        return deploy_api_gateway_to_stage(
            self.aws_client_factory,
            credentials,
            rest_api_id,
            stage_name
        )

    @run_on_executor
    @emit_runtime_metrics("create_resource")
    def create_resource(self, credentials, rest_api_id, parent_id, path_part):
        return create_resource(
            self.aws_client_factory,
            credentials,
            rest_api_id,
            parent_id,
            path_part
        )

    @run_on_executor
    @emit_runtime_metrics("create_method")
    def create_method(self, credentials, method_name, rest_api_id, resource_id, http_method, api_key_required):
        return create_method(
            self.aws_client_factory,
            credentials,
            method_name,
            rest_api_id,
            resource_id,
            http_method,
            api_key_required
        )

    @run_on_executor
    @emit_runtime_metrics("clean_lambda_iam_policies")
    def clean_lambda_iam_policies(self, credentials, lambda_name):
        return clean_lambda_iam_policies(
            self.aws_client_factory,
            credentials,
            lambda_name
        )

    @run_on_executor
    @emit_runtime_metrics("add_integration_response")
    def add_integration_response(self, credentials, rest_api_id, resource_id, http_method, lambda_name):
        return add_integration_response(
            self.aws_client_factory,
            credentials,
            rest_api_id,
            resource_id,
            http_method,
            lambda_name
        )

    @run_on_executor
    @emit_runtime_metrics("link_api_method_to_lambda")
    def link_api_method_to_lambda(self, credentials, rest_api_id, resource_id, http_method, api_path, lambda_name):
        return link_api_method_to_lambda(
            self.aws_client_factory,
            credentials,
            rest_api_id,
            resource_id,
            http_method,
            api_path,
            lambda_name
        )
