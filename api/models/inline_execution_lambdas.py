from initiate_database import *
import uuid
import time


class InlineExecutionLambda(Base):
    __tablename__ = "inline_execution_lambdas"

    id = Column(Text(), primary_key=True)

    # The unique key identifying this Lambda, this consists of the following:
    # * The language name
    # * Ordered list of libraries
    # * Timeout
    # * Memory
    # * Environment variables
    # * Layers
    # All of the above encoded as JSON and hashed with SHA256
    # If any of these change then we have to create a whole new Lambda. This actually
    # takes as much time as just updating the existing Lambda due to the way AWS works
    # in the background.
    unique_hash_key = Column(Text())

    # The ARN of the Lambda, used for deleting it/referencing it
    arn = Column(Text())

    # The total size of the Lambda.
    # Important for computing if we're close to the
    # 75GB storage limit in AWS
    size = Column(Integer())

    # Last run time, this is used to do more intelligent garbage
    last_used_timestamp = Column(Integer())

    timestamp = Column(Integer())

    # AWS Account this Lambda was deployed to.
    aws_account_id = Column(
        CHAR(36),
        ForeignKey(
            "aws_accounts.id"
        )
    )
    aws_account = relationship(
        "AWSAccount",
        back_populates="inline_execution_lambdas"
    )

    def __init__(self):
        self.id = str(uuid.uuid4())
        self.timestamp = int(time.time())
        self.last_used_timestamp = int(time.time())

    def __str__(self):
        return self.id

    def to_dict(self):
        exposed_attributes = [
            "id",
            "unique_hash_key",
            "arn",
            "size",
            "last_used_timestamp",
            "timestamp"
        ]

        return_dict = {}

        for attribute in exposed_attributes:
            return_dict[attribute] = getattr(self, attribute)

        return return_dict
