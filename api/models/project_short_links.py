from .initiate_database import *
import random
import string
import json
import uuid
import time


class ProjectShortLink(Base):
    __tablename__ = "project_short_links"

    id = Column(
        CHAR(36),
        primary_key=True
    )

    # The short ID for the shortlink
    short_id = Column(
        Text(),
        unique=True
    )

    # Project Diagram data
    project_json = Column(JSON())

    timestamp = Column(Integer())

    def __init__(self):
        self.id = str(uuid.uuid4())
        self.short_id = self.get_random_id(12)
        self.timestamp = int(time.time())

    def to_dict(self):
        exposed_attributes = [
            "id",
            "short_id",
            "project_json",
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

    def get_random_id(self, length):
        """
        Returns a cryptographically-random ID so that you can't bruteforce
        the IDs of posted projects. This way you can only get a project if
        someone actually sent the link to you.

        Given an online-bruteforce attack 12 characters lowercase and number
        would take many many centuries to crack.
        """
        return "".join(
            random.SystemRandom().choice(
                string.ascii_lowercase + string.digits
            ) for _ in range(length)
        )
