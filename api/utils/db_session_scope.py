from contextlib import contextmanager


@contextmanager
def session_scope(db_session_maker):
    """Provide a transactional scope around a series of operations."""
    session = db_session_maker()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
