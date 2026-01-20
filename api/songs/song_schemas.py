"""Pydantic schemas for MIDI songs."""

from uuid import UUID

import pydantic
from pydantic import ConfigDict

from api.chats.chat_types import ModelName
from api.songs.song_types import Key, TimeSignature
from api.tracks import track_schemas


# Request/Response models for this route
class GenerateRequest(pydantic.BaseModel):
    """Request payload for /api/midi/generate endpoint."""

    thread_id: UUID = pydantic.Field(description="Thread identifier for conversation context")
    plan_model: ModelName = pydantic.Field(description="Model to use for the planning stage")
    generate_model: ModelName = pydantic.Field(description="Model to use for the generation stage")
    key: Key | None = pydantic.Field(None, description="Musical key constraint")
    bpm: int | None = pydantic.Field(None, gt=29, lt=361, description="Tempo constraint in BPM (30-360)")
    time_signature: TimeSignature | None = pydantic.Field(None, description="Time signature constraint")
    measures: int | None = pydantic.Field(None, gt=0, lt=33, description="Number of measures to generate (1-32)")
    prompt: str = pydantic.Field(min_length=1, description="User's musical generation request")


class ConversationRestoreRequest(pydantic.BaseModel):
    """Request to restore a conversation by thread_id."""

    thread_id: UUID = pydantic.Field(description="Thread identifier to restore")


class ConversationMessageResponse(pydantic.BaseModel):
    """A message in the conversation history."""

    role: str = pydantic.Field(description="Message role: 'user' or 'assistant'")
    content: str = pydantic.Field(description="Message content")
    plan_model: str | None = pydantic.Field(None, description="Model used for planning (user messages only)")
    generate_model: str | None = pydantic.Field(None, description="Model used for generation (user messages only)")
    key: str | None = pydantic.Field(None, description="Musical key constraint (user messages only)")
    bpm: int | None = pydantic.Field(None, description="BPM constraint (user messages only)")
    time_signature: str | None = pydantic.Field(None, description="Time signature constraint (user messages only)")
    measures: int | None = pydantic.Field(None, description="Measures constraint (user messages only)")
    plan_data: dict | None = pydantic.Field(None, description="Plan data (assistant messages only)")
    midi_events: list[dict] | None = pydantic.Field(None, description="MIDI events (assistant messages only)")
    created_at: str = pydantic.Field(description="ISO timestamp of message creation")


class ConversationRestoreResponse(pydantic.BaseModel):
    """Response containing conversation history."""

    user_id: UUID = pydantic.Field(description="User identifier")
    thread_id: UUID = pydantic.Field(description="Thread identifier")
    messages: list[ConversationMessageResponse] = pydantic.Field(
        description="Conversation messages in chronological order"
    )


class SongResponse(pydantic.BaseModel):
    """Response model for MIDI songs including tracks and loops."""

    id: str = pydantic.Field(description="Song ID")
    title: str = pydantic.Field(description="Song title")
    bpm: int = pydantic.Field(description="Tempo in BPM")
    key: str = pydantic.Field(description="Musical key")
    time_signature: str = pydantic.Field(description="Time signature")
    created_at: str = pydantic.Field(description="ISO timestamp of creation")
    updated_at: str = pydantic.Field(description="ISO timestamp of last update")

    model_config = ConfigDict(from_attributes=True)


class SongDetailResponse(SongResponse):
    """Response model for MIDI songs including tracks and loops."""

    tracks: list[track_schemas.TrackDetailResponse] = pydantic.Field(description="Tracks in this song")

    model_config = ConfigDict(from_attributes=True)


class CreateSongRequest(pydantic.BaseModel):
    """Request payload for creating a new song."""

    title: str | None = pydantic.Field(None, description="Song title (optional)")
    bpm: int = pydantic.Field(gt=29, lt=361, description="Tempo in BPM (30-360)")
    key: Key = pydantic.Field(description="Musical key")
    time_signature: TimeSignature = pydantic.Field(description="Time signature")
