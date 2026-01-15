"""FastAPI routes for MIDI loops."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api import auth, database
from api.loops import loop_models, loop_schemas, loop_utils
from api.midi import midi_agents
from api.tracks import track_utils

router = APIRouter(prefix="/api/midi", tags=["loops"])


@router.post("/loops/", response_model=loop_schemas.LoopDetailResponse)
async def create_loop(
    request: loop_schemas.CreateLoopRequest,
    db: Session = Depends(database.get_db),
    user_id: UUID = Depends(auth.get_current_user_id),
) -> loop_schemas.LoopDetailResponse:
    """
    Create a new MIDI loop.
    """
    track = track_utils.get_track_for_user(db, user_id, request.track_id)

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


@router.get("/loops/{loop_id}", response_model=loop_schemas.LoopDetailResponse)
async def get_loop(
    loop_id: str,
    db: Session = Depends(database.get_db),
    user_id: UUID = Depends(auth.get_current_user_id),
) -> loop_schemas.LoopDetailResponse:
    """
    Get a specific loop with all chat messages.
    """
    loop = loop_utils.get_loop_for_user(db, user_id, loop_id)

    if not loop:
        raise HTTPException(status_code=404)

    return loop.to_detail_response()


@router.delete("/loops/{loop_id}", status_code=204)
async def delete_loop(
    loop_id: str,
    db: Session = Depends(database.get_db),
    user_id: UUID = Depends(auth.get_current_user_id),
) -> None:
    """
    Delete a loop and all associated chat messages.

    The chat messages are automatically deleted via cascade relationship.
    """
    loop = loop_utils.get_loop_for_user(db, user_id, loop_id)

    if not loop:
        raise HTTPException(status_code=404, detail="Loop not found")

    # Delete the loop (chat messages are cascade deleted)
    db.delete(loop)
    db.commit()


@router.patch("/loops/{loop_id}", response_model=loop_schemas.LoopResponse)
async def update_loop(
    loop_id: str,
    request: loop_schemas.PatchLoopRequest,
    db: Session = Depends(database.get_db),
    user_id: UUID = Depends(auth.get_current_user_id),
) -> loop_schemas.LoopResponse:
    """
    Update a loop's offset, repeat, or track_id.
    All fields are optional - only provided fields will be updated.
    """
    loop = loop_utils.get_loop_for_user(db, user_id, loop_id)

    if not loop:
        raise HTTPException(status_code=404)

    # Update fields if provided
    if request.offset is not None:
        loop.offset = request.offset

    if request.repeat is not None:
        loop.repeat = request.repeat

    if request.track_id is not None:
        track = track_utils.get_track_for_user(db, user_id, request.track_id)

        if not track:
            raise HTTPException(status_code=404, detail="Track not found")

        loop.track_id = request.track_id

    db.commit()
    db.refresh(loop)

    return loop.to_response()


@router.post("/loops/{loop_id}/chats", response_model=loop_schemas.LoopDetailResponse)
async def append_chat(
    request: loop_schemas.AppendChatRequest,
    db: Session = Depends(database.get_db),
    user_id: UUID = Depends(auth.get_current_user_id),
) -> loop_schemas.LoopDetailResponse:
    """Create a new user chat message for a loop."""
    loop = loop_utils.get_loop_for_user(db, user_id, request.loop_id)

    if not loop:
        raise HTTPException(status_code=404)

    agent = midi_agents.get_agent()
    loop: loop_models.MidiLoop = await agent.invoke(
        user_id=user_id,
        loop_id=loop.id,
        user_prompt=request.msg,
        expect_measures=request.measures,
    )

    return loop.to_detail_response()
