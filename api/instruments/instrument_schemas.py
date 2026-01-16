import pydantic

from api.instruments.instrument_types import InstrumentType, LicenseType
from api.midi.midi_types import MidiEventType


class InstrumentSampleResponse(pydantic.BaseModel):
    """Response model for instrument samples."""

    id: str = pydantic.Field(description="Sample ID")
    uri: str = pydantic.Field(description="Sample URI")
    midi_event: MidiEventType = pydantic.Field(description="MIDI event name")


class InstrumentResponse(pydantic.BaseModel):
    """Response model for instruments."""

    id: str = pydantic.Field(description="Instrument ID")
    title: str = pydantic.Field(description="Instrument title")
    type: InstrumentType = pydantic.Field(description="Instrument type")
    license_type: LicenseType = pydantic.Field(description="Instrument license type")
    license_uri: str = pydantic.Field(description="Instrument license URI")
    samples: list[InstrumentSampleResponse] = pydantic.Field(description="Instrument samples")


class ListInstrumentsResponse(pydantic.BaseModel):
    """Response model for listing instruments."""

    instruments: list[InstrumentResponse] = pydantic.Field(description="Instruments")
