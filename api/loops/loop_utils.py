from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from api.chats import chat_utils
from api.instruments.instrument_types import InstrumentType
from api.loops import loop_models
from api.songs import song_models
from api.tracks import track_models

# Fixed demo loop IDs (must be hardcoded so frontend can fetch by ID)
DEMO_LOOP_IDS: dict[InstrumentType, UUID] = {
    "piano": UUID("00000000-0000-0000-0000-000000000000"),
    "bass": UUID("22222222-2222-2222-2222-222222222222"),
    "drum": UUID("33333333-3333-3333-3333-333333333333"),
}


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


def get_demo_loop_for_instrument(instrument: InstrumentType, track_id: UUID) -> loop_models.MidiLoop:
    """
    Get a demo loop ORM instance for a given instrument type.
    """
    now = datetime.now()
    loop_id = DEMO_LOOP_IDS[instrument]
    chat_messages = chat_utils.get_demo_chats_for_instrument(instrument, loop_id)
    midi_events = next((chat.midi_events for chat in chat_messages if chat.midi_events is not None), [])

    loop = loop_models.MidiLoop(
        id=loop_id,
        track_id=track_id,
        offset=0,
        measures=4,
        extend_measures=0,
        midi_events=midi_events,
        chat_messages=chat_messages,
        created_at=now,
        updated_at=now,
    )

    return loop
