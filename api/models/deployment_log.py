from .initiate_database import *
from datetime import datetime
import uuid


class DeploymentLog(Base):
    __tablename__ = "deployment_log"

    id = Column(CHAR(36), primary_key=True)
    # No need for constraints or references for these values as they're only
    # used for logging purposes.
    org_id = Column(
        CHAR(36),
        ForeignKey(
            "organizations.id"
        )
    )

   timestamp = Column(DateTime, server_default=func.now())

    def __init__(self):
        self.id = str(uuid.uuid4())

    def __str__(self):
        return self.id
