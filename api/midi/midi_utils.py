import re
from typing import cast

from api.midi.midi_constants import MIDI_EVENT_TO_HEX, MIDI_EVENT_TYPES
from api.midi.midi_types import MidiEventType

REGEX_NON_ALPHANUM = re.compile(r"[^a-zA-Z0-9]")


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
