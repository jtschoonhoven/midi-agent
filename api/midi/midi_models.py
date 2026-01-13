# Pydantic models used by this module
import pydantic

from api.audio.audio_types import Chord
from api.midi.midi_types import MidiEventType


class MidiEvent(pydantic.BaseModel):
    """A fully resolved MIDI event with explicit timing."""

    chord: Chord | None = pydantic.Field(description="Underlying chord in the progression (does not necessarily match the current note)")
    measure: int = pydantic.Field(gt=0, description="The measure, starting from 1")
    beat: int = pydantic.Field(gt=0, lt=9, description="The beat within the measure, starting from 1")
    beat_div4: int = pydantic.Field(gt=0, lt=9, description="Divides the beat into quarters (16th notes)")
    beat_div16: int = pydantic.Field(gt=0, lt=9, description="Divides the beat into 16ths (64th notes)")
    event: MidiEventType = pydantic.Field(description="MIDI note or CC event")
    value: int = pydantic.Field(ge=0, le=100, description="Velocity or CC value, scaled 0-100")