"""Utility functions for chat messages, including demo data."""

import uuid
from datetime import datetime
from uuid import UUID

from api.chats import chat_models
from api.instruments.instrument_types import InstrumentType
from api.midi import midi_models, midi_utils

# Demo chat message content for each instrument
DEMO_CHAT_CONTENT: dict[InstrumentType, tuple[str, str]] = {
    "piano": (
        "Create a simple 4-bar chord progression in C major",
        "A classic I-vi-IV-V (C-Am-F-G) chord progression with sustained chords and melodic fills.",
    ),
    "bass": (
        "Add a bass line that follows the chord roots",
        "A supportive bass line following the root notes of each chord with a steady rhythm.",
    ),
    "drum": (
        "Create a basic rock drum beat",
        "A standard rock beat with kick on 1 and 3, snare on 2 and 4, and steady hi-hats.",
    ),
}


def get_demo_chats_for_instrument(instrument: InstrumentType, loop_id: UUID) -> list["chat_models.ChatMessage"]:
    """
    Return a demo user and assistant chat message for a given instrument.
    """
    now = datetime.now()
    user_msg, assistant_msg = DEMO_CHAT_CONTENT[instrument]
    midi_events = get_demo_midi_events_for_instrument(instrument)

    return [
        chat_models.ChatMessage(
            id=uuid.uuid4(),
            loop_id=loop_id,
            role="user",
            msg=user_msg,
            midi_events=None,
            created_at=now,
            updated_at=now,
        ),
        chat_models.ChatMessage(
            id=uuid.uuid4(),
            loop_id=loop_id,
            role="assistant",
            msg=assistant_msg,
            midi_events=midi_events,
            created_at=now,
            updated_at=now,
        ),
    ]


def get_demo_midi_events_for_instrument(instrument: InstrumentType) -> list["midi_models.MidiEvent"]:
    """
    Get demo MIDI events for a given instrument type.
    """
    if instrument == "piano":
        return _get_demo_midi_events_piano()
    elif instrument == "bass":
        return _get_demo_midi_events_bass()
    elif instrument == "drum":
        return _get_demo_midi_events_drum()
    else:
        raise ValueError(f"Unknown instrument type: {instrument}")


def _get_demo_midi_events_piano() -> list["midi_models.MidiEvent"]:
    """Get demo MIDI events for piano: C - Am - F - G chord progression."""
    events = [
        # Measure 1: C major chord (C-E-G)
        midi_models.GeneratedMidiEvent(measure=1, beat=1, event="C4", value=70, chord="I"),
        midi_models.GeneratedMidiEvent(measure=1, beat=1, event="E4", value=65, chord="I"),
        midi_models.GeneratedMidiEvent(measure=1, beat=1, event="G4", value=60, chord="I"),
        midi_models.GeneratedMidiEvent(measure=1, beat=3, event="C4", value=0, chord="I"),  # note off
        midi_models.GeneratedMidiEvent(measure=1, beat=3, event="E4", value=0, chord="I"),
        midi_models.GeneratedMidiEvent(measure=1, beat=3, event="G4", value=0, chord="I"),
        midi_models.GeneratedMidiEvent(measure=1, beat=3, event="E4", value=55, chord="I"),
        midi_models.GeneratedMidiEvent(measure=1, beat=4, event="E4", value=0, chord="I"),
        midi_models.GeneratedMidiEvent(measure=1, beat=4, event="G4", value=55, chord="I"),
        midi_models.GeneratedMidiEvent(measure=1, beat=4, event="G4", value=0, chord="I", beat_div4=3),
        # Measure 2: A minor chord (A-C-E)
        midi_models.GeneratedMidiEvent(measure=2, beat=1, event="A3", value=70, chord="VI"),
        midi_models.GeneratedMidiEvent(measure=2, beat=1, event="C4", value=65, chord="VI"),
        midi_models.GeneratedMidiEvent(measure=2, beat=1, event="E4", value=60, chord="VI"),
        midi_models.GeneratedMidiEvent(measure=2, beat=3, event="A3", value=0, chord="VI"),
        midi_models.GeneratedMidiEvent(measure=2, beat=3, event="C4", value=0, chord="VI"),
        midi_models.GeneratedMidiEvent(measure=2, beat=3, event="E4", value=0, chord="VI"),
        midi_models.GeneratedMidiEvent(measure=2, beat=3, event="C4", value=55, chord="VI"),
        midi_models.GeneratedMidiEvent(measure=2, beat=4, event="C4", value=0, chord="VI"),
        midi_models.GeneratedMidiEvent(measure=2, beat=4, event="E4", value=55, chord="VI"),
        midi_models.GeneratedMidiEvent(measure=2, beat=4, event="E4", value=0, chord="VI"),
        # Measure 3: F major chord (F-A-C)
        midi_models.GeneratedMidiEvent(measure=3, beat=1, event="F3", value=70, chord="IV"),
        midi_models.GeneratedMidiEvent(measure=3, beat=1, event="A3", value=65, chord="IV"),
        midi_models.GeneratedMidiEvent(measure=3, beat=1, event="C4", value=60, chord="IV"),
        midi_models.GeneratedMidiEvent(measure=3, beat=3, event="F3", value=0, chord="IV"),
        midi_models.GeneratedMidiEvent(measure=3, beat=3, event="A3", value=0, chord="IV"),
        midi_models.GeneratedMidiEvent(measure=3, beat=3, event="C4", value=0, chord="IV"),
        midi_models.GeneratedMidiEvent(measure=3, beat=3, event="A3", value=55, chord="IV"),
        midi_models.GeneratedMidiEvent(measure=3, beat=4, event="A3", value=0, chord="IV"),
        midi_models.GeneratedMidiEvent(measure=3, beat=4, event="C4", value=55, chord="IV"),
        midi_models.GeneratedMidiEvent(measure=3, beat=4, event="C4", value=0, chord="IV"),
        # Measure 4: G major chord (G-B-D)
        midi_models.GeneratedMidiEvent(measure=4, beat=1, event="G3", value=70, chord="V"),
        midi_models.GeneratedMidiEvent(measure=4, beat=1, event="B3", value=65, chord="V"),
        midi_models.GeneratedMidiEvent(measure=4, beat=1, event="D4", value=60, chord="V"),
        midi_models.GeneratedMidiEvent(measure=4, beat=3, event="G3", value=0, chord="V"),
        midi_models.GeneratedMidiEvent(measure=4, beat=3, event="B3", value=0, chord="V"),
        midi_models.GeneratedMidiEvent(measure=4, beat=3, event="D4", value=0, chord="V"),
        midi_models.GeneratedMidiEvent(measure=4, beat=3, event="B3", value=55, chord="V"),
        midi_models.GeneratedMidiEvent(measure=4, beat=4, event="B3", value=0, chord="V"),
        midi_models.GeneratedMidiEvent(measure=4, beat=4, event="D4", value=55, chord="V"),
        midi_models.GeneratedMidiEvent(measure=4, beat=4, event="D4", value=0, chord="V"),
    ]
    return midi_utils.normalize_generated_midi_events(events)


def _get_demo_midi_events_bass() -> list["midi_models.MidiEvent"]:
    """Get demo MIDI events for bass: root notes following the chord progression."""
    events = [
        # Measure 1: C
        midi_models.GeneratedMidiEvent(measure=1, beat=1, event="C2", value=80, chord="I"),
        midi_models.GeneratedMidiEvent(measure=1, beat=3, event="C2", value=0, chord="I"),
        midi_models.GeneratedMidiEvent(measure=1, beat=3, event="C2", value=70, chord="I"),
        midi_models.GeneratedMidiEvent(measure=1, beat=4, event="C2", value=0, chord="I"),
        # Measure 2: A
        midi_models.GeneratedMidiEvent(measure=2, beat=1, event="A1", value=80, chord="VI"),
        midi_models.GeneratedMidiEvent(measure=2, beat=3, event="A1", value=0, chord="VI"),
        midi_models.GeneratedMidiEvent(measure=2, beat=3, event="A1", value=70, chord="VI"),
        midi_models.GeneratedMidiEvent(measure=2, beat=4, event="A1", value=0, chord="VI"),
        # Measure 3: F
        midi_models.GeneratedMidiEvent(measure=3, beat=1, event="F1", value=80, chord="IV"),
        midi_models.GeneratedMidiEvent(measure=3, beat=3, event="F1", value=0, chord="IV"),
        midi_models.GeneratedMidiEvent(measure=3, beat=3, event="F1", value=70, chord="IV"),
        midi_models.GeneratedMidiEvent(measure=3, beat=4, event="F1", value=0, chord="IV"),
        # Measure 4: G
        midi_models.GeneratedMidiEvent(measure=4, beat=1, event="G1", value=80, chord="V"),
        midi_models.GeneratedMidiEvent(measure=4, beat=3, event="G1", value=0, chord="V"),
        midi_models.GeneratedMidiEvent(measure=4, beat=3, event="G1", value=70, chord="V"),
        midi_models.GeneratedMidiEvent(measure=4, beat=4, event="G1", value=0, chord="V"),
    ]
    return midi_utils.normalize_generated_midi_events(events)


def _get_demo_midi_events_drum() -> list["midi_models.MidiEvent"]:
    """Get demo MIDI events for drums: basic rock beat."""
    GeneratedMidiEvent = midi_models.GeneratedMidiEvent
    events: list[midi_models.GeneratedMidiEvent] = [
        # Measure 1
        # Beat 1: kick + hi-hat
        GeneratedMidiEvent(measure=1, beat=1, event="closedhihat", value=60),
        GeneratedMidiEvent(measure=1, beat=1, event="acousticbassdrum", value=85),
        GeneratedMidiEvent(measure=1, beat=1, event="closedhihat", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=1, beat=1, event="acousticbassdrum", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=1, beat=1, event="closedhihat", value=55, beat_div4=3),
        GeneratedMidiEvent(measure=1, beat=1, event="closedhihat", value=0, beat_div4=4),
        # Beat 2: snare + hi-hat
        GeneratedMidiEvent(measure=1, beat=2, event="closedhihat", value=60),
        GeneratedMidiEvent(measure=1, beat=2, event="acousticsnare", value=80),
        GeneratedMidiEvent(measure=1, beat=2, event="closedhihat", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=1, beat=2, event="acousticsnare", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=1, beat=2, event="closedhihat", value=55, beat_div4=3),
        GeneratedMidiEvent(measure=1, beat=2, event="closedhihat", value=0, beat_div4=4),
        # Beat 3: kick + hi-hat
        GeneratedMidiEvent(measure=1, beat=3, event="closedhihat", value=60),
        GeneratedMidiEvent(measure=1, beat=3, event="acousticbassdrum", value=80),
        GeneratedMidiEvent(measure=1, beat=3, event="closedhihat", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=1, beat=3, event="acousticbassdrum", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=1, beat=3, event="closedhihat", value=55, beat_div4=3),
        GeneratedMidiEvent(measure=1, beat=3, event="closedhihat", value=0, beat_div4=4),
        # Beat 4: snare + hi-hat
        GeneratedMidiEvent(measure=1, beat=4, event="closedhihat", value=60),
        GeneratedMidiEvent(measure=1, beat=4, event="acousticsnare", value=80),
        GeneratedMidiEvent(measure=1, beat=4, event="closedhihat", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=1, beat=4, event="acousticsnare", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=1, beat=4, event="closedhihat", value=55, beat_div4=3),
        GeneratedMidiEvent(measure=1, beat=4, event="closedhihat", value=0, beat_div4=4),
        # Measure 2
        # Beat 1: kick + hi-hat
        GeneratedMidiEvent(measure=2, beat=1, event="closedhihat", value=60),
        GeneratedMidiEvent(measure=2, beat=1, event="acousticbassdrum", value=85),
        GeneratedMidiEvent(measure=2, beat=1, event="closedhihat", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=2, beat=1, event="acousticbassdrum", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=2, beat=1, event="closedhihat", value=55, beat_div4=3),
        GeneratedMidiEvent(measure=2, beat=1, event="closedhihat", value=0, beat_div4=4),
        # Beat 2: snare + hi-hat
        GeneratedMidiEvent(measure=2, beat=2, event="closedhihat", value=60),
        GeneratedMidiEvent(measure=2, beat=2, event="acousticsnare", value=80),
        GeneratedMidiEvent(measure=2, beat=2, event="closedhihat", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=2, beat=2, event="acousticsnare", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=2, beat=2, event="closedhihat", value=55, beat_div4=3),
        GeneratedMidiEvent(measure=2, beat=2, event="closedhihat", value=0, beat_div4=4),
        # Beat 3: kick + hi-hat
        GeneratedMidiEvent(measure=2, beat=3, event="closedhihat", value=60),
        GeneratedMidiEvent(measure=2, beat=3, event="acousticbassdrum", value=80),
        GeneratedMidiEvent(measure=2, beat=3, event="closedhihat", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=2, beat=3, event="acousticbassdrum", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=2, beat=3, event="closedhihat", value=55, beat_div4=3),
        GeneratedMidiEvent(measure=2, beat=3, event="closedhihat", value=0, beat_div4=4),
        # Beat 4: snare + hi-hat
        GeneratedMidiEvent(measure=2, beat=4, event="closedhihat", value=60),
        GeneratedMidiEvent(measure=2, beat=4, event="acousticsnare", value=80),
        GeneratedMidiEvent(measure=2, beat=4, event="closedhihat", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=2, beat=4, event="acousticsnare", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=2, beat=4, event="closedhihat", value=55, beat_div4=3),
        GeneratedMidiEvent(measure=2, beat=4, event="closedhihat", value=0, beat_div4=4),
        # Measure 3
        # Beat 1: kick + hi-hat
        GeneratedMidiEvent(measure=3, beat=1, event="closedhihat", value=60),
        GeneratedMidiEvent(measure=3, beat=1, event="acousticbassdrum", value=85),
        GeneratedMidiEvent(measure=3, beat=1, event="closedhihat", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=3, beat=1, event="acousticbassdrum", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=3, beat=1, event="closedhihat", value=55, beat_div4=3),
        GeneratedMidiEvent(measure=3, beat=1, event="closedhihat", value=0, beat_div4=4),
        # Beat 2: snare + hi-hat
        GeneratedMidiEvent(measure=3, beat=2, event="closedhihat", value=60),
        GeneratedMidiEvent(measure=3, beat=2, event="acousticsnare", value=80),
        GeneratedMidiEvent(measure=3, beat=2, event="closedhihat", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=3, beat=2, event="acousticsnare", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=3, beat=2, event="closedhihat", value=55, beat_div4=3),
        GeneratedMidiEvent(measure=3, beat=2, event="closedhihat", value=0, beat_div4=4),
        # Beat 3: kick + hi-hat
        GeneratedMidiEvent(measure=3, beat=3, event="closedhihat", value=60),
        GeneratedMidiEvent(measure=3, beat=3, event="acousticbassdrum", value=80),
        GeneratedMidiEvent(measure=3, beat=3, event="closedhihat", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=3, beat=3, event="acousticbassdrum", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=3, beat=3, event="closedhihat", value=55, beat_div4=3),
        GeneratedMidiEvent(measure=3, beat=3, event="closedhihat", value=0, beat_div4=4),
        # Beat 4: snare + hi-hat
        GeneratedMidiEvent(measure=3, beat=4, event="closedhihat", value=60),
        GeneratedMidiEvent(measure=3, beat=4, event="acousticsnare", value=80),
        GeneratedMidiEvent(measure=3, beat=4, event="closedhihat", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=3, beat=4, event="acousticsnare", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=3, beat=4, event="closedhihat", value=55, beat_div4=3),
        GeneratedMidiEvent(measure=3, beat=4, event="closedhihat", value=0, beat_div4=4),
        # Measure 4
        # Beat 1: kick + hi-hat
        GeneratedMidiEvent(measure=4, beat=1, event="closedhihat", value=60),
        GeneratedMidiEvent(measure=4, beat=1, event="acousticbassdrum", value=85),
        GeneratedMidiEvent(measure=4, beat=1, event="closedhihat", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=4, beat=1, event="acousticbassdrum", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=4, beat=1, event="closedhihat", value=55, beat_div4=3),
        GeneratedMidiEvent(measure=4, beat=1, event="closedhihat", value=0, beat_div4=4),
        # Beat 2: snare + hi-hat
        GeneratedMidiEvent(measure=4, beat=2, event="closedhihat", value=60),
        GeneratedMidiEvent(measure=4, beat=2, event="acousticsnare", value=80),
        GeneratedMidiEvent(measure=4, beat=2, event="closedhihat", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=4, beat=2, event="acousticsnare", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=4, beat=2, event="closedhihat", value=55, beat_div4=3),
        GeneratedMidiEvent(measure=4, beat=2, event="closedhihat", value=0, beat_div4=4),
        # Beat 3: kick + hi-hat
        GeneratedMidiEvent(measure=4, beat=3, event="closedhihat", value=60),
        GeneratedMidiEvent(measure=4, beat=3, event="acousticbassdrum", value=80),
        GeneratedMidiEvent(measure=4, beat=3, event="closedhihat", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=4, beat=3, event="acousticbassdrum", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=4, beat=3, event="closedhihat", value=55, beat_div4=3),
        GeneratedMidiEvent(measure=4, beat=3, event="closedhihat", value=0, beat_div4=4),
        # Beat 4: snare + hi-hat
        GeneratedMidiEvent(measure=4, beat=4, event="closedhihat", value=60),
        GeneratedMidiEvent(measure=4, beat=4, event="acousticsnare", value=80),
        GeneratedMidiEvent(measure=4, beat=4, event="closedhihat", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=4, beat=4, event="acousticsnare", value=0, beat_div4=2),
        GeneratedMidiEvent(measure=4, beat=4, event="closedhihat", value=55, beat_div4=3),
        GeneratedMidiEvent(measure=4, beat=4, event="closedhihat", value=0, beat_div4=4),
    ]

    return midi_utils.normalize_generated_midi_events(events)
