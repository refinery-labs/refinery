import logging
from datetime import datetime, timedelta

from models.task_locks import TaskLock


log = logging.getLogger(__name__)

__all__ = [
    'Locker',
    'AcquireFailure',
]


class AcquireFailure(Exception):
    pass


class Locker:
    def __init__(self, app_name, expiry_delta=None):
        self.app_name = app_name
        self.expiry_delta = expiry_delta

        if self.expiry_delta is None:
            self.expiry_delta = timedelta(minutes=15)

    def _lock_name(self, name):
        if self.app_name is None:
            return name

        return '{}.{}'.format(self.app_name, name)

    def lock(self, session, name):
        lock_name = self._lock_name(name)
        return Lock(session, lock_name, self.expiry_delta)


class Lock:
    def __init__(self, session, task_id, expiry_delta):
        self.session = session
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
                self.session.commit()
                return True

            # failed to acquire lock
            return False

        # lock was not locked, locking now
        task_lock.locked = True
        self.session.commit()
        return True

    def _new_lock(self):
        task_lock = TaskLock(
            self.task_id,
            self._future_expiry(),
            locked=True
        )
        self.session.add(task_lock)
        self.session.commit()

    def acquire(self):
        task_lock = self.session.query(TaskLock).filter_by(
            task_id=self.task_id
        ).first()

        if task_lock:
            if self._acquire_lock(task_lock):
                self.locked = True
                return True
            return False

        # create a new task lock in the table
        self._new_lock()
        self.locked = True
        return True

    def release(self):
        # if we were not locked in the first place, do not update db
        if not self.locked:
            return

        task_lock = self.session.query(TaskLock).filter_by(
            task_id=self.task_id
        ).first()

        if not task_lock:
            # lock doesn't exit, this is ok if we are releasing
            return

        task_lock.locked = False
        self.session.commit()

    def __enter__(self):
        if not self.acquire():
            raise AcquireFailure
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    def __del__(self):
        try:
            self.release()
        except Exception:
            pass
