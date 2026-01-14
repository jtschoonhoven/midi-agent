from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from api.songs import song_models
from api.tracks import track_models


def get_track_for_user(db: Session, user_id: str | UUID, track_id: str | UUID) -> Optional["track_models.MidiTrack"]:
    """Fetch the given track from the DB if it exists and belongs to the user, else return None."""
    return (
        db.query(track_models.MidiTrack)
        .join(song_models.MidiSong, track_models.MidiTrack.song_id == song_models.MidiSong.id)
        .filter(track_models.MidiTrack.id == str(track_id), song_models.MidiSong.user_id == str(user_id))
        .first()
    )
