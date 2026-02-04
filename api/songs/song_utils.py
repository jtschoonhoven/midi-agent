import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session, make_transient

from api.songs import song_models
from api.tracks.track_utils import get_demo_track_for_instrument

DEMO_SONG_ID = UUID("00000000-0000-0000-0000-000000000000")


def get_song_for_user(db: Session, user_id: str | UUID, song_id: str | UUID) -> Optional["song_models.MidiSong"]:
    """Fetch the given song from the DB if it exists and belongs to the user, else return None."""
    return (
        db.query(song_models.MidiSong)
        .filter(song_models.MidiSong.id == str(song_id), song_models.MidiSong.user_id == str(user_id))
        .first()
    )


def get_demo_song() -> song_models.MidiSong:
    """
    Get the demo song as an ORM model instance (not persisted to DB).

    The returned song has tracks and loops attached as relationships.
    """
    now = datetime.now()

    song = song_models.MidiSong(
        id=DEMO_SONG_ID,
        user_id=uuid.uuid4(),
        title="Demo Song",
        bpm=120,
        key="C",
        time_signature="4/4",
        created_at=now,
        updated_at=now,
    )
    # Attach demo tracks (which have loops attached)
    song.tracks = [
        get_demo_track_for_instrument("piano", DEMO_SONG_ID),
        get_demo_track_for_instrument("bass", DEMO_SONG_ID),
        get_demo_track_for_instrument("drum", DEMO_SONG_ID),
    ]

    return song


def create_demo_song_for_user(db: Session, user_id: UUID) -> song_models.MidiSong:
    """
    Create a copy of the demo song for a new user.

    This creates real database records that the user can then modify.
    Uses get_demo_song() as the source, clears IDs, and persists to DB.
    """
    song = get_demo_song()

    # Make transient and clear ID so DB generates a new one
    make_transient(song)
    song.id = None  # type: ignore[assignment]
    song.user_id = user_id
    db.add(song)
    db.flush()

    for track in song.tracks:
        make_transient(track)
        track.id = None  # type: ignore[assignment]
        track.song_id = song.id
        db.add(track)
        db.flush()

        for loop in track.loops:
            make_transient(loop)
            loop.id = None  # type: ignore[assignment]
            loop.track_id = track.id
            db.add(loop)
            db.flush()

            for chat in loop.chat_messages:
                make_transient(chat)
                chat.id = None  # type: ignore[assignment]
                chat.loop_id = loop.id
                db.add(chat)

    return song
