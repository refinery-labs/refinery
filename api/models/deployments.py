from sqlalchemy import Enum

from data_types.deployment_stages import DeploymentStages
from .initiate_database import *
from .projects import Project
import json
import uuid
import time




class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(CHAR(36), primary_key=True)

    project_id = Column(
        CHAR(36),
        ForeignKey(Project.id),
        primary_key=True
    )

    # AWS Account this deployment was deployed to.
    aws_account_id = Column(
        CHAR(36),
        ForeignKey(
            "aws_accounts.id"
        )
    )

    organization_id = Column(
        CHAR(36),
        ForeignKey(
            "organizations.id"
        )
    )

    stage = Column(Enum(DeploymentStages), nullable=False)

    deployment_json = Column(Text())

    timestamp = Column(Integer())

    def __init__(self, id=None):
        if id is None:
            self.id = str(uuid.uuid4())
        else:
            self.id = id
        self.timestamp = int(time.time())

    def to_dict(self):
        exposed_attributes = [
            "id",
            "project_id",
            "organization_id",
            "deployment_json",
            "timestamp"
        ]

        json_attributes = ["deployment_json"]
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
