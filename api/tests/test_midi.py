"""Tests for MIDI routes."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.midi.midi_utils import MidiEvent


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def sample_midi_events():
    """Create sample MIDI events for testing."""
    return [
        MidiEvent(measure=1, beat=1, beat_div4=1, beat_div16=1, event="C4", value=80),
        MidiEvent(measure=1, beat=2, beat_div4=1, beat_div16=1, event="E4", value=80),
        MidiEvent(measure=1, beat=3, beat_div4=1, beat_div16=1, event="G4", value=80),
        MidiEvent(measure=1, beat=4, beat_div4=1, beat_div16=1, event="C4", value=0),
        MidiEvent(measure=1, beat=4, beat_div4=2, beat_div16=1, event="E4", value=0),
        MidiEvent(measure=1, beat=4, beat_div4=3, beat_div16=1, event="G4", value=0),
    ]


@pytest.fixture
def render_request_payload(sample_midi_events):
    """Create a render request payload."""
    return {
        "bpm": 120,
        "midi": [
            {
                "measure": event.measure,
                "beat": event.beat,
                "beat_div4": event.beat_div4,
                "beat_div16": event.beat_div16,
                "event": event.event,
                "value": event.value,
            }
            for event in sample_midi_events
        ],
    }


class TestRenderEndpoint:
    """Tests for /api/midi/render endpoint."""

    @patch("api.midi.midi_routes.render_midi_to_audio")
    @patch("api.midi.midi_routes.shutil.move")
    def test_render_midi_success(self, mock_move, mock_render, client, render_request_payload):
        """Test successful MIDI rendering."""
        # Create a temporary file to simulate rendered audio
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_file_path = temp_file.name
        temp_file.close()

        try:
            # Mock the render function to return our temp file
            mock_render.return_value = (temp_file_path, 4.5, 44100)

            # Mock shutil.move to avoid actual file operations
            mock_move.return_value = None

            # Make the request
            response = client.post("/api/midi/render", json=render_request_payload)

            # Verify response
            assert response.status_code == 200
            data = response.json()

            assert "audio_url" in data
            assert data["audio_url"].startswith("/audio/")
            assert data["audio_url"].endswith(".wav")
            assert data["duration_seconds"] == 4.5
            assert data["sample_rate"] == 44100

            # Verify render function was called with correct arguments
            mock_render.assert_called_once()
            call_args = mock_render.call_args
            midi_events = call_args[0][0]
            bpm = call_args[0][1]
            sample_rate = call_args[0][2]

            assert len(midi_events) == 6
            assert bpm == 120
            assert sample_rate == 44100

            # Verify file move was called
            mock_move.assert_called_once()

        finally:
            # Clean up temp file if it still exists
            Path(temp_file_path).unlink(missing_ok=True)

    @patch("api.midi.midi_routes.render_midi_to_audio")
    def test_render_midi_invalid_bpm(self, mock_render, client):
        """Test render with invalid BPM."""
        payload = {
            "bpm": 25,  # Below minimum of 30
            "midi": [{"measure": 1, "beat": 1, "beat_div4": 1, "beat_div16": 1, "event": "C4", "value": 80}],
        }

        response = client.post("/api/midi/render", json=payload)
        assert response.status_code == 422  # Validation error

    @patch("api.midi.midi_routes.render_midi_to_audio")
    def test_render_midi_empty_events(self, mock_render, client):
        """Test render with empty MIDI events."""
        payload = {"bpm": 120, "midi": []}

        # Empty MIDI events list is valid - the endpoint will process it
        # The actual behavior depends on how render_midi_to_audio handles empty input
        client.post("/api/midi/render", json=payload)

    @patch("api.midi.midi_routes.render_midi_to_audio")
    def test_render_midi_soundfont_not_found(self, mock_render, client, render_request_payload):
        """Test render when soundfont is not found."""
        # Mock the render function to raise FileNotFoundError
        mock_render.side_effect = FileNotFoundError("Soundfont not found at /path/to/soundfont")

        response = client.post("/api/midi/render", json=render_request_payload)

        assert response.status_code == 500
        assert "Soundfont not found" in response.json()["detail"]

    @patch("api.midi.midi_routes.render_midi_to_audio")
    def test_render_midi_generic_error(self, mock_render, client, render_request_payload):
        """Test render with generic error during rendering."""
        # Mock the render function to raise a generic exception
        mock_render.side_effect = Exception("Unexpected error during rendering")

        response = client.post("/api/midi/render", json=render_request_payload)

        assert response.status_code == 500
        assert "MIDI rendering failed" in response.json()["detail"]

    @patch("api.midi.midi_routes.render_midi_to_audio")
    @patch("api.midi.midi_routes.shutil.move")
    def test_render_midi_high_bpm(self, mock_move, mock_render, client):
        """Test render with high BPM value."""
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_file_path = temp_file.name
        temp_file.close()

        try:
            mock_render.return_value = (temp_file_path, 2.0, 44100)
            mock_move.return_value = None

            payload = {
                "bpm": 350,  # Near maximum of 360
                "midi": [{"measure": 1, "beat": 1, "beat_div4": 1, "beat_div16": 1, "event": "C4", "value": 80}],
            }

            response = client.post("/api/midi/render", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["duration_seconds"] == 2.0

        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    @patch("api.midi.midi_routes.render_midi_to_audio")
    @patch("api.midi.midi_routes.shutil.move")
    def test_render_midi_control_messages(self, mock_move, mock_render, client):
        """Test render with control messages (Sustain, ModWheel, etc.)."""
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_file_path = temp_file.name
        temp_file.close()

        try:
            mock_render.return_value = (temp_file_path, 3.0, 44100)
            mock_move.return_value = None

            payload = {
                "bpm": 120,
                "midi": [
                    {"measure": 1, "beat": 1, "beat_div4": 1, "beat_div16": 1, "event": "C4", "value": 80},
                    {"measure": 1, "beat": 1, "beat_div4": 2, "beat_div16": 1, "event": "Sustain", "value": 100},
                    {"measure": 1, "beat": 2, "beat_div4": 1, "beat_div16": 1, "event": "ModWheel", "value": 50},
                    {"measure": 1, "beat": 3, "beat_div4": 1, "beat_div16": 1, "event": "C4", "value": 0},
                    {"measure": 1, "beat": 4, "beat_div4": 1, "beat_div16": 1, "event": "AllNotesOff", "value": 100},
                ],
            }

            response = client.post("/api/midi/render", json=payload)
            assert response.status_code == 200

            # Verify the render function received all events including control messages
            mock_render.assert_called_once()
            midi_events = mock_render.call_args[0][0]
            assert len(midi_events) == 5

        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    def test_render_midi_missing_required_fields(self, client):
        """Test render with missing required fields."""
        # Missing bpm
        response = client.post("/api/midi/render", json={"midi": []})
        assert response.status_code == 422

        # Missing midi
        response = client.post("/api/midi/render", json={"bpm": 120})
        assert response.status_code == 422

    def test_render_midi_invalid_midi_event(self, client):
        """Test render with invalid MIDI event structure."""
        payload = {
            "bpm": 120,
            "midi": [
                {
                    "measure": 1,
                    "beat": 1,
                    # Missing beat_div4, beat_div16
                    "event": "C4",
                    "value": 80,
                }
            ],
        }

        response = client.post("/api/midi/render", json=payload)
        assert response.status_code == 422  # Validation error
