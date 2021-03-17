import secrets

from .initiate_database import *
import uuid


class DeploymentAuth(Base):
    __tablename__ = "deployment_auth"

    id = Column(CHAR(36), primary_key=True)

    org_id = Column(
        CHAR(36),
        ForeignKey(
            "organizations.id"
        )
    )

    secret = Column(Text)

    def __init__(self, org_id):
        self.id = str(uuid.uuid4())
        self.org_id = org_id
        self.secret = secrets.token_urlsafe(32)

    def __str__(self):
        return self.id
