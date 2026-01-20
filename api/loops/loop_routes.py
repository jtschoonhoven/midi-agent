"""FastAPI routes for MIDI loops."""

from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from api import auth, database
from api.loops import loop_models, loop_schemas, loop_utils
from api.midi import midi_agents
from api.songs import song_models
from api.tracks import track_models, track_utils

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
        extend_measures=request.extend_measures,
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
    Update a loop's offset, extend_measures, or track_id.
    All fields are optional - only provided fields will be updated.
    """
    loop = loop_utils.get_loop_for_user(db, user_id, loop_id)

    if not loop:
        raise HTTPException(status_code=404)

    # Update fields if provided
    if request.offset is not None:
        loop.offset = request.offset

    if request.extend_measures is not None:
        loop.extend_measures = request.extend_measures

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
    loop: loop_models.MidiLoop | None = (
        db.query(loop_models.MidiLoop)
        .join(track_models.MidiTrack, loop_models.MidiLoop.track_id == track_models.MidiTrack.id)
        .join(song_models.MidiSong, track_models.MidiTrack.song_id == song_models.MidiSong.id)
        .options(
            # Eager load related resources
            joinedload(loop_models.MidiLoop.chat_messages),
            joinedload(loop_models.MidiLoop.track).joinedload(track_models.MidiTrack.song),
        )
        .filter(loop_models.MidiLoop.id == str(request.loop_id), song_models.MidiSong.user_id == str(user_id))
        .first()
    )
    if not loop:
        raise HTTPException(status_code=404)

    track = loop.track
    song = track.song

    loop = await midi_agents.generate_midi_for_loop(
        user_id=user_id,
        loop_id=loop.id,
        model_name=midi_agents.DEFAULT_MODEL_NAME,
        user_prompt=request.msg,
        expect_time_signature=song.time_signature,
        expect_bpm=song.bpm,
        expect_key=song.key,
        expect_measures=request.measures,
        expect_instrument=loop.track.instrument,
    )

    return loop.to_detail_response()


@router.get("/loops/{loop_id}/download")
async def download_loop_wav(
    loop_id: str,
    db: Session = Depends(database.get_db),
    user_id: UUID = Depends(auth.get_current_user_id),
) -> StreamingResponse:
    """
    Download a loop as a WAV file.

    Renders the loop to audio using the instrument samples and returns it as a downloadable WAV file.
    """
    # Get loop with track and song information
    loop: loop_models.MidiLoop | None = (
        db.query(loop_models.MidiLoop)
        .join(track_models.MidiTrack, loop_models.MidiLoop.track_id == track_models.MidiTrack.id)
        .join(song_models.MidiSong, track_models.MidiTrack.song_id == song_models.MidiSong.id)
        .options(
            joinedload(loop_models.MidiLoop.track).joinedload(track_models.MidiTrack.song),
        )
        .filter(loop_models.MidiLoop.id == str(loop_id), song_models.MidiSong.user_id == str(user_id))
        .first()
    )

    if not loop:
        raise HTTPException(status_code=404, detail="Loop not found")

    # Check if loop has MIDI events
    if not loop.midi_events:
        raise HTTPException(status_code=400, detail="Loop has no MIDI events to render")

    track = loop.track
    song = track.song

    # Render loop to WAV
    try:
        wav_buffer = track_utils.render_loop_to_wav(db, loop, track, song)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to render loop: {str(e)}")

    # Generate filename
    filename = f"loop_{loop_id[:8]}.wav"

    # Return as streaming response
    return StreamingResponse(
        wav_buffer,
        media_type="audio/wav",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
