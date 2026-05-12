# Pydantic models used by this module
import logging

import pydantic

from api.audio.audio_types import Chord
from api.midi.midi_types import MidiEventType

log = logging.getLogger(__name__)


class MidiEvent(pydantic.BaseModel):
    """A fully resolved MIDI event with explicit timing."""

    chord: Chord | None = pydantic.Field(
        description="Underlying chord in the progression (does not necessarily match the current note)"
    )
    measure: int = pydantic.Field(gt=0, description="The measure, starting from 1")
    beat: int = pydantic.Field(gt=0, lt=9, description="The beat within the measure, starting from 1")
    beat_div4: int = pydantic.Field(gt=0, lt=9, description="Divides the beat into quarters (16th notes)")
    beat_div16: int = pydantic.Field(gt=0, lt=9, description="Divides the beat into 16ths (64th notes)")
    event: MidiEventType = pydantic.Field(description="MIDI note or CC event")
    value: int = pydantic.Field(ge=0, le=100, description="Velocity or CC value, scaled 0-100")


class GeneratedMidiEvent(pydantic.BaseModel):
    """A MIDI event with optional timing fields (for LLM generation)."""

    chord: Chord | None = pydantic.Field(
        default=None, description="Underlying chord in the progression (does not necessarily match the current note)"
    )
    measure: int | None = pydantic.Field(None, gt=0, description="The measure, starting from 1")
    beat: int | None = pydantic.Field(None, gt=0, lt=9, description="The beat within the measure, starting from 1")
    beat_div4: int | None = pydantic.Field(None, gt=0, lt=9, description="Divides the beat into quarters")
    beat_div16: int | None = pydantic.Field(None, gt=0, lt=9, description="Divides the beat into 16ths")
    event: str = pydantic.Field(
        description='MIDI note, cc, or GM drum name: "C#4", "Sustain", "Open Hi-Hat'
    )
    value: int = pydantic.Field(ge=0, le=100, description="Velocity or CC value, scaled 0-100")
