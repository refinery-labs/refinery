import json
import time

import uuid

from sqlalchemy import Column, Integer, ForeignKey, Text, Index, TEXT
from sqlalchemy.dialects.postgresql import JSONB

from models.initiate_database import Base
from models.model_exceptions import InvalidModelCreationError


class UserOAuthDataRecordModel(Base):
    """
    This holds the response from any OAuth providers. To be used in the event that we need to retrieve data about a user
    later, but we don't know where the store that information today. The raw data from an OAuth provider is stored on
    the `json_data` column of this table as binary JSON data (PostgreSQL specific data type).
    """
    __tablename__ = "user_oauth_data_records"

    id = Column(
        TEXT(),
        primary_key=True
    )

    oauth_token = Column(Text(), nullable=False)

    # The JSON contents of the OAuth data record
    json_data = Column(JSONB(), nullable=False)

    timestamp = Column(Integer(), nullable=False)

    # Represents the record that was used to fetch this data
    oauth_account_id = Column(
        TEXT(),
        ForeignKey(
            "user_oauth_accounts.id"
        ),
        nullable=False
    )

    def __init__(self, json_data, oauth_token, oauth_account_id):

        if json_data is None or json_data == "":
            raise InvalidModelCreationError("Must provide 'json_data' when creating OAuth account")

        if oauth_token is None or oauth_token == "":
            raise InvalidModelCreationError("Must provide 'oauth_token' when creating OAuth account")

        if oauth_account_id is None or oauth_account_id == "":
            raise InvalidModelCreationError("Must provide 'oauth_account_id' when creating OAuth account")

        self.json_data = str(json_data)
        self.oauth_token = str(oauth_token)
        self.oauth_account_id = str(oauth_account_id)

        self.id = str(uuid.uuid4())
        self.timestamp = int(time.time())

    def to_dict(self):
        exposed_attributes = [
            "json_data",
            "id",
            "timestamp",
            "oauth_account_id"
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
    'idx_oauth_account_id__timestamp',
    UserOAuthDataRecordModel.oauth_account_id,
    UserOAuthDataRecordModel.timestamp.desc()
)
