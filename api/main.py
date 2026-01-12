"""FastAPI application entry point."""

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    init_db()

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
