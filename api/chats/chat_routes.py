"""FastAPI routes for chat history."""

import pydantic
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ConfigDict
from sqlalchemy.orm import Session

from api.database import get_db
from api.chats.chat_models import ChatMessage
from api.loops.loop_models import MidiLoop


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


class ChatHistoryResponse(pydantic.BaseModel):
    """Response model for chat history."""

    loop_id: str = pydantic.Field(description="Loop ID")
    messages: list[ChatMessageResponse] = pydantic.Field(description="Chat messages in chronological order")
    message_count: int = pydantic.Field(description="Total number of messages")


router = APIRouter(prefix="/api/midi", tags=["chats"])


@router.get("/loops/{loop_id}/chats", response_model=ChatHistoryResponse)
async def get_loop_chats(loop_id: str, db: Session = Depends(get_db)) -> ChatHistoryResponse:
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
        loop = db.query(MidiLoop).filter(MidiLoop.id == loop_id).first()
        if not loop:
            raise HTTPException(status_code=404, detail="Loop not found")

        # Get all chat messages for this loop
        messages = (
            db.query(ChatMessage).filter(ChatMessage.loop_id == loop_id).order_by(ChatMessage.created_at.asc()).all()
        )

        message_responses = [
            ChatMessageResponse(
                id=msg.id,
                role=msg.role,
                msg=msg.msg,
                midi_events=msg.midi_events,
                loop_id=msg.loop_id,
                created_at=msg.created_at.isoformat(),
                updated_at=msg.updated_at.isoformat(),
            )
            for msg in messages
        ]

        return ChatHistoryResponse(loop_id=loop_id, messages=message_responses, message_count=len(message_responses))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chat history: {str(e)}")

