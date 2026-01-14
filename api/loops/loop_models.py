"""SQLAlchemy models for loops."""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base
from api.loops import loop_schemas

if TYPE_CHECKING:
    from api.chats.chat_models import ChatMessage
    from api.loops.loop_schemas import LoopDetailResponse, LoopResponse
    from api.tracks.track_models import MidiTrack


class MidiLoop(Base):
    """Stores MIDI loop information."""

    __tablename__ = "midi_loops"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    offset: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # In measures
    measures: Mapped[int] = mapped_column(Integer, nullable=False)
    repeat: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    midi_events: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    track_id: Mapped[str] = mapped_column(String(36), ForeignKey("midi_tracks.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    track: Mapped["MidiTrack"] = relationship("MidiTrack", back_populates="loops")  # pyright: ignore[reportUndefinedVariable]
    chat_messages: Mapped[list["ChatMessage"]] = relationship(  # pyright: ignore[reportUndefinedVariable]
        "ChatMessage", back_populates="loop", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<MidiLoop(id={self.id}, offset={self.offset}, measures={self.measures}, repeat={self.repeat})>"

    def to_response(self) -> "LoopResponse":
        return loop_schemas.LoopResponse(
            id=self.id,
            offset=self.offset,
            measures=self.measures,
            repeat=self.repeat,
            midi_events=self.midi_events,
            track_id=self.track_id,
            created_at=self.created_at.isoformat(),
            updated_at=self.updated_at.isoformat(),
        )

    def to_detail_response(self) -> "LoopDetailResponse":
        return loop_schemas.LoopDetailResponse(
            id=self.id,
            offset=self.offset,
            measures=self.measures,
            repeat=self.repeat,
            midi_events=self.midi_events,
            track_id=self.track_id,
            created_at=self.created_at.isoformat(),
            updated_at=self.updated_at.isoformat(),
            chats=[chat.to_response() for chat in self.chat_messages],
        )
