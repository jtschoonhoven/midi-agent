"""SQLAlchemy models for loops."""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from api.database import Base
from api.loops import loop_schemas
from api.midi.midi_models import MidiEvent

if TYPE_CHECKING:
    from api.chats.chat_models import ChatMessage
    from api.loops.loop_schemas import LoopDetailResponse, LoopResponse
    from api.tracks.track_models import MidiTrack


class MidiLoop(Base):
    """Stores MIDI loop information."""

    __tablename__ = "midi_loops"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    offset: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # In measures
    measures: Mapped[int] = mapped_column(Integer, nullable=False)
    extend_measures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    midi_events: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    track_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("midi_tracks.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    @validates("midi_events")
    def validate_midi_events(self, _key: str, value: list[dict[str, Any] | MidiEvent]) -> list[dict[str, Any]]:
        """Validate and serialize midi_events to dicts for JSON storage."""
        result: list[dict[str, Any]] = []
        for event in value:
            if isinstance(event, MidiEvent):
                result.append(event.model_dump())
            else:
                # Validate dict conforms to MidiEvent schema, then store as dict
                MidiEvent.model_validate(event)
                result.append(event)
        return result

    # Relationships
    track: Mapped["MidiTrack"] = relationship("MidiTrack", back_populates="loops")  # pyright: ignore[reportUndefinedVariable]
    chat_messages: Mapped[list["ChatMessage"]] = relationship(  # pyright: ignore[reportUndefinedVariable]
        "ChatMessage", back_populates="loop", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<MidiLoop(id={self.id}, offset={self.offset}, measures={self.measures}, extend_measures={self.extend_measures})>"

    def to_response(self) -> "LoopResponse":
        return loop_schemas.LoopResponse(
            id=str(self.id),
            offset=self.offset,
            measures=self.measures,
            extend_measures=self.extend_measures,
            midi_events=self.midi_events,
            track_id=str(self.track_id),
            created_at=self.created_at.isoformat(),
            updated_at=self.updated_at.isoformat(),
        )

    def to_detail_response(self) -> "LoopDetailResponse":
        return loop_schemas.LoopDetailResponse(
            id=str(self.id),
            offset=self.offset,
            measures=self.measures,
            extend_measures=self.extend_measures,
            midi_events=self.midi_events,
            track_id=str(self.track_id),
            created_at=self.created_at.isoformat(),
            updated_at=self.updated_at.isoformat(),
            chats=[chat.to_response() for chat in self.chat_messages],
        )
