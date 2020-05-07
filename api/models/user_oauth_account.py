from data_types.oauth_providers import OAuthProvider
from sqlalchemy import Enum, Index, TEXT
from initiate_database import *
import json
import uuid

from models.model_exceptions import InvalidModelCreationError


class UserOAuthAccountModel(Base):
    """
    Stores information about users that have authenticated via OAuth.
    """
    __tablename__ = "user_oauth_accounts"

    id = Column(
        TEXT(),
        primary_key=True
    )

    provider = Column(Enum(OAuthProvider), nullable=False)

    # Parent organization the user belongs to
    user_id = Column(
        TEXT(),
        ForeignKey(
            "users.id"
        ),
        nullable=False
    )

    # Unique identifier provided by the OAuth provider.
    # We use this to match up the OAuth data received against a specific user.
    provider_unique_id = Column(
        TEXT(),
        nullable=False
    )

    # One user can have many OAuth data records
    oauth_data_records = relationship(
        "UserOAuthDataRecordModel",
        lazy="dynamic",
        # When a user is deleted all oauth tokens should
        # be deleted as well.
        cascade="all, delete-orphan",
        backref="user_oauth_accounts"
    )

    def __init__(self, provider, provider_unique_id, user_id):
        if provider is None or provider is "":
            raise InvalidModelCreationError("Must provide 'provider' when creating OAuth account")

        if user_id is None or user_id is "":
            raise InvalidModelCreationError("Must provide 'user_id' when creating OAuth account")

        self.provider = str(provider)

        self.id = str(uuid.uuid4())

        self.provider_unique_id = str(provider_unique_id)

        self.user_id = str(user_id)

    def to_dict(self):
        exposed_attributes = [
            "id",
            "provider",
            "user_id"
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


Index('idx_provider__user', UserOAuthAccountModel.provider, UserOAuthAccountModel.user_id, unique=True)
Index(
    'idx_provider__provider_unique_id',
    UserOAuthAccountModel.provider,
    UserOAuthAccountModel.provider_unique_id,
    unique=True
)
