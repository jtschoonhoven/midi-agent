"""FastAPI routes for MIDI generation."""

import shutil
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

import pydantic
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import get_db
from api.midi.midi_models import get_conversation_history, store_assistant_message, store_user_message
from api.midi.midi_renderer import render_midi_to_audio
from api.midi.midi_utils import MidiEvent, PlanResponse, run_generation_pipeline

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

    user_id: UUID = pydantic.Field(description="User identifier for tracking")
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
    """Request to restore a conversation by user_id and thread_id."""

    user_id: UUID = pydantic.Field(description="User identifier")
    thread_id: UUID = pydantic.Field(description="Thread identifier to restore")


class ConversationMessage(pydantic.BaseModel):
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
    messages: list[ConversationMessage] = pydantic.Field(description="Conversation messages in chronological order")
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


router = APIRouter(prefix="/api/midi", tags=["midi"])


@router.post("/generate", response_model=MidiResponse)
async def generate_midi(request: GenerateRequest, db: Session = Depends(get_db)) -> MidiResponse:
    """
    Generate MIDI events from a natural language prompt.

    Args:
        request: Generation request with user_id, thread_id, constraints, and prompt
        db: Database session

    Returns:
        MidiResponse with plan and list of MIDI events

    Raises:
        HTTPException: If generation fails
    """
    try:
        # Store user message
        store_user_message(
            db=db,
            user_id=request.user_id,
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
            user_id=request.user_id,
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
    request: ConversationRestoreRequest, db: Session = Depends(get_db)
) -> ConversationRestoreResponse:
    """
    Restore a previous conversation by user_id and thread_id.

    Args:
        request: Restore request with user_id and thread_id
        db: Database session

    Returns:
        ConversationRestoreResponse with full conversation history

    Raises:
        HTTPException: If conversation not found or retrieval fails
    """
    try:
        # Retrieve conversation history
        messages = get_conversation_history(db, request.user_id, request.thread_id)

        # Return 404 if no conversation found
        if not messages:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Convert to response format
        conversation_messages = [
            ConversationMessage(
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
            user_id=request.user_id,
            thread_id=request.thread_id,
            messages=conversation_messages,
            message_count=len(conversation_messages),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversation restoration failed: {str(e)}")


@router.post("/render", response_model=RenderResponse)
async def render_midi(request: RenderRequest) -> RenderResponse:
    """
    Render MIDI events to audio.

    Args:
        request: Render request with BPM and MIDI events

    Returns:
        RenderResponse with audio URL, duration, and sample rate

    Raises:
        HTTPException: If rendering fails
    """
    try:
        # Render MIDI to audio
        sample_rate = 44100
        audio_file_path, duration, actual_sample_rate = render_midi_to_audio(request.midi, request.bpm, sample_rate)

        # Store audio file in a persistent location
        # Create output directory if it doesn't exist
        project_root = Path(__file__).parent.parent.parent
        output_dir = project_root / "audio_output"
        output_dir.mkdir(exist_ok=True)

        # Generate unique filename
        output_filename = f"{uuid4()}.wav"
        output_path = output_dir / output_filename

        # Move rendered file to output directory
        shutil.move(audio_file_path, str(output_path))

        # Generate URL (for local development, use file path)
        # In production, this would be a proper URL to a CDN or file server
        audio_url = f"/audio/{output_filename}"

        return RenderResponse(audio_url=audio_url, duration_seconds=duration, sample_rate=actual_sample_rate)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Soundfont not found: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MIDI rendering failed: {str(e)}")
