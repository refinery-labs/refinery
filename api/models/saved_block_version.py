from initiate_database import *
from saved_block import SavedBlock
import uuid
import time

from sqlalchemy.dialects.postgresql import JSONB


class SavedBlockVersion(Base):
    __tablename__ = "saved_block_versions"

    id = Column(Text(), primary_key=True)
    saved_block_id = Column(
        Text(),
        ForeignKey(SavedBlock.id),
        primary_key=True
    )

    version = Column(
        Integer()
    )

    # deprecated: use block_object_json
    block_object = Column(Text())

    _block_object_json = Column(
        "block_object_json",
        JSONB(astext_type=Text)
    )

    @property
    def block_object_json(self):
        return self._block_object_json

    @block_object_json.setter
    def block_object_json( self, block_json ):
        self._block_object_json = block_json

    @property
    def shared_files(self):
        """
        Returns an empty list by default.
        """
        if self._shared_files is None:
            return []
        return self._shared_files

    @shared_files.setter
    def shared_files(self, value):
        self._shared_files = value

    _shared_files = Column(
        "shared_files",
        JSON()
    )
    shared_files = synonym(
        '_shared_files',
        descriptor=shared_files
    )

    timestamp = Column(Integer())

    def __init__(self):
        self.id = str(uuid.uuid4())
        self.timestamp = int(time.time())

    def __str__(self):
        return self.id
