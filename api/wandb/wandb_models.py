"""
Weave (Weights & Biases) models for LLM observability.
Usually *_models.py files contain database ORM models, but in this case they are Weave models and associated schemas.
Docs: https://docs.wandb.ai/weave/guides/core-types/models
"""

import os
from uuid import UUID

import pydantic
import weave
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from api.audio.audio_types import Chord, MidiEvent, MidiEventType
from api.chats.chat_constants import MODEL_PROVIDER_MAP
from api.chats.chat_models import ChatMessage
from api.database import SessionLocal
from api.loops.loop_models import MidiLoop
from api.songs.song_models import MidiSong
from api.tracks.track_models import MidiTrack

PLANNING_PROMPT = """You are a music theory expert and composition planner.

Your job is to analyze a user's musical request and create a high-level plan that includes:
- The appropriate key for the piece
- A suitable tempo (BPM)
- The time signature
- The number of measures (1-32)
- A chord progression that fits the style
- A brief description of the style/feel

Be thoughtful about your choices. Consider the mood, genre, and any specific requests the user made.
Explain your reasoning so your choices can be evaluated.

Examples of good reasoning:
- "You requested 'bouncy piano' which suggests an upbeat feel. I chose 120 BPM in G major with a I-V-vi-IV progression for its bright, accessible sound."
- "For a melancholic ballad, I selected D minor at 72 BPM with a i-VI-III-VII progression to create emotional depth."

IMPORTANT: If set, do not change the current key, time signature, BPM, or measures unless it is explicitly requested by the user.
"""

GENERATION_PROMPT = """You are a MIDI composer. Given a musical plan, generate the actual MIDI events.
The plan specifies: key, BPM, time signature, measures, style, and chord progression.

Your job is to translate this into concrete MIDI events using the provided schema.
Follow the chord progression and style guidance exactly.
Create musical phrases that fit the specified feel.
Generate exactly the specified number of measures of music.

Each SparseMidiEvent has:
- measure: which measure (starting from 1, unbounded)
- beat: which beat in the measure (starting from 1, up to the time signature's beats per measure)
- beat_div4: one quarter of a beat (1-4 inclusive)
- beat_div16: one 16th of a beat (1-4 inclusive)
- event: the note name (e.g. "C4", "G#3") or control ("Sustain", "ModWheel")
- value: velocity/intensity 0-100 (note-off events have a velocity of 0)

Carefully consider the timing of notes (measure/beat) as well as their duration (delta from note-on to note-off).
You are encouraged to use the documented CC events (Sustain, ModWheel) when appropriate.
Generate a musically coherent sequence that realizes the plan."""

class GenerateMidiEvent(pydantic.BaseModel):
    """A MIDI event with optional timing fields (for LLM generation)."""

    chord: Chord | None = pydantic.Field(description="Underlying chord in the progression (does not necessarily match the current note)")
    measure: int | None = pydantic.Field(None, gt=0, description="The measure, starting from 1")
    beat: int | None = pydantic.Field(None, gt=0, lt=9, description="The beat within the measure, starting from 1")
    beat_div4: int | None = pydantic.Field(None, gt=0, lt=9, description="Divides the beat into quarters")
    beat_div16: int | None = pydantic.Field(None, gt=0, lt=9, description="Divides the beat into 16ths")
    event: MidiEventType = pydantic.Field(description="MIDI note or CC event")
    value: int = pydantic.Field(ge=0, le=100, description="Velocity or CC value, scaled 0-100")


class GenerateMidiResponse(pydantic.BaseModel):
    """Response from generation model with sparse MIDI events."""

    midi_events: list[GenerateMidiEvent] = pydantic.Field(description="List of sparse MIDI events")

    def to_midi_events(self) -> list[MidiEvent]:
        """Convert sparse MIDI events to fully resolved events with explicit timing."""
        result: list[MidiEvent] = []

        chord: Chord | None = None
        measure = 1
        beat = 1
        beat_div4 = 1
        beat_div16 = 1

        for item in self.midi_events:
            if item.chord and item.chord != chord:
                chord = item.chord
            if item.measure and item.measure != measure:
                measure = item.measure
                beat = 1
                beat_div4 = 1
                beat_div16 = 1
            if item.beat and item.beat != beat:
                beat = item.beat
                beat_div4 = 1
                beat_div16 = 1
            if item.beat_div4 and item.beat_div4 != beat_div4:
                beat_div4 = item.beat_div4
                beat_div16 = 1
            if item.beat_div16 and item.beat_div16 != beat_div16:
                beat_div16 = item.beat_div16

            result.append(
                MidiEvent(
                    chord=chord,
                    measure=measure,
                    beat=beat,
                    beat_div4=beat_div4,
                    beat_div16=beat_div16,
                    event=item.event,
                    value=item.value,
                )
            )

        # # Add cleanup events after the last measure
        # sustain_off = MidiEvent(
        #     measure=measure + 1, beat=1, beat_div4=1, beat_div16=1, event="Sustain", value=0
        # all_notes_off = MidiEvent(
        #     measure=measure + 1, beat=1, beat_div4=1, beat_div16=1, event="AllNotesOff", value=100
        # reset_controllers = MidiEvent(
        #     measure=measure + 1, beat=1, beat_div4=1, beat_div16=1, event="ResetControllers", value=100
        # )
        # result.append(sustain_off)
        # result.append(all_notes_off)
        # result.append(reset_controllers)

        return result


def load_chat_history(user_id: UUID, loop_id: UUID) -> list[dict[str, str]]:
    """Load chat history from SQLite database.

    Args:
        user_id: User ID
        loop_id: Loop ID

    Returns:
        List of message dicts with 'role' and 'content' keys
    """
    db: Session = SessionLocal()
    try:
        # Verify loop exists and belongs to user
        # Query: MidiLoop -> MidiTrack -> MidiSong
        loop = (
            db.query(MidiLoop)
            .join(MidiTrack, MidiLoop.track_id == MidiTrack.id)
            .join(MidiSong, MidiTrack.song_id == MidiSong.id)
            .filter(
                MidiLoop.id == str(loop_id),
                MidiSong.user_id == str(user_id)
            )
            .first()
        )

        if not loop:
            return []

        # Get all chat messages for this loop
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.loop_id == str(loop_id))
            .order_by(ChatMessage.created_at.asc())
            .all()
        )

        # Convert to simple message format
        return [{"role": msg.role, "content": msg.msg} for msg in messages]
    finally:
        db.close()


class GenerateMidi(weave.Model):
    """Weave model for generating MIDI events from user prompts.

    Attributes:
        model_name: Name of the LLM model to use (e.g., "claude-sonnet-4-5", "gpt-4o")
        system_prompt: System prompt to guide the model's behavior
    """

    model_name: str
    system_prompt: str = GENERATION_PROMPT

    @weave.op()
    async def invoke(self, user_id: UUID, loop_id: UUID, user_prompt: str) -> list[MidiEvent]:
        """Generate MIDI events from a user prompt.

        Args:
            user_id: User ID for loading chat history
            loop_id: Loop ID for loading chat history
            user_prompt: User's generation request

        Returns:
            List of fully resolved MIDI events

        Raises:
            ValueError: If required API keys are not set
        """
        # Get provider and model name
        model_provider, _ = MODEL_PROVIDER_MAP[self.model_name]

        # Check for required API keys
        if model_provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY environment variable is required for Anthropic models")
        if model_provider == "openai" and not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI models")

        # Initialize model with structured output
        model = init_chat_model(
            self.model_name,
            model_provider=model_provider
        ).with_structured_output(GenerateMidiResponse)

        # Load chat history from database
        history = load_chat_history(user_id, loop_id)

        # Build messages: system prompt, history, and user prompt
        messages = [SystemMessage(content=self.system_prompt)]

        # Add chat history
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                # Import AIMessage only when needed to avoid circular imports
                from langchain_core.messages import AIMessage
                messages.append(AIMessage(content=msg["content"]))

        # Add current user prompt
        messages.append(HumanMessage(content=user_prompt))

        # Invoke model with structured output
        response: GenerateMidiResponse = await model.ainvoke(messages)

        return response.to_midi_events()



if __name__ == "__main__":
    """
    Invoke the GenerateMidi model directly from the CLI.
    
    Example usage:
    ```
        uv run python api/wandb/wandb_models.py \
            --user-id=00000000-0000-0000-0000-000000000000 \
            --loop-id=00000000-0000-0000-0000-000000000000 \
            --prompt="Generate 4 bars of pop music in C major"
    ```
    """
    import argparse
    import asyncio
    import json
    import sys
    
    from dotenv import load_dotenv

    load_dotenv()
    weave.init(os.environ["PROJECT_ID"])

    parser = argparse.ArgumentParser(
        description="Generate MIDI events using LLM with chat history"
    )
    parser.add_argument(
        "--user-id",
        type=str,
        required=True,
        help="User ID (UUID format)",
    )
    parser.add_argument(
        "--loop-id",
        type=str,
        required=True,
        help="Loop ID (UUID format)",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        required=True,
        help="User prompt for MIDI generation",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="claude-sonnet-4-5",
        help="Model name (default: claude-sonnet-4-5)",
    )

    args = parser.parse_args()

    # Validate UUIDs
    try:
        user_id = UUID(args.user_id)
        loop_id = UUID(args.loop_id)
    except ValueError as e:
        print(f"Error: Invalid UUID format - {e}", file=sys.stderr)
        sys.exit(1)

    # Create model instance
    model = GenerateMidi(model_name=args.model)

    # Run async invoke
    async def main():
        try:
            midi_events = await model.invoke(user_id, loop_id, args.prompt)
            # Print results as JSON
            print(json.dumps([event.model_dump() for event in midi_events], indent=2))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    asyncio.run(main())
