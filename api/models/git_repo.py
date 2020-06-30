import time

from sqlalchemy import Index, TEXT
from .initiate_database import *
import json
import uuid

from models.model_exceptions import InvalidModelCreationError

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from models import GitRepoDataRecordsModel, Organization


class GitRepoModel(Base):
    """
    Refinery-associated Git Repos live here, and their associated configuration + ownership information
    """
    __tablename__ = "git_repos"

    id = Column(
        TEXT(),
        primary_key=True
    )

    """
    This ID is used by us to keep track of the data received about a repo.
    """
    repo_data_record_id = Column(
        TEXT(),
        nullable=False
    )

    # One user can have many Git repo data records
    git_repo_data_records = relationship(
        "GitRepoDataRecordsModel",
        lazy="dynamic",
        # When a repo is deleted all repo data should be deleted as well.
        cascade="all, delete-orphan",
        backref="git_repos"
    )

    # Parent organization the repo belongs to
    organization_id = Column(
        TEXT(),
        ForeignKey(
            "organizations.id"
        ),
        nullable=False
    )

    organization = relationship("Organization", back_populates="git_repos")

    def __init__(self, repo_data_record_id, organization_id):
        if organization_id is None or organization_id == "":
            raise InvalidModelCreationError("Must provide 'organization_id' when creating git repo")

        if repo_data_record_id is None or repo_data_record_id == "":
            raise InvalidModelCreationError("Must provide 'repo_data_record_id' when creating git repo")

        self.organization_id = str(organization_id)

        self.repo_data_record_id = str(repo_data_record_id)

        self.id = str(uuid.uuid4())

    def to_dict(self):
        exposed_attributes = [
            "id",
            "organization_id",
            "repo_data_record_id"
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
