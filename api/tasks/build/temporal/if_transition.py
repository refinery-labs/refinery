from assistants.decorators import aws_exponential_backoff
from botocore.exceptions import ClientError
from hashlib import sha256
from io import BytesIO
from pyconstants.project_constants import THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME
from tasks.s3 import s3_object_exists
from utils.general import add_file_to_zipfile
from utils.wrapped_aws_functions import lambda_delete_function
from zipfile import ZIP_DEFLATED, ZipFile


LAMBDA_FUNCTION_TEMPLATE = """
def lambda_handler(event, context):
    return_data = event['return_data']
    node_id = event['node_id']
    result = perform(node_id, return_data)

    return json.dumps(result)


def perform(node_id, return_data):
    {expressions}
    raise ValueError('Invalid node uuid')


{transition_functions}
"""


TRANSITION_FUNCTION_TEMPLATE = """
def {fn_name}(return_data):
    return {expression}
"""


BOOL_EXPR_TEMPLATE = """
    {statement} node_id == '{node_id}':
        return {fn_name}(return_data)
"""


class IfTransitionBuilder:
    runtime = "python3.6"
    handler = "lambda_function.lambda_handler"

    def __init__(self, deploy_config, aws_client_factory, credentials):
        self.aws_client_factory = aws_client_factory
        self.credentials = credentials
        self.deploy_config = deploy_config
        self.if_transitions = self.get_if_transitions()

    def get_if_transitions(self):
        relationships = self.deploy_config.get("workflow_relationships", [])
        result = []

        for relationship in relationships:
            transition_type = relationship.get('type')
            expression = relationship.get('expression')
            node = relationship.get('node')

            if transition_type == 'if' and expression and node:
                result.append(relationship)

        return result

    def perform(self):
        zip_data = self.get_zip_data()
        key = self.upload_to_s3(zip_data)
        arn = self.deploy_lambda(key)

        return arn

    def get_zip_data(self):
        if not self.if_transitions:
            return

        package_zip = BytesIO()

        with ZipFile(package_zip, "a", ZIP_DEFLATED) as zip_file_handler:
            add_file_to_zipfile(
                zip_file_handler,
                "lambda_function.py",
                self.lambda_function
            )

        zip_data = package_zip.getvalue()
        package_zip.close()

        return zip_data

    def get_s3_key(self, zip_data):
        shasum = sha256(zip_data).hexdigest()

        return f'if_transition_{shasum}.zip'

    def upload_to_s3(self, zip_data):
        key = self.get_s3_key(zip_data)
        bucket = self.credentials['lambda_packages_bucket']
        s3_client = self.aws_client_factory.get_aws_client(
            "s3",
            self.credentials
        )

        exists = s3_object_exists(
            self.aws_client_factory,
            self.credentials,
            bucket,
            key
        )

        if exists:
            return key

        s3_client.put_object(
            Key=key,
            Bucket=bucket,
            Body=zip_data,
        )

        return key

    @property
    def role(self):
        account_id = str(self.credentials["account_id"])
        account_type = self.credentials["account_type"]

        if account_type == "THIRDPARTY":
            return f"arn:aws:iam::{account_id}:role/{THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME}"
        else:
            return f"arn:aws:iam::{account_id}:role/refinery_default_aws_lambda_role"

    @aws_exponential_backoff(allowedErrors=['ResourceConflictException'])
    def deploy_lambda(self, path):
        lambda_client = self.aws_client_factory.get_aws_client(
            "lambda",
            self.credentials
        )

        try:
            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#Lambda.Client.create_function
            response = lambda_client.create_function(
                FunctionName=path,
                Runtime=self.runtime,
                Role=self.role,
                Handler=self.handler,
                Code={
                    "S3Bucket": self.credentials["lambda_packages_bucket"],
                    "S3Key": path,
                },
                Description="A Lambda deployed by refinery, manages transitions",
                Timeout=int(30),
                Publish=True,
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceConflictException":
                lambda_client = self.aws_client_factory.get_aws_client("lambda", self.credentials)

                # Delete the existing lambda
                delete_response = lambda_delete_function(
                    lambda_client,
                    path
                )

            raise

        return response['FunctionArn']

    @property
    def lambda_function(self):
        expressions = '\n'.join([
            self.get_bool_expr(i, j)
            for i, j in enumerate(self.if_transitions)
        ])
        transition_functions = '\n'.join([
            self.get_transition_fn(i)
            for i in self.if_transitions
        ])

        return LAMBDA_FUNCTION_TEMPLATE.format(
            expressions=expressions,
            transition_functions=transition_functions
        )

    def get_fn_name(self, node_id):
        return "perform_{}".format(node_id.replace('-', '_'))

    def get_transition_fn(self, transition):
        fn_name = self.get_fn_name(transition['node'])
        expression = transition['expression']

        return TRANSITION_FUNCTION_TEMPLATE.format(
            fn_name=fn_name,
            expression=expression
        )

    def get_bool_expr(self, index, transition):
        node_id = transition['node']
        fn_name = self.get_fn_name(node_id)
        statement = 'if' if index == 0 else 'elif'

        return BOOL_EXPR_TEMPLATE.format(
            statement=statement,
            node_id=node_id,
            fn_name=fn_name
        )
