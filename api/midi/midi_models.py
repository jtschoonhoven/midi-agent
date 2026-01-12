"""SQLAlchemy models for conversation storage."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class ConversationMessage(Base):
    """Stores individual messages in a conversation thread."""

    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    thread_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Store the generation request parameters
    plan_model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    generate_model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    key: Mapped[str | None] = mapped_column(String(5), nullable=True)
    bpm: Mapped[int | None] = mapped_column(nullable=True)
    time_signature: Mapped[str | None] = mapped_column(String(5), nullable=True)
    measures: Mapped[int | None] = mapped_column(nullable=True)

    # Store the assistant's response data (plan + MIDI events)
    plan_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    midi_events: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<ConversationMessage(id={self.id}, thread_id={self.thread_id}, role={self.role})>"


def store_user_message(
    db,
    user_id: UUID,
    thread_id: UUID,
    prompt: str,
    plan_model: str,
    generate_model: str,
    key: str | None,
    bpm: int | None,
    time_signature: str | None,
    measures: int | None,
) -> ConversationMessage:
    """Store a user message in the database."""
    message = ConversationMessage(
        user_id=str(user_id),
        thread_id=str(thread_id),
        role="user",
        content=prompt,
        plan_model=plan_model,
        generate_model=generate_model,
        key=key,
        bpm=bpm,
        time_signature=time_signature,
        measures=measures,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def store_assistant_message(
    db,
    user_id: UUID,
    thread_id: UUID,
    content: str,
    plan_data: dict[str, Any],
    midi_events: list[dict[str, Any]],
) -> ConversationMessage:
    """Store an assistant response in the database."""
    message = ConversationMessage(
        user_id=str(user_id),
        thread_id=str(thread_id),
        role="assistant",
        content=content,
        plan_data=plan_data,
        midi_events=midi_events,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_conversation_history(db, user_id: UUID, thread_id: UUID) -> list[ConversationMessage]:
    """Retrieve all messages for a given user and thread, ordered by creation time."""
    return (
        db.query(ConversationMessage)
        .filter(
            ConversationMessage.user_id == str(user_id),
            ConversationMessage.thread_id == str(thread_id),
        )
        .order_by(ConversationMessage.created_at.asc())
        .all()
    )
