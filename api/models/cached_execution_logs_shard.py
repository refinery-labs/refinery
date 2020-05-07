from .initiate_database import *
from .projects import Project
import uuid
import time


class CachedExecutionLogsShard(Base):
    __tablename__ = "cached_execution_logs_shards"

    id = Column(
        CHAR(36),
        primary_key=True
    )

    # The date shard this refers to
    # e.g. "dt=2019-07-15-13-35"
    date_shard = Column(
        Text(),
        index=True
    )

    """
    # All of the cached data for a given shard (e.g. "dt=2019-07-15-13-35")
    [
        {
            "arn": "arn:aws:lambda:us-west-2:532121572788:function:Untitled_Code_Block_RFNItzJNn2",
            "count": "1",
            "dt": "2019-07-15-13-35",
            "execution_pipeline_id": "46b0fdd3-266d-4c6f-af7c-79198a112e96",
            "function_name": "Untitled_Code_Block_RFNItzJNn2",
            "log_id": "22e4625e-46d1-401a-b935-bcde17f8b667",
            "project_id": "08757409-4bc8-4a29-ade7-371b1a46f99e",
            "timestamp": 1563197795,
            "type": "SUCCESS"
        }
        {
            "arn": "arn:aws:lambda:us-west-2:532121572788:function:Untitled_Code_Block_RFNItzJNn3",
            "count": "1",
            "dt": "2019-07-15-13-35",
            "execution_pipeline_id": "46b0fdd3-266d-4c6f-af7c-79198a112e96",
            "function_name": "Untitled_Code_Block_RFNItzJNn3",
            "log_id": "40b02027-c856-4d2b-bd63-c62f300944e5",
            "project_id": "08757409-4bc8-4a29-ade7-371b1a46f99e",
            "timestamp": 1563197795,
            "type": "SUCCESS"
        }
    ]
    """
    shard_data = Column(JSON())

    # Project ID these logs are related to
    project_id = Column(
        CHAR(36),
        ForeignKey(Project.id),
        primary_key=True
    )

    timestamp = Column(Integer())

    def __init__(self):
        self.id = str(uuid.uuid4())
        self.timestamp = int(time.time())

    def to_dict(self):
        exposed_attributes = [
            "id",
            "date_shard",
            "shard_data",
            "project_id",
            "timestamp"
        ]

        return_dict = {}

        for attribute in exposed_attributes:
            return_dict[attribute] = getattr(self, attribute)

        return return_dict

    def __str__(self):
        return self.id
