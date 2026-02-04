import io
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

import numpy as np
from pydub import AudioSegment
from scipy.io import wavfile
from sqlalchemy.orm import Session

from api.instruments import instrument_models
from api.instruments.instrument_types import InstrumentType
from api.loops import loop_models
from api.loops.loop_utils import get_demo_loop_for_instrument
from api.songs import song_models
from api.tracks import track_models
from api.tracks.track_types import TrackColor


def get_track_for_user(db: Session, user_id: str | UUID, track_id: str | UUID) -> Optional["track_models.MidiTrack"]:
    """Fetch the given track from the DB if it exists and belongs to the user, else return None."""
    return (
        db.query(track_models.MidiTrack)
        .join(song_models.MidiSong, track_models.MidiTrack.song_id == song_models.MidiSong.id)
        .filter(track_models.MidiTrack.id == str(track_id), song_models.MidiSong.user_id == str(user_id))
        .first()
    )


def render_loop_to_wav(
    db: Session,
    loop: "loop_models.MidiLoop",
    track: "track_models.MidiTrack",
    song: "song_models.MidiSong",
) -> io.BytesIO:
    """
    Render a loop to a WAV file at 44.1 kHz in memory using instrument samples.

    Args:
        db: Database session
        loop: The loop to render
        track: The track containing the loop (provides instrument type)
        song: The song containing the track (provides BPM and time signature)

    Returns:
        BytesIO object containing the WAV file data

    Raises:
        ValueError: If instrument samples are not found or if there are issues with the audio data
    """
    SAMPLE_RATE = 44100  # 44.1 kHz

    # Get instrument and samples from database
    instrument = (
        db.query(instrument_models.Instrument).filter(instrument_models.Instrument.type == track.instrument).first()
    )

    if not instrument:
        raise ValueError(f"No instrument found for type: {track.instrument}")

    if not instrument.samples:
        raise ValueError(f"No samples found for instrument: {instrument.title}")

    # Build sample map: event name -> file path
    project_root = Path(__file__).parent.parent
    sample_map: dict[str, Path] = {}

    for sample in instrument.samples:
        # sample.uri is like "public/instruments/piano/C4.wav"
        sample_path = project_root / sample.uri
        if sample_path.exists():
            sample_map[sample.midi_event] = sample_path

    if not sample_map:
        raise ValueError(f"No valid sample files found for instrument: {instrument.title}")

    # Parse time signature to get beats per measure
    time_sig_parts = song.time_signature.split("/")
    beats_per_measure = int(time_sig_parts[0])

    # Calculate total duration in seconds (just the loop's measures, no extend_measures)
    beats_per_second = song.bpm / 60.0
    total_beats = loop.measures * beats_per_measure
    total_duration_seconds = total_beats / beats_per_second

    # Create silent audio buffer
    total_samples = int(total_duration_seconds * SAMPLE_RATE)
    audio_buffer = np.zeros(total_samples, dtype=np.float32)

    # Helper function to calculate time in seconds for a MIDI event
    def event_time_in_seconds(measure: int, beat: int, beat_div4: int, beat_div16: int) -> float:
        """Calculate the time in seconds for a MIDI event."""
        # Convert to 0-indexed
        beat_position = (measure - 1) * beats_per_measure + (beat - 1) + (beat_div4 - 1) / 4.0 + (beat_div16 - 1) / 16.0
        return beat_position / beats_per_second

    # Process MIDI events and render
    for event in loop.midi_events:
        # Skip note-off events (value=0) and control change events
        if event.get("value", 0) == 0:
            continue

        event_name = event.get("event")
        if not event_name or event_name not in sample_map:
            continue

        # Calculate event time
        event_time = event_time_in_seconds(
            event["measure"],
            event["beat"],
            event["beat_div4"],
            event["beat_div16"],
        )

        # Skip events beyond the loop duration
        if event_time >= total_duration_seconds:
            continue

        # Load and mix the sample
        try:
            sample_audio = AudioSegment.from_wav(str(sample_map[event_name]))

            # Convert to numpy array at our target sample rate
            if sample_audio.frame_rate != SAMPLE_RATE:
                sample_audio = sample_audio.set_frame_rate(SAMPLE_RATE)

            # Convert to mono if stereo
            if sample_audio.channels > 1:
                sample_audio = sample_audio.set_channels(1)

            # Convert to float32 numpy array (-1.0 to 1.0)
            sample_array = np.array(sample_audio.get_array_of_samples(), dtype=np.float32)
            sample_array = sample_array / (2**15)  # Convert from int16 range to float

            # Apply velocity scaling (0-100 -> 0.0-1.0)
            velocity = event.get("value", 80) / 100.0
            sample_array = sample_array * velocity

            # Calculate start position in the buffer
            start_sample = int(event_time * SAMPLE_RATE)
            end_sample = min(start_sample + len(sample_array), total_samples)

            # Mix the sample into the buffer
            mix_length = end_sample - start_sample
            audio_buffer[start_sample:end_sample] += sample_array[:mix_length]

        except Exception as e:
            print(f"Warning: Failed to load/mix sample {event_name}: {e}")
            continue

    # Normalize to prevent clipping
    max_val = np.abs(audio_buffer).max()
    if max_val > 1.0:
        audio_buffer = audio_buffer / max_val

    # Convert to int16 for WAV file
    audio_int16 = (audio_buffer * 32767).astype(np.int16)

    # Write to BytesIO as WAV
    wav_buffer = io.BytesIO()
    wavfile.write(wav_buffer, SAMPLE_RATE, audio_int16)
    wav_buffer.seek(0)

    return wav_buffer


def get_demo_track_for_instrument(instrument: InstrumentType, song_id: UUID) -> track_models.MidiTrack:
    """
    Get a demo track ORM instance for a given instrument type.
    """
    now = datetime.now()

    title: str = instrument.title()
    midi_channel: int = 1
    color: TrackColor = "primary"

    if instrument == "piano":
        title = "Piano"
        midi_channel = 1
        color = "primary"
    elif instrument == "bass":
        title = "Bass"
        midi_channel = 2
        color = "secondary"
    elif instrument == "drum":
        title = "Drums"
        midi_channel = 10
        color = "error"
    else:
        raise ValueError(f"Unknown instrument type: {instrument}")

    track = track_models.MidiTrack(
        id=uuid.uuid4(),
        song_id=song_id,
        title=title,
        midi_channel=midi_channel,
        instrument=instrument,
        color=color,
        updated_at=now,
        created_at=now,
    )
    # Attach demo loop
    track.loops = [get_demo_loop_for_instrument(instrument, track.id)]

    return track
