"""FastAPI routes for MIDI loops."""

from uuid import UUID

import pydantic
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ConfigDict
from sqlalchemy.orm import Session

from api import auth, database
from api.chats import chat_models
from api.loops import loop_models
from api.midi import midi_agents
from api.songs import song_models
from api.tracks import track_models


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


router = APIRouter(prefix="/api/midi", tags=["loops"])


@router.post("/loops/", response_model=LoopDetailResponse)
async def create_loop(
    request: CreateLoopRequest,
    db: Session = Depends(database.get_db),
    user_id: UUID = Depends(auth.get_current_user_id),
) -> LoopDetailResponse:
    """
    Create a new MIDI loop.
    """
    try:
        # Validate that the track exists and belongs to a song owned by the user
        track = (
            db.query(track_models.MidiTrack)
            .join(song_models.MidiSong, track_models.MidiTrack.song_id == song_models.MidiSong.id)
            .filter(track_models.MidiTrack.id == request.track_id, song_models.MidiSong.user_id == str(user_id))
            .first()
        )

        if not track:
            raise HTTPException(status_code=404)

        # Create new loop with empty MIDI events
        new_loop = loop_models.MidiLoop(
            measures=request.measures,
            repeat=request.repeat,
            midi_events=[],
            track_id=request.track_id,
        )
        db.add(new_loop)
        db.commit()
        db.refresh(new_loop)

        return new_loop.to_detail_response()

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create loop: {str(e)}") from e


@router.get("/loops/{loop_id}/chats", response_model=ChatHistoryResponse)
async def get_chats(loop_id: str, db: Session = Depends(database.get_db)) -> ChatHistoryResponse:
    """
    Get complete chat history for a specific loop.

    Args:
        loop_id: Loop identifier (path parameter)
        db: Database session

    Returns:
        ChatHistoryResponse with all messages

    Raises:
        HTTPException: If loop not found
    """
    try:
        # Verify loop exists
        loop = db.query(loop_models.MidiLoop).filter(loop_models.MidiLoop.id == loop_id).first()
        if not loop:
            raise HTTPException(status_code=404, detail="Loop not found")

        # Get all chat messages for this loop
        messages = (
            db.query(chat_models.ChatMessage)
            .filter(chat_models.ChatMessage.loop_id == loop_id)
            .order_by(chat_models.ChatMessage.created_at.asc())
            .all()
        )

        messages_response = [msg.to_response() for msg in messages]

        return ChatHistoryResponse(loop_id=loop_id, messages=messages_response)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chat history: {str(e)}") from e


class AppendChatRequest(pydantic.BaseModel):
    """Request model for appending a new chat message to a loop."""

    loop_id: str = pydantic.Field(description="ID of the loop to add the chat message to")
    msg: str = pydantic.Field(min_length=1, description="User message content")


@router.post("/loops/{loop_id}/chats", response_model=LoopDetailResponse)
async def append_chat(
    request: AppendChatRequest,
    db: Session = Depends(database.get_db),
    user_id: UUID = Depends(auth.get_current_user_id),
) -> LoopDetailResponse:
    """Create a new user chat message for a loop."""
    try:
        # Validate that the loop exists and belongs to a track owned by the user
        loop: loop_models.MidiLoop | None = (
            db.query(loop_models.MidiLoop)
            .join(track_models.MidiTrack, loop_models.MidiLoop.track_id == track_models.MidiTrack.id)
            .join(song_models.MidiSong, track_models.MidiTrack.song_id == song_models.MidiSong.id)
            .filter(loop_models.MidiLoop.id == request.loop_id, song_models.MidiSong.user_id == str(user_id))
            .first()
        )

        if not loop:
            raise HTTPException(status_code=404)

        agent = midi_agents.get_agent()
        loop: loop_models.MidiLoop = await agent.invoke(
            user_id=user_id, track_id=loop.track_id, loop_id=loop.id, user_prompt=request.msg
        )

        return loop.to_detail_response()

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create chat message: {str(e)}") from e
