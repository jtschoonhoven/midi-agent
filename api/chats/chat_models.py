"""SQLAlchemy models for chat messages and conversations."""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from api.database import Base
from api.loops import loop_schemas
from api.midi.midi_models import MidiEvent

if TYPE_CHECKING:
    from api.loops.loop_models import MidiLoop
    from api.loops.loop_schemas import ChatMessageResponse


class ChatMessage(Base):
    """Stores chat messages associated with MIDI loops."""

    __tablename__ = "chat_messages"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    role: Mapped[str] = mapped_column(
        Enum("user", "assistant", name="chat_message_role"),
        nullable=False,
    )
    msg: Mapped[str] = mapped_column(Text, nullable=False)
    midi_events: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    loop_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("midi_loops.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    @validates("midi_events")
    def validate_midi_events(
        self, _key: str, value: list[dict[str, Any] | MidiEvent] | None
    ) -> list[dict[str, Any]] | None:
        """Validate and serialize midi_events to dicts for JSON storage."""
        if value is None:
            return None
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
    loop: Mapped["MidiLoop"] = relationship("MidiLoop", back_populates="chat_messages")

    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, role={self.role}, loop_id={self.loop_id})>"

    def to_response(self) -> "ChatMessageResponse":
        return loop_schemas.ChatMessageResponse(
            id=str(self.id),
            role=self.role,
            msg=self.msg,
            midi_events=[MidiEvent.model_validate(event) for event in self.midi_events],
            loop_id=str(self.loop_id),
            created_at=self.created_at.isoformat(),
            updated_at=self.updated_at.isoformat(),
        )


# Legacy support - keep old ConversationMessage model for backward compatibility
class ConversationMessage(Base):
    """[DEPRECATED] Legacy conversation message model. Use ChatMessage instead."""

    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    thread_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
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

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<ConversationMessage(id={self.id}, thread_id={self.thread_id}, role={self.role})>"


# Legacy functions - keep for backward compatibility
def store_user_message(
    db: Any,
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
    """[DEPRECATED] Store a user message in the database. Use new models instead."""
    message = ConversationMessage(
        user_id=user_id,
        thread_id=thread_id,
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
    db: Any,
    user_id: UUID,
    thread_id: UUID,
    content: str,
    plan_data: dict[str, Any],
    midi_events: list[dict[str, Any]],
) -> ConversationMessage:
    """[DEPRECATED] Store an assistant response in the database. Use new models instead."""
    message = ConversationMessage(
        user_id=user_id,
        thread_id=thread_id,
        role="assistant",
        content=content,
        plan_data=plan_data,
        midi_events=midi_events,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_conversation_history(db: Any, user_id: UUID, thread_id: UUID) -> list[ConversationMessage]:
    """[DEPRECATED] Retrieve all messages for a given user and thread. Use new models instead."""
    messages: list[ConversationMessage] = (
        db.query(ConversationMessage)
        .filter(
            ConversationMessage.user_id == user_id,
            ConversationMessage.thread_id == thread_id,
        )
        .order_by(ConversationMessage.created_at.asc())
        .all()
    )
    return messages
