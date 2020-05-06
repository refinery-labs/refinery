import time

from psycopg2.extensions import JSONB
from sqlalchemy import Index, TEXT
from initiate_database import *
import json
import uuid

from models.model_exceptions import InvalidModelCreationError

REQUIRED_JSON_ATTRIBUTES = [
    'created_at',
    'description',
    'full_name',
    'html_url',
    'id',
    'private',
    'pushed_at',
    'updated_at',
    'url'
]


class GitRepoDataRecordsModel(Base):
    """
    Refinery-associated Git Repos live here, and their associated configuration + ownership information
    """
    __tablename__ = "git_repo_data_records"

    id = Column(
        TEXT(),
        primary_key=True
    )

    parent_git_repo_id = Column(
        TEXT(),
        ForeignKey('git_repos.id'),
        nullable=False
    )

    parent_git_repo = relationship(
        "GitRepoModel",
        back_populates="git_repo_data_records"
    )

    description = Column(
        TEXT()
    )

    """
    This ID is given to us by Github.
    """
    github_repo_id = Column(
        Integer(),
        nullable=False
    )

    name = Column(
        TEXT(),
        nullable=False
    )

    private = Column(
        Boolean(),
        nullable=False
    )

    raw_json = Column(
        JSONB(),
        nullable=False
    )

    repo_uri = Column(
        TEXT(),
        nullable=False
    )

    repo_uri_html = Column(
        TEXT(),
        nullable=False
    )

    """
    Entries are sorted by timestamp, with the latest value being the value read.
    """
    timestamp = Column(
        Integer(),
        nullable=False
    )

    def __init__(self, parent_git_repo_id, raw_json, parsed_json=None):
        if parent_git_repo_id is None or parent_git_repo_id is "":
            raise InvalidModelCreationError("Must provide 'parent_git_repo_id' when creating git repo data")

        if raw_json is None:
            raise InvalidModelCreationError("Must provide 'raw_json' when creating git repo data")

        for required_key in REQUIRED_JSON_ATTRIBUTES:
            if required_key not in raw_json:
                raise InvalidModelCreationError("Missing key '" + required_key + "' in raw_json data")

        if parsed_json is None:
            parsed_json = json.loads(raw_json)

        # Manually map over fields from the JSON
        self.description = parsed_json['description']
        self.created_at = parsed_json['created_at']
        self.github_repo_id = parsed_json['id']
        self.name = parsed_json['full_name']
        self.private = parsed_json['private']
        self.pushed_at = parsed_json['pushed_at']
        self.repo_uri = parsed_json['url']
        self.repo_uri_html = parsed_json['html_url']
        self.updated_at = parsed_json['updated_at']

        # Keep a raw copy
        self.raw_json = raw_json

        self.parent_git_repo_id = str(parent_git_repo_id)

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


Index(
    'idx_git_repo_data_record__git_repo_id__timestamp',
    GitRepoDataRecordsModel.parent_git_repo_id,
    GitRepoDataRecordsModel.timestamp,
    unique=True
)
