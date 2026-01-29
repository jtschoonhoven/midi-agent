"""FastAPI application entry point."""

import logging
import os
import traceback
from collections.abc import Awaitable, Callable
from pathlib import Path

import weave
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from api import auth
from api.database import init_db
from api.instruments import instrument_routes, instrument_utils
from api.loops import loop_routes
from api.songs import song_routes
from api.tracks import track_routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(name)s - %(message)s",
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


# Authentication middleware - validates API keys for all requests
@app.middleware("http")
async def auth_middleware_wrapper(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """Wrap the auth middleware."""
    return await auth.auth_middleware(request, call_next)


# Request/Response logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """Log all incoming requests and responses."""
    log.info(f"Request: {request.method} {request.url.path}")
    # Log headers but mask the Authorization header for security
    headers = dict(request.headers)
    if "authorization" in headers:
        headers["authorization"] = "***MASKED***"
    log.debug(f"Request headers: {headers}")

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
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions with detailed logging."""
    log.error(f"HTTP {exc.status_code}: {request.method} {request.url.path}")
    log.error(f"Error detail: {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors with detailed logging."""
    log.error(f"Validation error: {request.method} {request.url.path}")
    log.error(f"Errors: {exc.errors()}")
    log.error(f"Body: {exc.body}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": exc.body},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
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
def startup_event() -> None:
    load_dotenv()
    weave.init(os.environ["PROJECT_ID"])

    init_db()
    instrument_utils.init_db()
    # Create audio output directory if it doesn't exist
    audio_dir = Path(__file__).parent.parent / "audio_output"
    audio_dir.mkdir(exist_ok=True)


# Mount static files for audio output
audio_output_dir = Path(__file__).parent.parent / "audio_output"
if audio_output_dir.exists():
    app.mount("/audio", StaticFiles(directory=str(audio_output_dir)), name="audio")

# Register routers
app.include_router(song_routes.router)
app.include_router(instrument_routes.router)
app.include_router(loop_routes.router)
app.include_router(track_routes.router)
app.mount("/public", StaticFiles(directory="api/public", html=False), name="public")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


# Serve React frontend (must be last - catch-all route)
frontend_dir = Path(__file__).parent.parent / "app" / "dist"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8246)
