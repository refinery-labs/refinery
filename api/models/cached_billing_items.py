from initiate_database import *
import json
import uuid
import time


class CachedBillingItem(Base):
    """
    This is a single line item pulled from AWS billing.

    Note that we do NOT stored the marked-up values for billing.
    The data pulled from the database must be marked up before
    being shown to the user.
    """
    __tablename__ = "cached_billing_items"

    id = Column(
        CHAR(36),
        primary_key=True
    )

    # Name of the service line
    service_name = Column(Text())

    # Currency unit
    unit = Column(Text())

    # Total billing amount stored as a string to
    # avoid any database fuckery around precision
    total = Column(Text())

    # Parent billing collection this item belongs to
    billing_collection_id = Column(
        CHAR(36),
        ForeignKey(
            "cached_billing_collections.id"
        )
    )
    billing_collection = relationship(
        "CachedBillingCollection",
        back_populates="billing_items"
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
