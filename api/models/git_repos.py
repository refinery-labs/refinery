import time

from sqlalchemy import Index, TEXT
from initiate_database import *
import json
import uuid

from models.model_exceptions import InvalidModelCreationError


class GitRepoModel(Base):
    """
    Refinery-associated Git Repos live here, and their associated configuration + ownership information
    """
    __tablename__ = "git_repos"

    id = Column(
        TEXT(),
        primary_key=True
    )

    date_added = Column(Integer(), nullable=False)

    name = Column(TEXT(), nullable=False)
    description = Column(TEXT(), nullable=False)

    # Parent organization the user belongs to
    organization_id = Column(
        TEXT(),
        ForeignKey(
            "organizations.id"
        ),
        nullable=False
    )

    def __init__(self, organization_id, name, description):
        if organization_id is None or organization_id is "":
            raise InvalidModelCreationError("Must provide 'organization_id' when creating git repo")

        if name is None or name is "":
            raise InvalidModelCreationError("Must provide 'name' when creating git repo")

        if description is None or description is "":
            raise InvalidModelCreationError("Must provide 'description' when creating git repo")

        self.organization_id = str(organization_id)

        self.name = str(name)
        self.description = str(description)

        self.id = str(uuid.uuid4())

        self.date_added = int(time.time())

    def to_dict(self):
        exposed_attributes = [
            "id",
            "description",
            "name",
            "organization_id",
            "date_added"
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


Index('idx_git_repo__organization', GitRepoModel.organization_id, GitRepoModel.id, unique=True)
