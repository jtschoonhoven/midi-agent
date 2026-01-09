import time
from midiagent.ai import MidiEvent
from midiagent.midi_widget import MidiWidget
from midiagent.types import TimeSignature


def play_midi(bpm: int, time_signature: TimeSignature, events: list[MidiEvent], midi: MidiWidget) -> None:
    idx = 0
    batch: list[MidiEvent] = []
    started_at = time.time()

    while idx < len(events):
        event = events[idx]
        elapsed = time.time() - started_at
        event_time = event.timestamp(bpm, time_signature)
        if event_time <= elapsed:
            idx += 1
            batch.append(event)
        elif batch:
            midi.events = [event.payload() for event in batch]
            batch = []
