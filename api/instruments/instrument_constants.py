from typing import TypedDict

from api.instruments.instrument_types import InstrumentType, LicenseType

LICENSE_TYPES: list[LicenseType] = ["GNU_GPL_V3", "BSD3"]
INSTRUMENT_TYPES: list[InstrumentType] = ["piano", "bass", "drum"]


class _InstrumentMetadata(TypedDict):
    title: str
    type: InstrumentType
    license_type: LicenseType


# Metadata for local sample directories
INSTRUMENT_DIR_TO_METADATA: dict[str, _InstrumentMetadata] = {
    "piano": {"title": "Piano", "type": "piano", "license_type": "GNU_GPL_V3"},
    "bass": {"title": "Bass", "type": "bass", "license_type": "GNU_GPL_V3"},
    "drum": {"title": "Drum", "type": "drum", "license_type": "BSD3"},
}
