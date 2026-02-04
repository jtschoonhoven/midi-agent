"""SQLAlchemy models for tracks."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base
from api.instruments.instrument_constants import INSTRUMENT_TYPES
from api.instruments.instrument_types import InstrumentType
from api.tracks import track_schemas
from api.tracks.track_constants import DEFAULT_TRACK_COLOR
from api.tracks.track_types import TrackColor

if TYPE_CHECKING:
    from api.loops.loop_models import MidiLoop
    from api.songs.song_models import MidiSong

DEFAULT_INST: InstrumentType = "piano"


class MidiTrack(Base):
    """Stores MIDI track information."""

    __tablename__ = "midi_tracks"
    __table_args__ = (CheckConstraint("midi_channel > 0", name="midi_channel_positive"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    song_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("midi_songs.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    midi_channel: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    instrument: Mapped[InstrumentType] = mapped_column(
        Enum(*INSTRUMENT_TYPES, name="track_instrument"), default=DEFAULT_INST, nullable=False
    )
    color: Mapped[TrackColor] = mapped_column(String(50), default=DEFAULT_TRACK_COLOR, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    song: Mapped["MidiSong"] = relationship("MidiSong", back_populates="tracks")
    loops: Mapped[list["MidiLoop"]] = relationship("MidiLoop", back_populates="track", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return (
            f"<MidiTrack(id={self.id}, title={self.title}, song_id={self.song_id}, midi_channel={self.midi_channel})>"
        )

    def to_response(self) -> "track_schemas.TrackResponse":
        return track_schemas.TrackResponse(
            id=str(self.id),
            song_id=str(self.song_id),
            title=self.title,
            midi_channel=self.midi_channel,
            instrument=self.instrument,
            color=self.color,
            created_at=self.created_at.isoformat(),
            updated_at=self.updated_at.isoformat(),
        )

    def to_detail_response(self) -> "track_schemas.TrackDetailResponse":
        return track_schemas.TrackDetailResponse(
            id=str(self.id),
            song_id=str(self.song_id),
            title=self.title,
            midi_channel=self.midi_channel,
            instrument=self.instrument,
            color=self.color,
            loops=[loop.to_response() for loop in self.loops],
            created_at=self.created_at.isoformat(),
            updated_at=self.updated_at.isoformat(),
        )
