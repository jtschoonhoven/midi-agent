import pydantic

from api.midi import midi_models, midi_utils


class GenerateMidiResponse(pydantic.BaseModel):
    """Response from generation model with sparse MIDI events and description."""

    description: str = pydantic.Field(
        description="One-sentence description of the generated loop, describing its musical character, style, or key features"
    )
    midi_events: list["midi_models.GeneratedMidiEvent"] = pydantic.Field(description="List of sparse MIDI events")

    def to_midi_events(self) -> list["midi_models.MidiEvent"]:
        """Convert sparse MIDI events to fully resolved events with explicit timing."""
        return midi_utils.normalize_generated_midi_events(self.midi_events)
