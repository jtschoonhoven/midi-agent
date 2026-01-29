"""FastAPI routes for audio rendering."""

from fastapi import APIRouter
from sqlalchemy.orm import joinedload

from api import database
from api.instruments import instrument_models, instrument_schemas

router = APIRouter(prefix="/api/midi", tags=["audio"])


@router.get("/instruments", response_model=instrument_schemas.ListInstrumentsResponse)
async def list_instruments() -> "instrument_schemas.ListInstrumentsResponse":
    """
    List all instrument samples in the public/instruments folder.
    """
    with database.get_db() as db:
        instruments = (
            db.query(instrument_models.Instrument).options(joinedload(instrument_models.Instrument.samples)).all()
        )
        return instrument_schemas.ListInstrumentsResponse(instruments=[inst.to_response() for inst in instruments])
