"""MIDI file creation and manipulation utilities."""

import re

import mido
from mido import Message, MidiFile, MidiTrack

from api.audio.audio_types import MidiEvent


def note_name_to_midi_number(note_name: str) -> int | None:
    """Convert note name to MIDI note number (e.g., 'C4' -> 60)."""
    note_map = {
        "C": 0,
        "C#": 1,
        "Db": 1,
        "D": 2,
        "D#": 3,
        "Eb": 3,
        "E": 4,
        "F": 5,
        "F#": 6,
        "Gb": 6,
        "G": 7,
        "G#": 8,
        "Ab": 8,
        "A": 9,
        "A#": 10,
        "Bb": 10,
        "B": 11,
    }

    match = re.match(r"^([A-G][b#]?)(-?\d+)$", note_name)
    if not match:
        return None

    note, octave = match.groups()
    note_value = note_map.get(note)
    if note_value is None:
        return None

    return (int(octave) + 1) * 12 + note_value


def create_midi_file(midi_events: list[MidiEvent], bpm: int, time_signature: str = "4/4") -> MidiFile:
    """Create a MIDI file from MIDI events."""
    mid = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    mid.tracks.append(track)

    # Add tempo (microseconds per beat)
    tempo = mido.bpm2tempo(bpm)
    track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))

    # Add time signature
    numerator, denominator = map(int, time_signature.split("/"))
    track.append(mido.MetaMessage("time_signature", numerator=numerator, denominator=denominator, time=0))

    # Convert events to MIDI messages with delta times
    # Events are already sorted by time, but we need to calculate deltas
    previous_ticks = 0

    # Extract beats per measure from time signature
    beats_per_measure = numerator

    for event in midi_events:
        # Calculate absolute tick time
        beat_time = (
            (event.measure - 1) * beats_per_measure
            + (event.beat - 1)
            + (event.beat_div4 - 1) / 4
            + (event.beat_div16 - 1) / 16
        )
        ticks = int(beat_time * mid.ticks_per_beat)

        # Calculate delta time from previous event
        delta = ticks - previous_ticks
        previous_ticks = ticks

        # Convert MIDI event to mido Message
        midi_note = note_name_to_midi_number(event.event)

        if midi_note is not None:
            # Scale velocity from 0-100 to 0-127
            velocity = int((event.value / 100) * 127)

            if velocity > 0:
                # Note on
                track.append(Message("note_on", note=midi_note, velocity=velocity, time=delta))
            else:
                # Note off
                track.append(Message("note_off", note=midi_note, velocity=0, time=delta))
        else:
            # Handle control change messages
            if event.event == "Sustain":
                cc_value = int((event.value / 100) * 127)
                track.append(Message("control_change", control=64, value=cc_value, time=delta))
            elif event.event == "ModWheel":
                cc_value = int((event.value / 100) * 127)
                track.append(Message("control_change", control=1, value=cc_value, time=delta))
            elif event.event == "AllNotesOff":
                track.append(Message("control_change", control=123, value=0, time=delta))
            elif event.event == "ResetControllers":
                track.append(Message("control_change", control=121, value=0, time=delta))

    return mid
