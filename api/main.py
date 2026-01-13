"""FastAPI application entry point."""

import shutil
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.database import init_db
from api.midi.midi_routes import router as midi_router

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="MIDI Agent API",
    description="AI-powered MIDI generation from natural language prompts",
    version="0.1.0",
)


# Initialize database on startup
@app.on_event("startup")
def startup_event():
    # Check if FluidSynth is installed
    fluidsynth_path = shutil.which("fluidsynth")
    if not fluidsynth_path:
        error_msg = (
            "FluidSynth is not installed or not in PATH. "
            "Please install FluidSynth:\n"
            "  - macOS: brew install fluid-synth\n"
            "  - Ubuntu/Debian: apt-get install fluidsynth\n"
            "  - Windows: Download from https://github.com/FluidSynth/fluidsynth/releases"
        )
        raise RuntimeError(error_msg)

    init_db()
    # Create audio output directory if it doesn't exist
    audio_dir = Path(__file__).parent.parent / "audio_output"
    audio_dir.mkdir(exist_ok=True)


# Mount static files for audio output
audio_output_dir = Path(__file__).parent.parent / "audio_output"
if audio_output_dir.exists():
    app.mount("/audio", StaticFiles(directory=str(audio_output_dir)), name="audio")

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite and common React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(midi_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
