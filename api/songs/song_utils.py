from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from api.songs import song_models


def get_song_for_user(db: Session, user_id: str | UUID, song_id: str | UUID) -> Optional["song_models.MidiSong"]:
    """Fetch the given song from the DB if it exists and belongs to the user, else return None."""
    return (
        db.query(song_models.MidiSong)
        .filter(song_models.MidiSong.id == str(song_id), song_models.MidiSong.user_id == str(user_id))
        .first()
    )
