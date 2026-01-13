"""FastAPI routes for MIDI generation."""

import random
import shutil
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

import pydantic
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ConfigDict
from sqlalchemy.orm import Session

from api.audio.audio_types import MidiEvent
from api.auth import get_current_user_id
from api.database import get_db
from api.songs.song_constants import ADJECTIVES, NOUNS
from api.songs.song_models import MidiSong
from api.tracks.track_models import MidiTrack
from api.loops.loop_models import MidiLoop
from api.chats.chat_models import (
    ConversationMessage,
    get_conversation_history,
    store_assistant_message,
    store_user_message,
)
from api.songs.song_utils import PlanResponse, run_generation_pipeline

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


class MidiResponse(pydantic.BaseModel):
    """Response from /api/midi/generate endpoint including plan and MIDI."""

    plan: PlanResponse = pydantic.Field(description="Musical plan from the planning stage")
    midi: list[MidiEvent] = pydantic.Field(description="Generated MIDI events")


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
    messages: list[ConversationMessageResponse] = pydantic.Field(description="Conversation messages in chronological order")
    message_count: int = pydantic.Field(description="Total number of messages")


class RenderRequest(pydantic.BaseModel):
    """Request payload for /api/midi/render endpoint."""

    bpm: int = pydantic.Field(gt=29, lt=361, description="Tempo in BPM (30-360)")
    midi: list[MidiEvent] = pydantic.Field(description="MIDI events to render")


class RenderResponse(pydantic.BaseModel):
    """Response from /api/midi/render endpoint with audio information."""

    audio_url: str = pydantic.Field(description="URL to the rendered audio file")
    duration_seconds: float = pydantic.Field(gt=0, description="Duration of the audio in seconds")
    sample_rate: int = pydantic.Field(gt=0, description="Sample rate of the audio in Hz")


# Response models for new RESTful endpoints
class ChatMessageResponse(pydantic.BaseModel):
    """Response model for chat messages."""

    id: str = pydantic.Field(description="Chat message ID")
    role: str = pydantic.Field(description="Message role: 'user' or 'assistant'")
    msg: str = pydantic.Field(description="Message content")
    midi_events: list[dict] | None = pydantic.Field(None, description="MIDI events (if any)")
    loop_id: str = pydantic.Field(description="ID of the associated loop")
    created_at: str = pydantic.Field(description="ISO timestamp of message creation")
    updated_at: str = pydantic.Field(description="ISO timestamp of last update")

    model_config = ConfigDict(from_attributes=True)


class LoopResponse(pydantic.BaseModel):
    """Response model for MIDI loops."""

    id: str = pydantic.Field(description="Loop ID")
    title: str = pydantic.Field(description="Loop title")
    measures: int = pydantic.Field(description="Number of measures in the loop")
    repeat: int = pydantic.Field(description="Number of times to repeat the loop")
    midi_events: list[dict] = pydantic.Field(description="MIDI events in the loop")
    track_id: str = pydantic.Field(description="ID of the parent track")
    created_at: str = pydantic.Field(description="ISO timestamp of creation")
    updated_at: str = pydantic.Field(description="ISO timestamp of last update")

    model_config = ConfigDict(from_attributes=True)


class TrackResponse(pydantic.BaseModel):
    """Response model for MIDI tracks."""

    id: str = pydantic.Field(description="Track ID")
    song_id: str = pydantic.Field(description="ID of the parent song")
    midi_channel: int = pydantic.Field(gt=0, description="MIDI channel (1-16)")
    loops: list[LoopResponse] = pydantic.Field(default_factory=list, description="Loops in this track")
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


class ChatHistoryResponse(pydantic.BaseModel):
    """Response model for chat history."""

    loop_id: str = pydantic.Field(description="Loop ID")
    messages: list[ChatMessageResponse] = pydantic.Field(description="Chat messages in chronological order")
    message_count: int = pydantic.Field(description="Total number of messages")




router = APIRouter(prefix="/api/midi", tags=["midi"])


@router.post("/generate", response_model=MidiResponse)
async def generate_midi(
    request: GenerateRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> MidiResponse:
    """
    Generate MIDI events from a natural language prompt.

    Args:
        request: Generation request with thread_id, constraints, and prompt
        db: Database session
        user_id: User ID from Authorization header

    Returns:
        MidiResponse with plan and list of MIDI events

    Raises:
        HTTPException: If generation fails
    """
    try:
        # Store user message
        store_user_message(
            db=db,
            user_id=user_id,
            thread_id=request.thread_id,
            prompt=request.prompt,
            plan_model=request.plan_model,
            generate_model=request.generate_model,
            key=request.key,
            bpm=request.bpm,
            time_signature=request.time_signature,
            measures=request.measures,
        )

        # Generate MIDI
        plan, midi_events = run_generation_pipeline(request)
        response = MidiResponse(plan=plan, midi=midi_events)

        # Store assistant response
        store_assistant_message(
            db=db,
            user_id=user_id,
            thread_id=request.thread_id,
            content=plan.reasoning,
            plan_data={
                "key": plan.key,
                "bpm": plan.bpm,
                "time_signature": plan.time_signature,
                "measures": plan.measures,
                "style": plan.style,
                "chord_progression": plan.chord_progression,
                "reasoning": plan.reasoning,
            },
            midi_events=[
                {
                    "measure": event.measure,
                    "beat": event.beat,
                    "beat_div4": event.beat_div4,
                    "beat_div16": event.beat_div16,
                    "event": event.event,
                    "value": event.value,
                }
                for event in midi_events
            ],
        )

        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MIDI generation failed: {str(e)}")


@router.post("/restore", response_model=ConversationRestoreResponse)
async def restore_conversation(
    request: ConversationRestoreRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> ConversationRestoreResponse:
    """
    Restore a previous conversation by thread_id.

    Args:
        request: Restore request with thread_id
        db: Database session
        user_id: User ID from Authorization header

    Returns:
        ConversationRestoreResponse with full conversation history

    Raises:
        HTTPException: If conversation not found or retrieval fails
    """
    try:
        # Retrieve conversation history
        messages = get_conversation_history(db, user_id, request.thread_id)

        # Return 404 if no conversation found
        if not messages:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Convert to response format
        conversation_messages = [
            ConversationMessageResponse(
                role=msg.role,
                content=msg.content,
                plan_model=msg.plan_model,
                generate_model=msg.generate_model,
                key=msg.key,
                bpm=msg.bpm,
                time_signature=msg.time_signature,
                measures=msg.measures,
                plan_data=msg.plan_data,
                midi_events=msg.midi_events,
                created_at=msg.created_at.isoformat(),
            )
            for msg in messages
        ]

        return ConversationRestoreResponse(
            user_id=user_id,
            thread_id=request.thread_id,
            messages=conversation_messages,
            message_count=len(conversation_messages),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversation restoration failed: {str(e)}")


@router.post("/songs/", response_model=SongDetailResponse)
async def create_song(
    request: CreateSongRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> SongDetailResponse:
    """
    Create a new song with an empty track.

    Args:
        request: Song creation request with title, bpm, and key
        db: Database session
        user_id: User ID from Authorization header

    Returns:
        SongDetailResponse with the new song and its empty track

    Raises:
        HTTPException: If creation fails
    """
    try:
        # Auto-generate title if not provided
        title = request.title
        if not title:
            adjective = random.choice(ADJECTIVES)
            noun = random.choice(NOUNS)
            title = f"{adjective} {noun}"

        # Create the song
        song = MidiSong(
            user_id=str(user_id),
            title=title,
            bpm=request.bpm,
            key=request.key,
        )
        db.add(song)
        db.flush()  # Flush to get the song ID without committing

        # Create an empty track with default MIDI channel 1
        track = MidiTrack(
            song_id=song.id,
            midi_channel=1,
        )
        db.add(track)
        db.commit()
        db.refresh(song)
        db.refresh(track)

        # Build response with the empty track
        track_response = TrackResponse(
            id=track.id,
            song_id=track.song_id,
            midi_channel=track.midi_channel,
            loops=[],
            created_at=track.created_at.isoformat(),
            updated_at=track.updated_at.isoformat(),
        )

        return SongDetailResponse(
            id=song.id,
            title=song.title,
            bpm=song.bpm,
            key=song.key,
            tracks=[track_response],
            created_at=song.created_at.isoformat(),
            updated_at=song.updated_at.isoformat(),
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create song: {str(e)}")


@router.get("/songs/", response_model=list[SongResponse])
async def list_songs(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> list[SongResponse]:
    """
    List all songs for the current user.

    Args:
        db: Database session
        user_id: User ID from Authorization header

    Returns:
        List of SongResponse objects

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        songs = (
            db.query(MidiSong)
            .filter(MidiSong.user_id == str(user_id))
            .order_by(MidiSong.created_at.desc())
            .all()
        )

        return [
            SongResponse(
                id=song.id,
                title=song.title,
                bpm=song.bpm,
                key=song.key,
                created_at=song.created_at.isoformat(),
                updated_at=song.updated_at.isoformat(),
            )
            for song in songs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve songs: {str(e)}")


@router.get("/songs/{song_id}", response_model=SongDetailResponse)
async def get_song(
    song_id: str,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> SongDetailResponse:
    """
    Get a specific song with all track details and loops.

    Args:
        song_id: Song identifier (path parameter)
        db: Database session
        user_id: User ID from Authorization header

    Returns:
        SongDetailResponse with tracks and loops

    Raises:
        HTTPException: If song not found or access denied
    """
    try:
        song = db.query(MidiSong).filter(MidiSong.id == song_id, MidiSong.user_id == str(user_id)).first()

        if not song:
            raise HTTPException(status_code=404, detail="Song not found or access denied")

        # Build response with tracks and loops
        tracks = [
            TrackResponse(
                id=track.id,
                song_id=track.song_id,
                midi_channel=track.midi_channel,
                loops=[
                    LoopResponse(
                        id=loop.id,
                        title=loop.title,
                        measures=loop.measures,
                        repeat=loop.repeat,
                        midi_events=loop.midi_events,
                        track_id=loop.track_id,
                        created_at=loop.created_at.isoformat(),
                        updated_at=loop.updated_at.isoformat(),
                    )
                    for loop in track.loops
                ],
                created_at=track.created_at.isoformat(),
                updated_at=track.updated_at.isoformat(),
            )
            for track in song.tracks
        ]

        return SongDetailResponse(
            id=song.id,
            title=song.title,
            bpm=song.bpm,
            key=song.key,
            tracks=tracks,
            created_at=song.created_at.isoformat(),
            updated_at=song.updated_at.isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve song: {str(e)}")


