"""SQLAlchemy models for tracks."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class MidiTrack(Base):
    """Stores MIDI track information."""

    __tablename__ = "midi_tracks"
    __table_args__ = (CheckConstraint("midi_channel > 0", name="midi_channel_positive"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    song_id: Mapped[str] = mapped_column(String(36), ForeignKey("midi_songs.id"), nullable=False, index=True)
    midi_channel: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    song: Mapped["MidiSong"] = relationship("MidiSong", back_populates="tracks")
    loops: Mapped[list["MidiLoop"]] = relationship("MidiLoop", back_populates="track", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<MidiTrack(id={self.id}, song_id={self.song_id}, midi_channel={self.midi_channel})>"
