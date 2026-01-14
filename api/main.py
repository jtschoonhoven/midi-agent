"""FastAPI application entry point."""

import logging
import os
import shutil
import traceback
from pathlib import Path

import weave
from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.audio import audio_routes
from api.database import init_db
from api.loops import loop_routes
from api.songs import song_routes
from api.tracks import track_routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Set specific loggers to DEBUG for more detailed output
logging.getLogger("api").setLevel(logging.DEBUG)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)

log = logging.getLogger(__name__)

app = FastAPI(
    title="MIDI Agent API",
    description="AI-powered MIDI generation from natural language prompts",
    version="0.1.0",
)

# Configure CORS - allow all origins for demo purposes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Must be False when allow_origins is "*"
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and responses."""
    log.info(f"Request: {request.method} {request.url.path}")
    log.debug(f"Request headers: {dict(request.headers)}")

    try:
        response = await call_next(request)
        log.info(f"Response: {request.method} {request.url.path} - Status {response.status_code}")
        return response
    except Exception as e:
        log.error(f"Request failed: {request.method} {request.url.path}")
        log.error(f"Error: {str(e)}")
        log.error(f"Traceback:\n{traceback.format_exc()}")
        raise


# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with detailed logging."""
    log.error(f"HTTP {exc.status_code}: {request.method} {request.url.path}")
    log.error(f"Error detail: {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors with detailed logging."""
    log.error(f"Validation error: {request.method} {request.url.path}")
    log.error(f"Errors: {exc.errors()}")
    log.error(f"Body: {exc.body}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": exc.body},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions with full traceback logging."""
    log.error(f"Unhandled exception: {request.method} {request.url.path}")
    log.error(f"Exception type: {type(exc).__name__}")
    log.error(f"Exception message: {str(exc)}")
    log.error(f"Full traceback:\n{traceback.format_exc()}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error": str(exc),
            "type": type(exc).__name__,
        },
    )


# Initialize database on startup
@app.on_event("startup")
def startup_event():
    load_dotenv()
    weave.init(os.environ["PROJECT_ID"])

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

# Register routers
app.include_router(song_routes.router)
app.include_router(audio_routes.router)
app.include_router(loop_routes.router)
app.include_router(track_routes.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
