from sqlalchemy import Index

from .initiate_database import *
import json
import uuid
import time

class StateLog(Base):
    """
    This is for storing logs from the frontend.

    The frontend just shits back some JSON of the
    Vuex state mutations and we can look through them
    at a later time to replay state/etc.
    """
    __tablename__ = "statelogs"

    id = Column(CHAR(36), primary_key=True)

    # ID the frontend uses to track sessions
    session_id = Column(
        Text()
    )

    # The JSON contents of the log
    state = Column(JSON())

    # Parent user the auth token belongs to
    user_id = Column(
        CHAR(36),
        ForeignKey(
            "users.id"
        )
    )

    timestamp = Column(Integer())

    def __init__(self):
        self.id = str(uuid.uuid4())
        self.timestamp = int(time.time())

    def to_dict(self):
        exposed_attributes = [
            "id",
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


Index('ix_statelogs_session_id', StateLog.session_id)
