"""Pydantic schemas for MIDI loops."""

import pydantic
from pydantic import ConfigDict


class ChatMessageResponse(pydantic.BaseModel):
    """Response model for chat messages."""

    id: str = pydantic.Field(description="Chat message ID")
    role: str = pydantic.Field(description="Message role: 'user' or 'assistant'")
    msg: str = pydantic.Field(description="Message content")
    midi_events: list[dict] | None = pydantic.Field(None, description="MIDI events (if any)")
    loop_id: str = pydantic.Field(description="ID of the associated loop")
    created_at: str = pydantic.Field(description="ISO timestamp of message creation")
    updated_at: str = pydantic.Field(description="ISO timestamp of last update")

    model_config = pydantic.ConfigDict(from_attributes=True)


class LoopResponse(pydantic.BaseModel):
    """Response model for MIDI loops, excluding chat message history."""

    id: str = pydantic.Field(description="Loop ID")
    measures: int = pydantic.Field(description="Number of measures in the loop")
    repeat: int = pydantic.Field(description="Number of times to repeat the loop")
    midi_events: list[dict] = pydantic.Field(description="MIDI events in the loop")
    track_id: str = pydantic.Field(description="ID of the parent track")
    created_at: str = pydantic.Field(description="ISO timestamp of creation")
    updated_at: str = pydantic.Field(description="ISO timestamp of last update")

    model_config = ConfigDict(from_attributes=True)


class LoopDetailResponse(LoopResponse):
    """Response model for MIDI loops, including chat message history."""

    chats: list[ChatMessageResponse] = pydantic.Field(
        default_factory=list, description="Chat messages in chronological order"
    )

    model_config = ConfigDict(from_attributes=True)


class CreateLoopRequest(pydantic.BaseModel):
    """Request model for creating a new loop."""

    track_id: str = pydantic.Field(description="ID of the parent track")
    measures: int = pydantic.Field(gt=0, le=33, description="Number of measures in the loop (1-32)")
    repeat: int = pydantic.Field(default=1, gt=0, description="Number of times to repeat the loop (default: 1)")


class ChatHistoryResponse(pydantic.BaseModel):
    """Response model for chat history."""

    loop_id: str = pydantic.Field(description="Loop ID")
    messages: list[ChatMessageResponse] = pydantic.Field(description="Chat messages in chronological order")


class AppendChatRequest(pydantic.BaseModel):
    """Request model for appending a new chat message to a loop."""

    loop_id: str = pydantic.Field(description="ID of the loop to add the chat message to")
    msg: str = pydantic.Field(min_length=1, description="User message content")
    measures: int = pydantic.Field(gt=0, le=33, description="Number of measures in the loop (1-32)")
