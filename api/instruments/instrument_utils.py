from pathlib import Path

from api import database
from api.instruments import instrument_models
from api.instruments.instrument_constants import INSTRUMENT_DIR_TO_METADATA
from api.midi import midi_utils


def init_db() -> None:
    """
    Load all instruments to the database.
    """
    import logging

    log = logging.getLogger(__name__)

    project_root = Path(__file__).parent.parent
    public_dir = project_root / "public"

    log.info(f"Initializing instruments from {public_dir / 'instruments'}")

    # Delete and rebuild the instruments table
    with database.get_db() as db:
        db.query(instrument_models.Instrument).delete()

        for inst, metadata in INSTRUMENT_DIR_TO_METADATA.items():
            inst_dir = public_dir / "instruments" / inst
            log.info(f"Loading instrument: {inst} from {inst_dir}")

            if not inst_dir.exists():
                log.warning(f"Instrument directory not found: {inst_dir}")
                continue

            instrument = instrument_models.Instrument(
                title=metadata["title"],
                type=metadata["type"],
                license_type=metadata["license_type"],
                license_uri=(inst_dir / "LICENSE.txt").relative_to(project_root).as_posix(),
            )
            db.add(instrument)
            db.flush()  # Flush to get the instrument ID

            sample_count = 0
            for file_path in inst_dir.rglob("*"):
                if file_path.is_file() and file_path.name.lower().endswith(".wav"):
                    filename = file_path.name.split(".")[0]
                    midi_event = midi_utils.str_to_midi_event(filename)

                    if midi_event is None:
                        log.warning(f"Skipping invalid MIDI event filename: {filename}")
                        continue

                    sample = instrument_models.InstrumentSample(
                        instrument_id=instrument.id,
                        uri=file_path.relative_to(project_root).as_posix(),
                        midi_event=midi_event,
                    )
                    db.add(sample)
                    sample_count += 1

            log.info(f"Loaded {sample_count} samples for {inst}")

        db.commit()
        log.info("Instrument initialization complete")
