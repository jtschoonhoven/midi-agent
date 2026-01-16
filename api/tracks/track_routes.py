"""FastAPI routes for MIDI tracks."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api import auth, database
from api.songs import song_utils
from api.tracks import track_models, track_schemas, track_utils

router = APIRouter(prefix="/api/midi", tags=["tracks"])


@router.post("/tracks/", response_model=track_schemas.TrackDetailResponse)
async def create_track(
    request: "track_schemas.CreateTrackRequest",
    db: Session = Depends(database.get_db),
    user_id: UUID = Depends(auth.get_current_user_id),
) -> "track_schemas.TrackDetailResponse":
    """
    Create a new MIDI track for a song.

    The MIDI channel is automatically assigned as the next available channel
    based on existing tracks in the song (max channel + 1).
    """
    try:
        # Validate that the song exists and belongs to the user
        song = song_utils.get_song_for_user(db, user_id, request.song_id)

        if not song:
            raise HTTPException(status_code=404, detail="Song not found")

        # Find the highest MIDI channel currently used in this song
        existing_tracks = (
            db.query(track_models.MidiTrack).filter(track_models.MidiTrack.song_id == request.song_id).all()
        )

        if existing_tracks:
            max_channel = max(track.midi_channel for track in existing_tracks)
            next_channel = max_channel + 1
        else:
            next_channel = 1

        # Validate MIDI channel doesn't exceed 16 (MIDI standard limit)
        if next_channel > 16:
            raise HTTPException(status_code=400, detail="Maximum number of tracks (16) reached for this song")

        # Create new track
        new_track = track_models.MidiTrack(
            song_id=request.song_id,
            title=request.title,
            midi_channel=next_channel,
        )
        db.add(new_track)
        db.commit()
        db.refresh(new_track)

        return new_track.to_detail_response()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create track: {str(e)}") from e


@router.delete("/tracks/{track_id}", status_code=204)
async def delete_track(
    track_id: str,
    db: Session = Depends(database.get_db),
    user_id: UUID = Depends(auth.get_current_user_id),
) -> None:
    """
    Delete a track and all associated loops.

    The loops are automatically deleted via cascade relationship.
    """
    track = track_utils.get_track_for_user(db, user_id, track_id)

    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    # Delete the track (loops are cascade deleted)
    db.delete(track)
    db.commit()


@router.patch("/tracks/{track_id}", response_model=track_schemas.TrackResponse)
async def update_track(
    track_id: str,
    request: "track_schemas.PatchTrackRequest",
    db: Session = Depends(database.get_db),
    user_id: UUID = Depends(auth.get_current_user_id),
) -> "track_schemas.TrackResponse":
    """
    Update a track's title, MIDI channel, and/or instrument.
    All fields are optional - only provided fields will be updated.
    """
    track = track_utils.get_track_for_user(db, user_id, track_id)

    if not track:
        raise HTTPException(status_code=404)
    # Update fields if provided
    if request.title is not None:
        track.title = request.title

    if request.midi_channel is not None:
        track.midi_channel = request.midi_channel

    if request.instrument is not None:
        track.instrument = request.instrument

    db.commit()
    db.refresh(track)

    return track.to_response()
