"""MIDI to audio rendering using FluidSynth."""

import os
import tempfile
import wave
from pathlib import Path

import fluidsynth
import mido
from mido import Message, MidiFile, MidiTrack

from api.midi.midi_utils import MidiEvent


def get_soundfont_path() -> str:
    """Get the path to the soundfont file."""
    # Check for SOUNDFONT_DIR environment variable
    soundfont_dir = os.getenv("SOUNDFONT_DIR")

    if soundfont_dir:
        # Use custom soundfont directory
        soundfont_path = Path(soundfont_dir) / "FluidR3_GM.sf2"
    else:
        # Use default location at api/soundfonts
        project_root = Path(__file__).parent.parent.parent
        soundfont_path = project_root / "api" / "soundfonts" / "FluidR3_GM.sf2"

    if not soundfont_path.exists():
        raise FileNotFoundError(
            f"Soundfont not found at {soundfont_path}. "
            f"Please ensure FluidR3_GM.sf2 exists in the soundfont directory. "
            f"You can set a custom directory with the SOUNDFONT_DIR environment variable."
        )

    return str(soundfont_path)


def note_name_to_midi_number(note_name: str) -> int | None:
    """Convert note name to MIDI note number (e.g., 'C4' -> 60)."""
    note_map = {
        "C": 0,
        "C#": 1,
        "Db": 1,
        "D": 2,
        "D#": 3,
        "Eb": 3,
        "E": 4,
        "F": 5,
        "F#": 6,
        "Gb": 6,
        "G": 7,
        "G#": 8,
        "Ab": 8,
        "A": 9,
        "A#": 10,
        "Bb": 10,
        "B": 11,
    }

    # Parse note name like "C4" or "C#4"
    import re

    match = re.match(r"^([A-G][b#]?)(-?\d+)$", note_name)
    if not match:
        return None

    note, octave = match.groups()
    note_value = note_map.get(note)
    if note_value is None:
        return None

    return (int(octave) + 1) * 12 + note_value


def create_midi_file(midi_events: list[MidiEvent], bpm: int, time_signature: str = "4/4") -> MidiFile:
    """Create a MIDI file from MIDI events."""
    mid = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    mid.tracks.append(track)

    # Add tempo (microseconds per beat)
    tempo = mido.bpm2tempo(bpm)
    track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))

    # Add time signature
    numerator, denominator = map(int, time_signature.split("/"))
    track.append(mido.MetaMessage("time_signature", numerator=numerator, denominator=denominator, time=0))

    # Convert events to MIDI messages with delta times
    # Events are already sorted by time, but we need to calculate deltas
    previous_ticks = 0

    # Extract beats per measure from time signature
    beats_per_measure = numerator

    for event in midi_events:
        # Calculate absolute tick time
        beat_time = (
            (event.measure - 1) * beats_per_measure
            + (event.beat - 1)
            + (event.beat_div4 - 1) / 4
            + (event.beat_div16 - 1) / 16
        )
        ticks = int(beat_time * mid.ticks_per_beat)

        # Calculate delta time from previous event
        delta = ticks - previous_ticks
        previous_ticks = ticks

        # Convert MIDI event to mido Message
        midi_note = note_name_to_midi_number(event.event)

        if midi_note is not None:
            # Scale velocity from 0-100 to 0-127
            velocity = int((event.value / 100) * 127)

            if velocity > 0:
                # Note on
                track.append(Message("note_on", note=midi_note, velocity=velocity, time=delta))
            else:
                # Note off
                track.append(Message("note_off", note=midi_note, velocity=0, time=delta))
        else:
            # Handle control change messages
            if event.event == "Sustain":
                cc_value = int((event.value / 100) * 127)
                track.append(Message("control_change", control=64, value=cc_value, time=delta))
            elif event.event == "ModWheel":
                cc_value = int((event.value / 100) * 127)
                track.append(Message("control_change", control=1, value=cc_value, time=delta))
            elif event.event == "AllNotesOff":
                track.append(Message("control_change", control=123, value=0, time=delta))
            elif event.event == "ResetControllers":
                track.append(Message("control_change", control=121, value=0, time=delta))

    return mid


def render_midi_to_audio(midi_events: list[MidiEvent], bpm: int, sample_rate: int = 44100) -> tuple[str, float, int]:
    """
    Render MIDI events to audio using FluidSynth.

    Args:
        midi_events: List of MIDI events to render
        bpm: Tempo in BPM
        sample_rate: Audio sample rate in Hz

    Returns:
        Tuple of (audio_file_path, duration_seconds, sample_rate)
    """
    # Get soundfont
    soundfont_path = get_soundfont_path()

    # Create MIDI file
    mid = create_midi_file(midi_events, bpm)

    # Save MIDI file to temporary location
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".mid", delete=False) as midi_file:
        midi_file_path = midi_file.name
        mid.save(midi_file)

    try:
        # Create output audio file
        output_file = tempfile.NamedTemporaryFile(mode="wb", suffix=".wav", delete=False)
        output_file_path = output_file.name
        output_file.close()

        # Initialize FluidSynth
        fs = fluidsynth.Synth(samplerate=float(sample_rate))
        fs.start()

        # Load soundfont
        sfid = fs.sfload(soundfont_path)
        fs.program_select(0, sfid, 0, 0)

        # Play MIDI file and render to audio
        fs.play_midi_file(midi_file_path)

        # Get audio samples
        samples = []
        # Calculate approximate duration from MIDI file
        duration = mid.length

        # Render audio in chunks
        num_samples = int(duration * sample_rate) + sample_rate  # Add 1 second buffer
        chunk_size = sample_rate // 2  # 0.5 second chunks

        for _ in range(0, num_samples, chunk_size):
            chunk = fs.get_samples(chunk_size)
            samples.extend(chunk)

        # Convert to 16-bit PCM
        import numpy as np

        audio_data = np.array(samples, dtype=np.float32)
        audio_data = np.clip(audio_data * 32767, -32768, 32767).astype(np.int16)

        # Write WAV file
        with wave.open(output_file_path, "wb") as wav_file:
            wav_file.setnchannels(2)  # Stereo
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())

        # Clean up FluidSynth
        fs.delete()

        return output_file_path, duration, sample_rate

    finally:
        # Clean up MIDI file
        os.unlink(midi_file_path)
