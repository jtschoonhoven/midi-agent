"""SQLAlchemy models for loops."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class MidiLoop(Base):
    """Stores MIDI loop information."""

    __tablename__ = "midi_loops"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    measures: Mapped[int] = mapped_column(Integer, nullable=False)
    repeat: Mapped[int] = mapped_column(Integer, nullable=False)
    midi_events: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    track_id: Mapped[str] = mapped_column(String(36), ForeignKey("midi_tracks.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    track: Mapped["MidiTrack"] = relationship("MidiTrack", back_populates="loops")
    chat_messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="loop", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<MidiLoop(id={self.id}, title={self.title}, measures={self.measures}, repeat={self.repeat})>"
