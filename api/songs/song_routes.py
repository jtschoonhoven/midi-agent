"""FastAPI routes for MIDI generation."""

import random
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from api import database
from api.auth import get_current_user_id
from api.songs import song_models, song_schemas
from api.songs.song_constants import ADJECTIVES, NOUNS
from api.tracks import track_models

router = APIRouter(prefix="/api/midi", tags=["midi"])


@router.post("/songs/", response_model=song_schemas.SongDetailResponse)
async def create_song(
    request: song_schemas.CreateSongRequest, user_id: UUID = Depends(get_current_user_id)
) -> song_schemas.SongDetailResponse:
    """
    Create a new song with three default tracks (piano, bass, drums)."""
    try:
        # Auto-generate title if not provided
        title = request.title
        if not title:
            adjective = random.choice(ADJECTIVES)
            noun = random.choice(NOUNS)
            title = f"{adjective} {noun}"

        # Create the song
        song = song_models.MidiSong(
            user_id=str(user_id),
            title=title,
            bpm=request.bpm,
            key=request.key,
            time_signature=request.time_signature,
        )
        with database.get_db() as db:
            db.add(song)
            db.flush()  # Flush to get the song ID without committing

            # Create three default tracks: piano, bass, drums
            tracks_config = [
                {"title": "Piano", "midi_channel": 1, "instrument": "piano", "color": "primary"},
                {"title": "Bass", "midi_channel": 2, "instrument": "bass", "color": "secondary"},
                {"title": "Drums", "midi_channel": 10, "instrument": "drum", "color": "warning"},
            ]

            for config in tracks_config:
                track = track_models.MidiTrack(
                    song_id=song.id,
                    title=config["title"],
                    midi_channel=config["midi_channel"],
                    instrument=config["instrument"],
                    color=config["color"],
                )
                db.add(track)

            db.commit()
            db.refresh(song)

            return song.to_detail_response()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create song: {str(e)}") from e


@router.get("/songs/", response_model=list[song_schemas.SongResponse])
async def list_songs(user_id: UUID = Depends(get_current_user_id)) -> list[song_schemas.SongResponse]:
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
        with database.get_db() as db:
            songs = (
                db.query(song_models.MidiSong)
                .filter(song_models.MidiSong.user_id == str(user_id))
                .order_by(song_models.MidiSong.created_at.desc())
                .all()
            )
            return [song.to_response() for song in songs]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve songs: {str(e)}") from e


@router.get("/songs/{song_id}", response_model=song_schemas.SongDetailResponse)
async def get_song(song_id: str, user_id: UUID = Depends(get_current_user_id)) -> song_schemas.SongDetailResponse:
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
        with database.get_db() as db:
            song = (
                db.query(song_models.MidiSong)
                .filter(song_models.MidiSong.id == song_id, song_models.MidiSong.user_id == str(user_id))
                .first()
            )

            if not song:
                raise HTTPException(status_code=404, detail="Song not found or access denied")

            return song.to_detail_response()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve song: {str(e)}") from e
