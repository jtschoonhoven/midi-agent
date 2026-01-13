"""SQLAlchemy models for songs."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class MidiSong(Base):
    """Stores MIDI song metadata."""

    __tablename__ = "midi_songs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    bpm: Mapped[int] = mapped_column(Integer, nullable=False)
    key: Mapped[str] = mapped_column(
        Enum(
            "Ab",
            "A",
            "A#",
            "Bb",
            "B",
            "C",
            "C#",
            "Db",
            "D",
            "D#",
            "Eb",
            "E",
            "F",
            "F#",
            "Gb",
            "G",
            "G#",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    tracks: Mapped[list["MidiTrack"]] = relationship("MidiTrack", back_populates="song", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<MidiSong(id={self.id}, user_id={self.user_id}, title={self.title}, key={self.key}, bpm={self.bpm})>"
