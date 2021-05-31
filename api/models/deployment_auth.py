import secrets

from .initiate_database import *
import uuid


class DeploymentAuth(Base):
    __tablename__ = "deployment_auth"

    id = Column(CHAR(36), primary_key=True)

    user_id = Column(
        CHAR(36),
        ForeignKey(
            "users.id"
        )
    )

    secret = Column(Text)

    def __init__(self, user_id):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.secret = secrets.token_urlsafe(32)

    def __str__(self):
        return self.id
