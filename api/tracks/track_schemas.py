import pydantic
from pydantic import ConfigDict

from api.loops import loop_schemas


class TrackResponse(pydantic.BaseModel):
    """Response model for MIDI tracks (excludes loops)."""

    id: str = pydantic.Field(description="Track ID")
    song_id: str = pydantic.Field(description="ID of the parent song")
    title: str = pydantic.Field(description="Track title")
    midi_channel: int = pydantic.Field(gt=0, description="MIDI channel (1-16)")
    created_at: str = pydantic.Field(description="ISO timestamp of creation")
    updated_at: str = pydantic.Field(description="ISO timestamp of last update")

    model_config = ConfigDict(from_attributes=True)


class TrackDetailResponse(TrackResponse):
    """Response model for MIDI tracks including loops."""

    loops: list[loop_schemas.LoopResponse] = pydantic.Field(description="Loops in this track")

    model_config = ConfigDict(from_attributes=True)


class CreateTrackRequest(pydantic.BaseModel):
    """Request model for creating a new track."""

    song_id: str = pydantic.Field(description="ID of the parent song")
    title: str = pydantic.Field(min_length=1, description="Track title")

    model_config = ConfigDict(from_attributes=True)


class PatchTrackRequest(pydantic.BaseModel):
    """Request model for updating a track."""

    title: str | None = pydantic.Field(None, min_length=1, description="Track title (optional)")
    midi_channel: int | None = pydantic.Field(None, ge=1, le=16, description="MIDI channel 1-16 (optional)")

    model_config = ConfigDict(from_attributes=True)
