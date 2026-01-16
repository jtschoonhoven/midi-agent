"""SQLAlchemy models for instruments."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base
from api.instruments import instrument_schemas
from api.instruments.instrument_constants import INSTRUMENT_TYPES, LICENSE_TYPES
from api.instruments.instrument_types import InstrumentType, LicenseType
from api.midi.midi_constants import MIDI_EVENT_TYPES
from api.midi.midi_types import MidiEventType


class Instrument(Base):
    """A playable instrument with samples."""

    __tablename__ = "instruments"

    # TODO: When migrating to postgres, use the native UUID type instead of a string
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[InstrumentType] = mapped_column(Enum(*INSTRUMENT_TYPES), nullable=False)
    license_type: Mapped[LicenseType] = mapped_column(Enum(*LICENSE_TYPES), nullable=False)
    license_uri: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    samples: Mapped[list["InstrumentSample"]] = relationship(
        "InstrumentSample", back_populates="instrument", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Instrument(id={self.id}, title={self.title}, type={self.type})>"

    def to_response(self) -> "instrument_schemas.InstrumentResponse":
        return instrument_schemas.InstrumentResponse(
            id=self.id,
            title=self.title,
            type=self.type,
            license_type=self.license_type,
            license_uri=self.license_uri,
            samples=[sample.to_response() for sample in self.samples],
        )


class InstrumentSample(Base):
    """A single audio file for a playable instrument."""

    __tablename__ = "instrument_samples"

    # TODO: When migrating to postgres, use the native UUID type instead of a string
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    instrument_id: Mapped[str] = mapped_column(String(36), ForeignKey("instruments.id"), nullable=False, index=True)
    uri: Mapped[str] = mapped_column(Text, nullable=False)
    midi_event: Mapped[MidiEventType] = mapped_column(Enum(*MIDI_EVENT_TYPES), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    instrument: Mapped["Instrument"] = relationship("Instrument", back_populates="samples")

    def __repr__(self) -> str:
        return f"<InstrumentSample(uri={self.uri}, midi_event={self.midi_event})>"

    def to_response(self) -> "instrument_schemas.InstrumentSampleResponse":
        return instrument_schemas.InstrumentSampleResponse(
            id=self.id,
            uri=self.uri,
            midi_event=self.midi_event,
        )
