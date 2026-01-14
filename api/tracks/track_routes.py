"""FastAPI routes for MIDI tracks."""

from uuid import UUID

import pydantic
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ConfigDict
from sqlalchemy.orm import Session

from api import auth, database
from api.songs import song_models, song_schemas
from api.tracks import track_models


class CreateTrackRequest(pydantic.BaseModel):
    """Request model for creating a new track."""

    song_id: str = pydantic.Field(description="ID of the parent song")

    model_config = ConfigDict(from_attributes=True)


router = APIRouter(prefix="/api/midi", tags=["tracks"])


@router.post("/tracks/", response_model=song_schemas.TrackResponse)
async def create_track(
    request: CreateTrackRequest,
    db: Session = Depends(database.get_db),
    user_id: UUID = Depends(auth.get_current_user_id),
) -> song_schemas.TrackResponse:
    """
    Create a new MIDI track for a song.

    The MIDI channel is automatically assigned as the next available channel
    based on existing tracks in the song (max channel + 1).
    """
    try:
        # Validate that the song exists and belongs to the user
        song = (
            db.query(song_models.MidiSong)
            .filter(song_models.MidiSong.id == request.song_id, song_models.MidiSong.user_id == str(user_id))
            .first()
        )

        if not song:
            raise HTTPException(status_code=404, detail="Song not found")

        # Find the highest MIDI channel currently used in this song
        existing_tracks = (
            db.query(track_models.MidiTrack)
            .filter(track_models.MidiTrack.song_id == request.song_id)
            .all()
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
            midi_channel=next_channel,
        )
        db.add(new_track)
        db.commit()
        db.refresh(new_track)

        return new_track.to_response()

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create track: {str(e)}") from e
