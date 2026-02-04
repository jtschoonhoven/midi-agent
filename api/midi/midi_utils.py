import logging
import re
from typing import cast

from api.audio.audio_types import Chord
from api.midi import midi_models
from api.midi.midi_constants import MIDI_EVENT_TO_HEX, MIDI_EVENT_TYPES
from api.midi.midi_types import MidiEventType

log = logging.getLogger(__name__)

REGEX_NON_ALPHANUM = re.compile(r"[^a-zA-Z0-9]")


def normalize_generated_midi_events(events: list["midi_models.GeneratedMidiEvent"]) -> list["midi_models.MidiEvent"]:
    """Convert sparse GeneratedMidiEvent list to fully resolved MidiEvent list."""
    result: list[midi_models.MidiEvent] = []

    chord: Chord | None = None
    measure = 1
    beat = 1
    beat_div4 = 1
    beat_div16 = 1

    for item in events:
        event = str_to_midi_event(item.event)
        if event is None:
            log.warning(f"Skipping invalid MIDI event: {item.event}")
            continue

        if item.chord and item.chord != chord:
            chord = item.chord
        if item.measure and item.measure != measure:
            measure = item.measure
            beat = 1
            beat_div4 = 1
            beat_div16 = 1
        if item.beat and item.beat != beat:
            beat = item.beat
            beat_div4 = 1
            beat_div16 = 1
        if item.beat_div4 and item.beat_div4 != beat_div4:
            beat_div4 = item.beat_div4
            beat_div16 = 1
        if item.beat_div16 and item.beat_div16 != beat_div16:
            beat_div16 = item.beat_div16

        result.append(
            midi_models.MidiEvent(
                chord=chord,
                measure=measure,
                beat=beat,
                beat_div4=beat_div4,
                beat_div16=beat_div16,
                event=event,
                value=item.value,
            )
        )

    return result


def str_to_midi_event(s: str) -> MidiEventType | None:
    """
    Return the matching MidiEventType or None if no match is found.
    """
    if s in MIDI_EVENT_TO_HEX:
        return cast(MidiEventType, s)
    elif (ev := s.upper()) in MIDI_EVENT_TYPES:
        return cast(MidiEventType, ev)
    elif (ev := s.lower()) in MIDI_EVENT_TYPES:
        return cast(MidiEventType, ev)
    elif (ev := re.sub(REGEX_NON_ALPHANUM, "", s).lower()) in MIDI_EVENT_TYPES:
        return cast(MidiEventType, ev)
    return None
