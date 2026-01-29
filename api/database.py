"""Database configuration and session management."""

import os
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

_SESSION_FACTORY: sessionmaker[Session] | None = None
_SESSION_ENGINE: Engine | None = None


# Base class for models
class Base(DeclarativeBase):
    pass


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Context manager for getting database sessions with automatic rollback on errors.
    """
    session_factory = _get_session_factory()
    db = session_factory()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables."""
    # Import all models to register them with SQLAlchemy
    # This must happen before create_all() is called
    from api.chats import chat_models  # noqa: F401
    from api.instruments import instrument_models  # noqa: F401
    from api.loops import loop_models  # noqa: F401
    from api.midi import midi_models  # noqa: F401
    from api.songs import song_models  # noqa: F401
    from api.tracks import track_models  # noqa: F401
    from api.users import user_models  # noqa: F401

    Base.metadata.create_all(bind=_get_engine())


def _get_engine() -> Engine:
    global _SESSION_ENGINE

    if _SESSION_ENGINE is None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL is required")

        _SESSION_ENGINE = create_engine(
            database_url,
            echo=False,  # Set to True for SQL query logging
            pool_pre_ping=True,  # Verify connections before using them
            pool_size=5,  # Connection pool size
            max_overflow=10,  # Maximum overflow connections
        )

    return _SESSION_ENGINE


def _get_session_factory() -> sessionmaker[Session]:
    global _SESSION_FACTORY

    if _SESSION_FACTORY is None:
        database_url = os.getenv("DATABASE_URL")

        if not database_url:
            raise ValueError("DATABASE_URL is required")

        _SESSION_FACTORY = sessionmaker(autocommit=False, autoflush=False, bind=_get_engine())

    return _SESSION_FACTORY
