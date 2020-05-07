from .initiate_database import *
import json
import uuid
import time

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from models import AWSAccount


class TerraformStateVersion(Base):
    """
    This is purely for situations where we break something
    (e.g. we lose customer terraform states) and we need to
    revert their terraform state. May also be useful for doing
    some deep-in-the-weeds debugging.

    IMPORTANT: Terraform states are sensitive, they have
    secrets inside of them - treat the data appropriately.
    """
    __tablename__ = "terraform_state_versions"

    id = Column(
        CHAR(36),
        primary_key=True
    )

    # Terraform state contents
    terraform_state = Column(Text())

    # Parent AWS account the state belongs to
    aws_account_id = Column(
        CHAR(36),
        ForeignKey(
            "aws_accounts.id"
        )
    )
    aws_account = relationship(
        "AWSAccount",
        back_populates="terraform_state_versions"
    )

    timestamp = Column(Integer())

    def __init__(self):
        self.id = str(uuid.uuid4())
        self.timestamp = int(time.time())

    def to_dict(self):
        exposed_attributes = [
            "id",
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

        return return_dict

    def __str__(self):
        return self.id
