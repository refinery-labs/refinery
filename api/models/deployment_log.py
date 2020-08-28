from .initiate_database import *
from datetime import datetime
import uuid


class DeploymentLog(Base):
    __tablename__ = "deployment_log"

    id = Column(CHAR(36), primary_key=True)
    # No need for constraints or references for these values as they're only
    # used for logging purposes.
    org_id = Column(CHAR(36))
    timestamp = Column(DateTime())

    def __init__(self):
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.now()

    def __str__(self):
        return self.id
