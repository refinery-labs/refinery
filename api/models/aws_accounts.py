from .initiate_database import *

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from models import CachedBillingCollection, Deployment, InlineExecutionLambda, TerraformStateVersion

import json
import uuid
import time


class AWSAccount(Base):
    __tablename__ = "aws_accounts"

    id = Column(
        CHAR(36),
        primary_key=True
    )

    # Label for the AWS account
    # Leave blank for now until we support multiple
    # AWS accounts.
    account_label = Column(Text())

    # AWS account ID
    account_id = Column(
        Text(),
        unique=True
    )

    # AWS region
    region = Column(Text())

    # The account status, this can be any of the followin:
    # CREATED: This means the account has been created but
    # not-yet set up via Terraform.
    # AVAILABLE: The AWS account has been set up via Terraform
    # and is ready to be used.
    # IN_USE: The account is currently being used by a customer.
    # NEEDS_CLOSING: The AWS account is no longer used and
    # needs to be manually closed.
    # CORRUPT: The AWS account is in a broken state due to an
    # CLOSED: The AWS account has been closed.
    # issue with the Terraform setup/provisioning.
    aws_account_status = Column(Text())

    # S3 bucket suffix, used to generate the full
    # bucket names for sub-accounts
    s3_bucket_suffix = Column(Text())

    # AWS account email - just useful
    aws_account_email = Column(Text())

    # AWS IAM Console Admin username
    iam_admin_username = Column(Text())

    # AWS IAM Console Admin password
    iam_admin_password = Column(Text())

    # Redis hostname
    redis_hostname = Column(Text())

    # Redis password
    redis_password = Column(Text())

    # Redis port
    redis_port = Column(BigInteger())

    # Redis secret prefix
    redis_secret_prefix = Column(Text())

    # Terraform latest state
    terraform_state = Column(Text())

    # The SSH public key for customer operations
    ssh_public_key = Column(Text())

    # The SSH private key for customer operations
    ssh_private_key = Column(Text())

    # The AWS account type, which can be any of the following:
    # MANAGED || THIRDPARTY
    # MANAGED is for sub-accounts that we manage
    # THIRDPARTY is for third-party AWS accounts we don't manage.
    account_type = Column(Text())

    timestamp = Column(Integer())

    # Parent organization the AWS account belongs to
    organization_id = Column(
        CHAR(36),
        ForeignKey(
            "organizations.id"
        )
    )

    # Deployments this AWS account is associated with
    deployments = relationship(
        "Deployment",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    # The cached billing collections for this AWS account
    cached_billing_collections = relationship(
        "CachedBillingCollection",
        back_populates="aws_account",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    # Inline execution Lambdas
    inline_execution_lambdas = relationship(
        "InlineExecutionLambda",
        back_populates="aws_account",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    # Child users to the organization
    terraform_state_versions = relationship(
        "TerraformStateVersion",
        back_populates="aws_account",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    def __init__(self):
        self.id = str(uuid.uuid4())
        self.timestamp = int(time.time())

    def to_dict(self):
        exposed_attributes = [
            "id",
            "account_label",
            "account_id",
            "region",
            "s3_bucket_suffix",
            "iam_admin_username",
            "iam_admin_password",
            "redis_hostname",
            "redis_password",
            "redis_port",
            "redis_secret_prefix",
            "account_type",
            "aws_account_status",
            "terraform_state",
            "timestamp"
        ]

        json_attributes = []
        return_dict = {}

        for attribute in exposed_attributes:
            if attribute in json_attributes:
                return_dict[attribute] = json.loads(
                    getattr(self, attribute)
                )
            else:
                return_dict[attribute] = getattr(self, attribute)

        # Generate S3 packages and logging bucket values
        return_dict["lambda_packages_bucket"] = "refinery-lambda-build-packages-" + self.s3_bucket_suffix
        return_dict["logs_bucket"] = "refinery-lambda-logging-" + self.s3_bucket_suffix

        return return_dict

    def __str__(self):
        return self.id
