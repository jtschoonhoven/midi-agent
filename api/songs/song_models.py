"""SQLAlchemy models for songs."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base
from api.songs import song_schemas
from api.songs.song_constants import KEYS, TIME_SIGNATURES
from api.songs.song_types import Key, TimeSignature

if TYPE_CHECKING:
    from api.tracks.track_models import MidiTrack


class MidiSong(Base):
    """Stores MIDI song metadata."""

    __tablename__ = "midi_songs"

    # TODO: When migrating to postgres, use the native UUID type instead of a string
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    bpm: Mapped[int] = mapped_column(Integer, default=120, nullable=False)
    key: Mapped[Key] = mapped_column(Enum(*KEYS), nullable=False)
    time_signature: Mapped[TimeSignature] = mapped_column(Enum(*TIME_SIGNATURES), default="4/4", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    tracks: Mapped[list["MidiTrack"]] = relationship("MidiTrack", back_populates="song", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<MidiSong(id={self.id}, user_id={self.user_id}, title={self.title}, key={self.key}, bpm={self.bpm}, time_signature={self.time_signature})>"

    def to_response(self) -> "song_schemas.SongResponse":
        return song_schemas.SongResponse(
            id=self.id,
            title=self.title,
            bpm=self.bpm,
            key=self.key,
            time_signature=self.time_signature,
            created_at=self.created_at.isoformat(),
            updated_at=self.updated_at.isoformat(),
        )

    def to_detail_response(self) -> "song_schemas.SongDetailResponse":
        return song_schemas.SongDetailResponse(
            id=self.id,
            title=self.title,
            bpm=self.bpm,
            key=self.key,
            time_signature=self.time_signature,
            tracks=[track.to_detail_response() for track in self.tracks],
            created_at=self.created_at.isoformat(),
            updated_at=self.updated_at.isoformat(),
        )
