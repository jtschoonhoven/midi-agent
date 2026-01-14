"""Pydantic schemas for MIDI songs."""

from typing import Literal
from uuid import UUID

import pydantic
from pydantic import ConfigDict

from api.loops import loop_schemas

# Type aliases
Key = Literal["Ab", "A", "A#", "Bb", "B", "C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb", "G", "G#"]
TimeSignature = Literal["3/4", "4/4", "5/4", "6/8", "7/8"]
ModelName = Literal[
    "claude-haiku-4-5",
    "claude-sonnet-4-5",
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-5-2",
    "gpt-5-mini",
    "gpt-5-nano",
]


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


class TrackResponse(pydantic.BaseModel):
    """Response model for MIDI tracks."""

    id: str = pydantic.Field(description="Track ID")
    song_id: str = pydantic.Field(description="ID of the parent song")
    midi_channel: int = pydantic.Field(gt=0, description="MIDI channel (1-16)")
    loops: list[loop_schemas.LoopResponse] = pydantic.Field(default_factory=list, description="Loops in this track")
    created_at: str = pydantic.Field(description="ISO timestamp of creation")
    updated_at: str = pydantic.Field(description="ISO timestamp of last update")

    model_config = ConfigDict(from_attributes=True)


class SongResponse(pydantic.BaseModel):
    """Response model for MIDI songs including tracks and loops."""

    id: str = pydantic.Field(description="Song ID")
    title: str = pydantic.Field(description="Song title")
    bpm: int = pydantic.Field(description="Tempo in BPM")
    key: str = pydantic.Field(description="Musical key")
    created_at: str = pydantic.Field(description="ISO timestamp of creation")
    updated_at: str = pydantic.Field(description="ISO timestamp of last update")

    model_config = ConfigDict(from_attributes=True)


class SongDetailResponse(SongResponse):
    """Response model for MIDI songs including tracks and loops."""

    tracks: list[TrackResponse] = pydantic.Field(default_factory=list, description="Tracks in this song")

    model_config = ConfigDict(from_attributes=True)


class CreateSongRequest(pydantic.BaseModel):
    """Request payload for creating a new song."""

    title: str | None = pydantic.Field(None, description="Song title (optional)")
    bpm: int = pydantic.Field(gt=29, lt=361, description="Tempo in BPM (30-360)")
    key: Key = pydantic.Field(description="Musical key")
