"""
Weave (Weights & Biases) models for LLM observability.
Usually *_models.py files contain database ORM models, but in this case they are Weave models and associated schemas.
Docs: https://docs.wandb.ai/weave/guides/core-types/models
"""

import logging
import os
from typing import Optional
from uuid import UUID, uuid4

import pydantic
import weave
from fastapi import HTTPException
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sqlalchemy.orm import Session, joinedload

from api.audio.audio_types import Chord, MidiEvent, MidiEventType
from api.chats.chat_constants import MODEL_PROVIDER_MAP
from api.chats.chat_models import ChatMessage
from api.database import SessionLocal
from api.loops.loop_models import MidiLoop
from api.songs.song_models import MidiSong
from api.tracks.track_models import MidiTrack

log = logging.getLogger(__name__)

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
Generate a musically coherent sequence that realizes the plan.

IMPORTANT: Also provide a brief one-sentence description of what you generated. This should describe the musical
character, style, or key features of the loop you created (e.g., "A bright 4-bar piano melody in C major with
staccato eighth notes and a playful rhythm" or "Warm sustained pad chords creating an ambient atmosphere")."""

_CLIENT: Optional["_GenerateMidi"] = None


def get_agent() -> "_GenerateMidi":
    """Get a client for the GenerateMidi model."""
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = _GenerateMidi(model_name="gpt-4o", system_prompt=GENERATION_PROMPT)
    return _CLIENT


class _GenerateMidi(weave.Model):
    """Weave model for generating MIDI events from user prompts.

    Attributes:
        model_name: Name of the LLM model to use (e.g., "claude-sonnet-4-5", "gpt-4o")
        system_prompt: System prompt to guide the model's behavior
    """

    model_name: str
    system_prompt: str

    @weave.op()
    async def invoke(self, *, user_id: UUID, track_id: UUID, loop_id: UUID, user_prompt: str) -> MidiLoop:
        """Generate MIDI events from a user prompt and save to database.

        Returns:
            Tuple of (MIDI events, new loop ID)

        Raises:
            ValueError: If required API keys are not set or track doesn't exist
        """
        # Get provider and model name
        model_provider, _ = MODEL_PROVIDER_MAP[self.model_name]

        # Check for required API keys
        if model_provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY environment variable is required for Anthropic models")
        if model_provider == "openai" and not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI models")

        # Initialize model with structured output
        model = init_chat_model(self.model_name, model_provider=model_provider).with_structured_output(
            GenerateMidiResponse
        )

        # Get the chat history and add the current prompt
        messages = self.load_chat_history(user_id=user_id, track_id=track_id, loop_id=loop_id)
        messages.append(HumanMessage(content=user_prompt))

        # Invoke model with structured output
        response: GenerateMidiResponse = await model.ainvoke(messages)
        midi_events = response.to_midi_events()

        # Save to database: create new loop and chat messages
        loop = self.update_loop(
            user_id=user_id,
            track_id=track_id,
            loop_id=loop_id,
            user_prompt=user_prompt,
            agent_description=response.description,
            midi_events=midi_events,
        )
        return loop

    def load_chat_history(
        self, *, user_id: UUID, track_id: UUID, loop_id: UUID
    ) -> list[SystemMessage | HumanMessage | AIMessage]:
        """Load chat history from a specific loop or the most recent loop in a track.

        Args:
            user_id: User ID
            track_id: Track ID
            loop_id: Loop ID to load chat history from, or None for a new loop

        Returns:
            List of LangChain message objects (SystemMessage, HumanMessage, AIMessage)
        """
        db: Session = SessionLocal()

        try:
            loop = (
                db.query(MidiLoop)
                .join(MidiTrack, MidiLoop.track_id == MidiTrack.id)
                .join(MidiSong, MidiTrack.song_id == MidiSong.id)
                .options(joinedload(MidiLoop.chat_messages))
                .filter(MidiLoop.id == str(loop_id), MidiTrack.id == str(track_id), MidiSong.user_id == str(user_id))
                .first()
            )
            if not loop:
                raise HTTPException(status_code=404)

            # Initialize history with the system prompt
            history: list[SystemMessage | HumanMessage | AIMessage] = [SystemMessage(content=self.system_prompt)]

            # Convert database messages to LangChain messages
            for chat in sorted(loop.chat_messages, key=lambda x: x.created_at):
                if chat.role == "system":
                    history.append(SystemMessage(content=chat.msg))
                if chat.role == "user":
                    history.append(HumanMessage(content=chat.msg))
                elif chat.role == "assistant":
                    history.append(AIMessage(content=chat.msg))
                else:
                    log.error(f"Unknown message role: {chat.role}")
                    raise HTTPException(status_code=500)

            return history

        finally:
            db.close()

    def update_loop(
        self,
        *,
        user_id: UUID,
        track_id: UUID,
        loop_id: UUID,
        user_prompt: str,
        agent_description: str,
        midi_events: list[MidiEvent],
    ) -> MidiLoop:
        """Save generated MIDI to database as a new loop with chat messages."""
        db: Session = SessionLocal()

        try:
            # Fetch the loop and verify track exists and belongs to user (assumed to exist)
            loop = (
                db.query(MidiLoop)
                .join(MidiTrack, MidiLoop.track_id == MidiTrack.id)
                .join(MidiSong, MidiTrack.song_id == MidiSong.id)
                .filter(MidiLoop.id == str(loop_id), MidiTrack.id == str(track_id), MidiSong.user_id == str(user_id))
                .first()
            )

            if not loop:
                raise HTTPException(status_code=404)

            # Update the loop with the new MIDI events
            loop.measures = max(event.measure for event in midi_events) + 1
            loop.midi_events = [event.model_dump() for event in midi_events]
            db.add(loop)

            # Add the user prompt to the chat history
            message = ChatMessage(
                id=str(uuid4()),
                role="user",
                msg=user_prompt,
                midi_events=None,
                loop_id=loop.id,
            )
            db.add(message)

            # Add the assistant message to the chat history
            assistant_message = ChatMessage(
                id=str(uuid4()),
                role="assistant",
                msg=agent_description,  # Use LLM-generated description
                midi_events=[event.model_dump() for event in midi_events],
                loop_id=loop.id,
            )
            db.add(assistant_message)

            # Commit changes and return
            db.commit()
            return loop

        except Exception as e:
            db.rollback()
            raise e

        finally:
            db.close()


class GenerateMidiEvent(pydantic.BaseModel):
    """A MIDI event with optional timing fields (for LLM generation)."""

    chord: Chord | None = pydantic.Field(
        default=None, description="Underlying chord in the progression (does not necessarily match the current note)"
    )
    measure: int | None = pydantic.Field(None, gt=0, description="The measure, starting from 1")
    beat: int | None = pydantic.Field(None, gt=0, lt=9, description="The beat within the measure, starting from 1")
    beat_div4: int | None = pydantic.Field(None, gt=0, lt=9, description="Divides the beat into quarters")
    beat_div16: int | None = pydantic.Field(None, gt=0, lt=9, description="Divides the beat into 16ths")
    event: MidiEventType = pydantic.Field(description="MIDI note or CC event")
    value: int = pydantic.Field(ge=0, le=100, description="Velocity or CC value, scaled 0-100")


class GenerateMidiResponse(pydantic.BaseModel):
    """Response from generation model with sparse MIDI events and description."""

    description: str = pydantic.Field(
        description="One-sentence description of the generated loop, describing its musical character, style, or key features"
    )
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


if __name__ == "__main__":
    """
    Invoke the GenerateMidi model directly from the CLI.

    Example usage:
    ```
        # Start fresh or continue from most recent loop
        uv run python api/midi/midi_agents.py \
            --user-id=00000000-0000-0000-0000-000000000000 \
            --track-id=00000000-0000-0000-0000-000000000000 \
            --prompt="Generate 4 bars of pop music in C major"

        # Continue from a specific loop
        uv run python api/midi/midi_agents.py \
            --user-id=00000000-0000-0000-0000-000000000000 \
            --track-id=00000000-0000-0000-0000-000000000000 \
            --loop-id=11111111-1111-1111-1111-111111111111 \
            --prompt="Make it more upbeat"
    ```
    """
    import argparse
    import asyncio
    import json
    import sys

    from dotenv import load_dotenv

    load_dotenv()
    weave.init(os.environ["PROJECT_ID"])

    parser = argparse.ArgumentParser(description="Generate MIDI events using LLM with chat history")
    parser.add_argument(
        "--user-id",
        type=str,
        required=True,
        help="User ID (UUID format)",
    )
    parser.add_argument(
        "--track-id",
        type=str,
        required=True,
        help="Track ID (UUID format)",
    )
    parser.add_argument(
        "--loop-id",
        type=str,
        required=False,
        help="Optional loop ID to continue from. If not provided, uses most recent loop in track.",
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
        track_id = UUID(args.track_id)
        loop_id = UUID(args.loop_id) if args.loop_id else None
    except ValueError as e:
        print(f"Error: Invalid UUID format - {e}", file=sys.stderr)
        sys.exit(1)

    # Create model instance
    model = _GenerateMidi(model_name=args.model, system_prompt=GENERATION_PROMPT)

    # Run async invoke
    async def main():
        try:
            midi_events, new_loop_id = await model.invoke(user_id, track_id, args.prompt, loop_id)
            # Print results as JSON
            result = {"loop_id": new_loop_id, "midi_events": [event.model_dump() for event in midi_events]}
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    asyncio.run(main())
