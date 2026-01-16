# """FastAPI routes for audio rendering."""

# from pathlib import Path

# import pydantic
# from fastapi import APIRouter

# class RenderRequest(pydantic.BaseModel):
#     """Request payload for /api/midi/render endpoint."""

#     bpm: int = pydantic.Field(gt=29, lt=361, description="Tempo in BPM (30-360)")
#     midi: list[MidiEvent] = pydantic.Field(description="MIDI events to render")


# class RenderResponse(pydantic.BaseModel):
#     """Response from /api/midi/render endpoint with audio information."""

#     audio_url: str = pydantic.Field(description="URL to the rendered audio file")
#     duration_seconds: float = pydantic.Field(gt=0, description="Duration of the audio in seconds")
#     sample_rate: int = pydantic.Field(gt=0, description="Sample rate of the audio in Hz")


# router = APIRouter(prefix="/api/midi", tags=["audio"])


# class PublicFilesResponse(pydantic.BaseModel):
#     """Response containing list of files in the public folder."""

#     public: list[str] = pydantic.Field(description="List of file paths relative to the public folder")


# @router.get("/samples", response_model=PublicFilesResponse)
# async def list_samples() -> PublicFilesResponse:
#     """
#     List all instrument samples in the public/instruments folder.
#     """
#     # Get the instruments folder path
#     project_root = Path(__file__).parent.parent
#     instruments_dir = project_root / "public" / "instruments"

#     # Collect all files recursively from instruments folder
#     files: list[str] = []
#     public_dir = project_root / "public"
#     for file_path in instruments_dir.rglob("*"):
#         if file_path.is_file() and not file_path.name.startswith("."):
#             # Get path relative to public folder (includes "instruments/" prefix)
#             relative_path = file_path.relative_to(public_dir)
#             # Convert to forward slashes for consistency across platforms
#             files.append(str(relative_path).replace("\\", "/"))

#     # Sort for consistent ordering
#     files.sort()

#     return PublicFilesResponse(public=files)


# @router.post("/render", response_model=RenderResponse)
# async def render_midi(request: RenderRequest) -> RenderResponse:
#     """
#     Render MIDI events to audio.

#     Args:
#         request: Render request with BPM and MIDI events

#     Returns:
#         RenderResponse with audio URL, duration, and sample rate

#     Raises:
#         HTTPException: If rendering fails
#     """
#     try:
#         # Render MIDI to audio
#         sample_rate = 44100
#         audio_file_path, duration, actual_sample_rate = render_midi_to_audio(request.midi, request.bpm, sample_rate)

#         # Store audio file in a persistent location
#         # Create output directory if it doesn't exist
#         project_root = Path(__file__).parent.parent.parent
#         output_dir = project_root / "audio_output"
#         output_dir.mkdir(exist_ok=True)

#         # Generate unique filename
#         output_filename = f"{uuid4()}.wav"
#         output_path = output_dir / output_filename

#         # Move rendered file to output directory
#         shutil.move(audio_file_path, str(output_path))

#         # Generate URL (for local development, use file path)
#         # In production, this would be a proper URL to a CDN or file server
#         audio_url = f"/audio/{output_filename}"

#         return RenderResponse(audio_url=audio_url, duration_seconds=duration, sample_rate=actual_sample_rate)
#     except FileNotFoundError as e:
#         raise HTTPException(status_code=500, detail="Soundfont not found") from e
#     except Exception as e:
#         raise HTTPException(status_code=500, detail="MIDI rendering failed") from e
