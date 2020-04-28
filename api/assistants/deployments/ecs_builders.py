import hashlib

import pinject
import requests
import tornado
import random
import uuid
import time
import io

from tornado.concurrent import run_on_executor, futures
from requests.exceptions import ConnectionError

from pyexceptions.builds import BuildException
from pyconstants.project_constants import EMPTY_ZIP_DATA
from botocore.exceptions import ClientError
from expiringdict import ExpiringDict
from utils.general import logit
from utils.performance_decorators import emit_runtime_metrics

try:
    # for Python 2.x
    from StringIO import StringIO
except ImportError:
    # for Python 3.x
    from io import StringIO

import zipfile

CLUSTER_NAME = "refinery_builders"
TASK_DEFINITION = "refinery_builders_task_family"

# The number of minutes to idle before spinning down
# the ECS task. This is too save costs as ECS charges
# per minute and we're using medium sized instance.
# The longer the idle, the longer it'll remain ready
# for someone to run another compile but the more costly
# it will be. The shorter the idle, the less time it will
# wait to spin down, but the user will encounter slow-startups
# more often.
BUILDER_IDLE_SPIN_DOWN_MINUTES = "15"

"""
Store whether a container is currently being spun up for builds.

This makes it so that if we receive two run commands at the same
time that we won't launch two ECS containers.

{
	"{{AWS_ACCOUNT_ID}}": "IN_PROGRESS" | "{{ECS_CONTAINER_IP}}"
}
"""
ECS_MEM_CACHE = ExpiringDict(
    max_len=1000,
    max_age_seconds=(5 * 60)
)


"""
Generate a build container password. To save us from having to store
more state in the database we repurpose the "iam_admin_username" and
the "iam_admin_password" values.

This is for a number of reasons:
* It is a secret value per user
* It's tied to a specific AWS account (which we want)
* It will be rotated when the regular AWS account IAM account gets rotated (in
that situation, we'd almost certainly want to rotate the container password
as well).
* It's not necessarily secret to the Refinery user themselves (they already have access to it).

We hash the password using SHA512 to protect against the edge case of
a malicious Go package stealing the secret value. If we didn't do this
hashing then a malicious Go package could read the environment variable
from the container and use it to potentially authenticate as the user in
AWS. Now if a Go package stole the value, they'd just have access to the
build container...which they would already have.

SHA512 is sufficient here because we generate an extremely entropic
cryptographically-secure password for the IAM password. We could use bcrypt
but we'll be doing this fairly often, so I want to be gentle to the server.
"""


def get_builder_shared_secret(credentials):
    hash_material = credentials["iam_admin_username"] + ":" + credentials["iam_admin_password"]
    return hashlib.sha512(
        hash_material
    ).hexdigest()


class AwsEcsManager(object):
    """
    This handles the logic for spinning up build tasks using ECS.

    The build server will automatically shut itself off after 60
    minutes of idling for cost savings.
    """

    aws_client_factory = None

    @pinject.copy_args_to_public_fields
    def __init__(self, aws_client_factory, loop=None):
        self.executor = futures.ThreadPoolExecutor(10)
        self.loop = loop or tornado.ioloop.IOLoop.current()

    @staticmethod
    def _get_security_group_id_by_group_name(aws_client_factory, credentials, security_group_name):
        ec2_client = aws_client_factory.get_aws_client(
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

        for security_group_metadata in response["SecurityGroups"]:
            return security_group_metadata["GroupId"]

        return None

    @staticmethod
    def _get_all_subnets(aws_client_factory, credentials):
        ec2_client = aws_client_factory.get_aws_client(
            "ec2",
            credentials
        )

        response = ec2_client.describe_subnets(
            MaxResults=1000
        )

        subnet_ids = []

        if not "Subnets" in response:
            return subnet_ids

        for subnet_metadata in response["Subnets"]:
            subnet_ids.append(
                subnet_metadata["SubnetId"]
            )

        return subnet_ids

    @staticmethod
    def _enable_long_form_arns(aws_client_factory, credentials):
        """
        This code will be irrelevant as of 2019-12-31 23:59:59 -0800

        However, before then we'll need to have this to enabled long-form
        ARNs for tasks and services since AWS is going through a migration.
        """
        ecs_client = aws_client_factory.get_aws_client(
            "ecs",
            credentials
        )

        print("Enabling long form ARN format for tasks...")
        response = ecs_client.put_account_setting_default(
            name="taskLongArnFormat",
            value="enabled"
        )

    @staticmethod
    def _start_builder_ecs_task(aws_client_factory, credentials):
        ecs_client = aws_client_factory.get_aws_client(
            "ecs",
            credentials
        )

        subnet_ids = AwsEcsManager._get_all_subnets(aws_client_factory, credentials)
        security_group_id = AwsEcsManager._get_security_group_id_by_group_name(
            aws_client_factory,
            credentials,
            "refinery_builders_security_group"
        )

        if len(subnet_ids) == 0:
            raise Exception("No subnets exist! Connect start a task without a subnet!")

        builder_agent_secret = get_builder_shared_secret(credentials)

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
                                            "value": builder_agent_secret
                                },
                                {
                                    "name": "MAX_IDLE_TIME",
                                            "value": BUILDER_IDLE_SPIN_DOWN_MINUTES
                                }
                            ]
                        }
                    ]
                }
            )
        except ClientError as e:
            error_message = e.response["Error"]["Message"]

            if error_message == "Long arn format must be enabled for ECS managed tags.":
                AwsEcsManager._enable_long_form_arns(aws_client_factory, credentials)
                return AwsEcsManager._start_builder_ecs_task(aws_client_factory, credentials)

            # If it's not the expected error then re-raise
            raise

        """
		Pull out and return relevant ECS task details
		"""
        return response["tasks"][0]["taskArn"]

    @staticmethod
    def _get_running_task_arns(aws_client_factory, credentials):
        ecs_client = aws_client_factory.get_aws_client(
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

        for task_arn in running_response["taskArns"]:
            task_arns.append(
                task_arn
            )

        for task_arn in pending_response["taskArns"]:
            task_arns.append(
                task_arn
            )

        return task_arns

    @staticmethod
    def _get_tasks_metadata_list(aws_client_factory, credentials, arn_list):
        ecs_client = aws_client_factory.get_aws_client(
            "ecs",
            credentials
        )

        response = ecs_client.describe_tasks(
            cluster=CLUSTER_NAME,
            tasks=arn_list
        )

        if not "tasks" in response:
            return []

        return response["tasks"]

    @staticmethod
    def _get_public_ips_from_private_ip_addresses(aws_client_factory, credentials, private_ip_addresses):
        ec2_client = aws_client_factory.get_aws_client(
            "ec2",
            credentials
        )

        response = None

        remaining_attempts = 20

        while remaining_attempts > 0:
            logit("Querying for public IP address from private IP...")
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

            if "NetworkInterfaces" in response and len(response["NetworkInterfaces"]) > 0:
                break

            time.sleep(1)
            remaining_attempts = remaining_attempts - 1

            if remaining_attempts == 0:
                return []

        ip_addresses = []

        for interface_metadata in response["NetworkInterfaces"]:
            ip_addresses.append(
                interface_metadata["Association"]["PublicIp"]
            )

        return ip_addresses

    @staticmethod
    def _get_cached_data(aws_client_factory, credentials):
        remaining_attempts = 5 * 60

        while remaining_attempts > 0:
            if not credentials["account_id"] in ECS_MEM_CACHE:
                # Expired from cache, let's just kick off another task
                return AwsEcsManager._get_build_container_ips(
                    aws_client_factory,
                    credentials,
                    True
                )

            container_ip = ECS_MEM_CACHE[credentials["account_id"]]

            if container_ip != "IN_PROGRESS":
                return container_ip

            time.sleep(1)

            remaining_attempts = remaining_attempts - 1

        # We tried to wait, let's just launch it ourselves.
        return AwsEcsManager._get_build_container_ips(
            aws_client_factory,
            credentials,
            True,
        )

    @staticmethod
    def _get_build_container_ips(aws_client_factory, credentials, bypass_memory_cache):
        """
        Searchs for an already-running build container.

        If one exists and is running, we use it. Otherwise
        we launch up a new container.

        (The containers will automatically terminate themselves
        after not doing any work for a given period of time).
        """
        if not bypass_memory_cache and credentials["account_id"] in ECS_MEM_CACHE:
            return AwsEcsManager._get_cached_data(aws_client_factory, credentials)

        # Set "IN_PROGRESS" for the ECS memory cache so we
        # don't ever kick off two relatively expensive ECS tasks.
        ECS_MEM_CACHE[credentials["account_id"]] = "IN_PROGRESS"

        logit("Pulling all running containers IPs...")

        logit("Pulling all existing task ARNs...")

        # First check if we have any already-running containers
        existing_task_arns = AwsEcsManager._get_running_task_arns(
            aws_client_factory,
            credentials
        )

        if len(existing_task_arns) == 0:
            logit("No existing tasks found, starting one and retrying action...")
            AwsEcsManager._start_builder_ecs_task(aws_client_factory, credentials)

            # Eventual consistency so we'll wait a bit
            time.sleep(2)
            return AwsEcsManager._get_build_container_ips(
                aws_client_factory,
                credentials,
                True
            )

        logit("Existing tasks found, pulling metadata for tasks...")

        # Pull the metadata for all running and pending tasks
        task_info_list = AwsEcsManager._get_tasks_metadata_list(
            aws_client_factory,
            credentials,
            existing_task_arns
        )

        build_container_private_ips = []

        for task_info in task_info_list:
            if task_info["lastStatus"] == "RUNNING":
                build_container_private_ips.append(
                    task_info["containers"][0]["networkInterfaces"][0]["privateIpv4Address"]
                )

        if len(build_container_private_ips) == 0:
            logit("No RUNNING build instances found, waiting briefly and retrying action...")
            time.sleep(2)
            return AwsEcsManager._get_build_container_ips(
                aws_client_factory,
                credentials,
                True
            )

        # Exchange interface IDs for interface public IPs
        build_container_instance_ips = AwsEcsManager._get_public_ips_from_private_ip_addresses(
            aws_client_factory,
            credentials,
            build_container_private_ips
        )

        # Add build container IPs to cache
        ECS_MEM_CACHE[credentials["account_id"]] = build_container_instance_ips

        return build_container_instance_ips


class BuilderManager(object):
    """
    This communicates with already-spun-up ECS builder tasks to
    kick off builds and get the results.
    """
    aws_client_factory = None
    aws_cloudwatch_client = None
    logger = None

    @pinject.copy_args_to_public_fields
    def __init__(self, aws_client_factory, aws_cloudwatch_client, logger, loop=None):
        self.executor = futures.ThreadPoolExecutor(10)
        self.loop = loop or tornado.ioloop.IOLoop.current()

    @run_on_executor
    @emit_runtime_metrics("ecs_builders__get_build_container_ip")
    def get_build_container_ip(self, credentials):
        return BuilderManager._get_build_container_ip(
            self.aws_client_factory,
            credentials
        )

    @staticmethod
    def _get_build_container_ip(aws_client_factory, credentials):
        # Get build container IPs
        build_container_ips = AwsEcsManager._get_build_container_ips(
            aws_client_factory,
            credentials,
            False
        )

        # Shuffle IPs so we send build request in a load-balanced way
        random.shuffle(build_container_ips)

        # Grab IP from list of IPs
        return build_container_ips[0]

    @staticmethod
    def _get_go112_zip(aws_client_factory, credentials, lambda_object):
        build_container_ip = BuilderManager._get_build_container_ip(
            aws_client_factory,
            credentials
        )

        go_binary_data = BuilderManager._get_go_compiled_binary(
            credentials,
            build_container_ip,
            lambda_object
        )

        return BuilderManager._get_lambda_package(
            go_binary_data
        )

    @run_on_executor
    @emit_runtime_metrics("ecs_builders__get_go112_binary_s3")
    def get_go112_binary_s3(self, credentials, lambda_object):
        return BuilderManager._get_go112_binary_s3(self.aws_client_factory, credentials, lambda_object)

    @staticmethod
    def _get_go112_binary_s3(aws_client_factory, credentials, lambda_object):
        build_container_ip = BuilderManager._get_build_container_ip(
            aws_client_factory,
            credentials
        )

        try:
            go_binary_data = BuilderManager._get_go_compiled_binary(
                credentials,
                build_container_ip,
                lambda_object
            )
        except ConnectionError as e:
            # This will occur if the task has just spun down.
            # Likely the old IP address of the task is incorrectly cached
            # We'll clear it and try again
            del ECS_MEM_CACHE[credentials["account_id"]]
            return BuilderManager._get_go112_binary_s3(
                aws_client_factory,
                credentials,
                lambda_object
            )

        # Upload binary to S3
        return BuilderManager._upload_binary_to_s3(
            aws_client_factory,
            credentials,
            go_binary_data
        )

    @staticmethod
    def _upload_binary_to_s3(aws_client_factory, credentials, go_binary_data):
        s3_client = aws_client_factory.get_aws_client(
            "s3",
            credentials
        )

        binary_path = "compiled_binaries/" + str(uuid.uuid4())

        s3_response = s3_client.put_object(
            Bucket=credentials["lambda_packages_bucket"],
            Body=go_binary_data,
            Key=binary_path,
            ACL="private"
        )

        return binary_path

    @staticmethod
    def _get_lambda_package(go_binary_data):
        lambda_package_zip = io.BytesIO(EMPTY_ZIP_DATA)

        with zipfile.ZipFile(lambda_package_zip, "a", zipfile.ZIP_DEFLATED) as zip_file_handler:
            info = zipfile.ZipInfo(
                "lambda"
            )
            info.external_attr = 0o777 << 16
            zip_file_handler.writestr(
                info,
                go_binary_data
            )

        lambda_package_zip_data = lambda_package_zip.getvalue()
        lambda_package_zip.close()
        return lambda_package_zip_data

    @staticmethod
    def _get_go_compiled_binary(credentials, build_container_ip, lambda_object):
        headers = {
            "X-Agent-Key": get_builder_shared_secret(credentials),
            "Content-Type": "application/json; charset=UTF-8"
        }

        logit("Sending Go build request to builder task...")
        request_body = {
            "shared_files": lambda_object.shared_files_list,
            "base_code": lambda_object.code,
            "libraries": lambda_object.libraries
        }

        response = requests.post(
            "http://" + build_container_ip + ":2222/api/v1/go/build",
            headers=headers,
            json=request_body
        )

        # Pull header to get the status of the build
        build_status = response.headers.get("X-Compile-Status", None)

        # If this succeeded we're done and can return the final binary.
        if build_status == "SUCCESS":
            return response.content
        elif build_status == "GO_GET_ERROR":
            raise BuildException(
                "An error occurred while running \"go get\", see the build output for more information.",
                response.text
            )
        elif build_status == "GO_BUILD_ERROR":
            raise BuildException(
                "An error occurred while building the Go binary, see the build output for more information.",
                response.text
            )
        elif build_status == "UNKNOWN":
            raise BuildException(
                "An unknown error occurred while compiling your Go binary.",
                response.text
            )

        raise BuildException(
            "An unknown error occurred while building your Go binary.",
            "The Refinery builder agent failed while trying to build your package, please submit this to Refinery support.",
        )
