from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from api.loops import loop_models
from api.songs import song_models
from api.tracks import track_models


def get_loop_for_user(db: Session, user_id: str | UUID, loop_id: str | UUID) -> Optional["loop_models.MidiLoop"]:
    """Fetch the given loop from the DB if it exists and belongs to the user, else return None."""
    return (
        db.query(loop_models.MidiLoop)
        .join(track_models.MidiTrack, loop_models.MidiLoop.track_id == track_models.MidiTrack.id)
        .join(song_models.MidiSong, track_models.MidiTrack.song_id == song_models.MidiSong.id)
        .options(joinedload(loop_models.MidiLoop.chat_messages))
        .filter(loop_models.MidiLoop.id == str(loop_id), song_models.MidiSong.user_id == str(user_id))
        .first()
    )
