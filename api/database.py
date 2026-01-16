"""Database configuration and session management."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# SQLite database file location
DATABASE_URL = "sqlite:///./midi_agent.db"

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite
    echo=False,  # Set to True for SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Base class for models
class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database sessions with automatic rollback on errors."""
    db = SessionLocal()
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

    Base.metadata.create_all(bind=engine)
