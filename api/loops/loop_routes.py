"""FastAPI routes for MIDI loops."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from api import auth, database
from api.loops import loop_models, loop_schemas
from api.midi import midi_agents
from api.songs import song_models
from api.tracks import track_models

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
        raise HTTPException(status_code=500, detail=f"Failed to create loop") from e


@router.get("/loops/{loop_id}", response_model=loop_schemas.LoopDetailResponse)
async def get_loop(loop_id: str, db: Session = Depends(database.get_db)) -> loop_schemas.LoopDetailResponse:
    """
    Get a specific loop with all chat messages.
    """
    try:
        loop = (
            db.query(loop_models.MidiLoop)
            .options(joinedload(loop_models.MidiLoop.chat_messages))
            .filter(loop_models.MidiLoop.id == loop_id)
            .first()
        )
        if not loop:
            raise HTTPException(status_code=404)
        
        return loop.to_detail_response()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500) from e


@router.delete("/loops/{loop_id}", status_code=201)
async def delete_loop(
    loop_id: str,
    db: Session = Depends(database.get_db),
    user_id: UUID = Depends(auth.get_current_user_id),
) -> None:
    """
    Delete a loop and all associated chat messages.

    The chat messages are automatically deleted via cascade relationship.
    """
    try:
        # Validate that the loop exists and belongs to a track owned by the user
        loop: loop_models.MidiLoop | None = (
            db.query(loop_models.MidiLoop)
            .join(track_models.MidiTrack, loop_models.MidiLoop.track_id == track_models.MidiTrack.id)
            .join(song_models.MidiSong, track_models.MidiTrack.song_id == song_models.MidiSong.id)
            .filter(loop_models.MidiLoop.id == loop_id, song_models.MidiSong.user_id == str(user_id))
            .first()
        )

        if not loop:
            raise HTTPException(status_code=404, detail="Loop not found")

        # Delete the loop (chat messages are cascade deleted)
        db.delete(loop)
        db.commit()

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete loop: {str(e)}") from e


@router.post("/loops/{loop_id}/chats", response_model=loop_schemas.LoopDetailResponse)
async def append_chat(
    request: loop_schemas.AppendChatRequest,
    db: Session = Depends(database.get_db),
    user_id: UUID = Depends(auth.get_current_user_id),
) -> loop_schemas.LoopDetailResponse:
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
            user_id=user_id, track_id=loop.track_id, loop_id=loop.id, user_prompt=request.msg, expect_measures=request.measures
        )

        return loop.to_detail_response()

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create chat message: {str(e)}") from e
