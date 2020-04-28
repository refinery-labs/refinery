from initiate_database import *
import json


class TaskLock(Base):
    """
    Locks to be used by coroutine tasks to prevent multiple, simultaneous invocations.
    Each lock has a time created which should cause the lock to be auto released after some time has passed.
    """
    __tablename__ = "task_locks"

    # The corresponding task identifier for the given task type
    task_id = Column(Text(), primary_key=True)

    # Whether or not this task lock is currently locked
    locked = Column(Boolean())

    # A future time when this lock will
    expiry = Column(DateTime())

    def __init__(self, task_id, expiry, locked=False):
        self.task_id = task_id
        self.expiry = expiry
        self.locked = locked

    def to_dict(self):
        exposed_attributes = [
            "task_id",
            "locked",
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
        return self.task_id
