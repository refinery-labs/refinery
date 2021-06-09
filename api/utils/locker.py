import logging
from datetime import datetime, timedelta

import pinject

from models.initiate_database import session_scope
from models.task_locks import TaskLock


log = logging.getLogger(__name__)

__all__ = [
    'Locker',
    'AcquireFailure',
]


class AcquireFailure(Exception):
    pass


def _lock_name(name):
    return f"refinery.{name}"


class LockFactory:
    db_session_maker = None

    @pinject.copy_args_to_public_fields
    def __init__(self, db_session_maker):
        pass

    def lock(self, name, expiry_delta=None):
        if expiry_delta is None:
            expiry_delta = timedelta(minutes=15)

        lock_name = _lock_name(name)
        return Lock(self.db_session_maker, lock_name, expiry_delta)


class Lock:
    def __init__(self, db_session_maker, task_id, expiry_delta):
        self.db_session_maker = db_session_maker
        self.task_id = task_id
        self.expiry_delta = expiry_delta
        self.locked = False

    def _future_expiry(self):
        current_time = datetime.now()
        return current_time + self.expiry_delta

    def _acquire_lock(self, task_lock):
        if task_lock.locked:

            # if the lock has expired, reset the lock an acquire lock
            current_time = datetime.now()
            if current_time > task_lock.expiry:
                task_lock.locked = True
                task_lock.expiry = self._future_expiry()
                return True

            # failed to acquire lock
            return False

        # lock was not locked, locking now
        task_lock.locked = True
        return True

    def _new_lock(self):
        return TaskLock(
            self.task_id,
            self._future_expiry()
        )

    def acquire(self):
        with session_scope(self.db_session_maker) as session:
            task_lock = session.query(TaskLock).filter_by(
                task_id=self.task_id
            ).first()

            if task_lock:
                if self._acquire_lock(task_lock):
                    self.locked = True
                    return True
                return False

            # create a new task lock in the table
            task_lock = self._new_lock()
            session.add(task_lock)

            self.locked = True
        return True

    def release(self):
        # if we were not locked in the first place, do not update db
        if not self.locked:
            print("we are not locked")
            return

        # TODO (cthompson) for some reason session scope doesnt work here...
        session = self.db_session_maker()

        task_lock = session.query(TaskLock).filter_by(
            task_id=self.task_id
        ).first()

        if not task_lock:
            # lock doesn't exit, this is ok if we are releasing
            session.close()
            return

        task_lock.locked = False
        session.commit()
        session.close()

    def __enter__(self):
        if not self.acquire():
            raise AcquireFailure
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    def __del__(self):
        self.release()

