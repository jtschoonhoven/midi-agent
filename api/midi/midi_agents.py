"""
Weave (Weights & Biases) models for LLM observability.
Docs: https://docs.wandb.ai/weave/guides/core-types/models
"""

import logging
import os
from types import TracebackType
from typing import TYPE_CHECKING, Optional, TypedDict, cast
from uuid import UUID, uuid4

import httpx
import pydantic
import weave
from anthropic import AsyncAnthropic
from anthropic.types.beta import BetaMessageParam
from fastapi import HTTPException
from openai import AsyncOpenAI
from openai.types.responses import ResponseInputItemParam
from weave.flow.scorer import ApplyScorerResult
from weave.trace.call import Call
from weave.trace.vals import WeaveList

from api.audio.audio_types import Chord
from api.chats import chat_models
from api.chats.chat_constants import MODEL_PROVIDER_MAP
from api.chats.chat_types import ModelName
from api.database import SessionLocal
from api.instruments.instrument_types import InstrumentType
from api.loops import loop_utils, loop_models
from api.midi import midi_evals, midi_models, midi_utils
from api.midi.midi_types import MidiEventType
from api.songs.song_types import Key, TimeSignature


DEFAULT_MODEL_NAME: ModelName = "claude-haiku-4-5"
MAX_ATTEMPTS = 3

log = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a helpful music composer. Given a user prompt, generate a musical loop in that style.

Each midi event has:
- chord: underlying chord in the progression (does not necessarily match the current note): I, V7, IIdim or null if N/A.
- measure: current measure starting from 1 (unbounded)
- beat: current beat in the measure (starting from 1, up to this time signature's beats per measure)
- beat_div4: one quarter of a beat (1-4 inclusive)
- beat_div16: one quarter of a div4 (1/16th of a beat, 1-4 inclusive)
- event: the note, CC, or GM drum name ("C4", "G#3", "Open Hi-Hat", "Sustain", "Modulation Wheel", etc.)
- value: velocity/intensity 0-100 (note-off events have a velocity of 0)

Examples of valid events (assuming 4/4):
 - {"chord": "I", "measure": 5, "beat": 4, "beat_div4": 2, "beat_div16": 1, "event": "C4", "value": 100}  # Middle C on the "&" of 2 in the 5th measure
 - {"measure": 6, "event": "C4", "value": 0}  # Note-off for middle C on the first beat of the 6th measure
 - {"measure": 6, "beat_div16": 4, "event": "Open Hi-Hat", "value": 20}  # Soft open hi-hat on the "e" of the 6th measure

Also provide a brief one-sentence description of what you generated (e.g., "A playful melody with stacatto eighth notes" or
"Warm sustained chords creating an ambient atmosphere").

Carefully consider the timing of notes (measure/beat) as well as their duration (delta from note-on to note-off).
IMPORTANT: THE NUMBER OF NOTE-ON EVENTS *MUST* EQUAL THE NUMBER OF NOTE-OFF EVENTS (value=0) FOR EACH NOTE!!"""


class ChatMessage(TypedDict):
    role: str
    content: str


ChatHistory = list[ChatMessage]
GenerateMidiCallResponse = tuple["GenerateMidiResponse", Call]

_MODEL_CACHE: dict[ModelName, "_GenerateMidi"] = {}


def get_model(model_name: ModelName) -> "_GenerateMidi":
    """Get a client for the GenerateMidi model."""
    global _MODEL_CACHE
    if not _MODEL_CACHE.get(model_name):
        _MODEL_CACHE[model_name] = _GenerateMidi(model_name=model_name, system_prompt=SYSTEM_PROMPT)
    return _MODEL_CACHE[model_name]


async def generate_midi_for_loop(
    *,
    user_id: str | UUID,
    loop_id: str | UUID,
    model_name: ModelName,
    user_prompt: str,
    expect_time_signature: TimeSignature,
    expect_bpm: int,
    expect_key: Key,
    expect_measures: int,
    expect_instrument: InstrumentType,
) -> "loop_models.MidiLoop":
    model_provider, _ = MODEL_PROVIDER_MAP[model_name]

    # Check for required API keys
    if model_provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI models")
    if model_provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        raise ValueError("ANTHROPIC_API_KEY environment variable is required for Anthropic models")

    # Get the chat history and add the current prompt
    chat_history = load_chat_history(user_id=user_id, loop_id=loop_id, system_prompt=SYSTEM_PROMPT)
    chat_history.append(ChatMessage(role="user", content=user_prompt))

    model = get_model(model_name)

    for n in range(MAX_ATTEMPTS):
        try:
            response = await model.invoke(
                chat_history=chat_history,
                expect_time_signature=expect_time_signature,
                expect_bpm=expect_bpm,
                expect_key=expect_key,
                expect_measures=expect_measures,
                expect_instrument=expect_instrument,
            )
            return update_loop(
                user_id=user_id,
                loop_id=loop_id,
                user_prompt=user_prompt,
                agent_description=response.description,
                midi_events=response.to_midi_events(),
            )
        except Exception as e:
            chat_history.append(
                ChatMessage(role="user", content=f"Previous attempt failed, please fix the error and try again: {e}")
            )
            log.exception(f"Generate midi attempt {n + 1}/{MAX_ATTEMPTS} failed: {e}")

    raise HTTPException(
        status_code=500, detail=f"Failed to generate valid MIDI after {MAX_ATTEMPTS} attempts. Please try again."
    )


@weave.op()
async def generate_midi(
    model_name: "ModelName",
    chat_history: ChatHistory | WeaveList,
    *,
    expect_time_signature: TimeSignature,
    expect_bpm: int,
    expect_key: Key,
    expect_measures: int,
    expect_instrument: InstrumentType,
) -> GenerateMidiCallResponse:
    """
    Run inference to generate MIDI events using the given model and chat history.
    Injects a constraint to restrict the number of measures generated.
    """
    if not chat_history:
        log.error("No chat history provided")
        raise HTTPException(status_code=500)

    # Hack: During evals, chat_history is replaced by an immutable WeaveList which must be unwrapped back to a mutable list
    if isinstance(chat_history, WeaveList):
        chat_history = chat_history.unwrap()

    # Inject a constraint for the number of measures
    user_content = chat_history[-1]["content"]
    patched_user_content = (
        f"{user_content}\nIMPORTANT: You *must* generate exactly {expect_measures} measures of MIDI events in "
        f"{expect_time_signature} at {expect_bpm} BPM in the key of {expect_key} for {expect_instrument}."
        "Remember that each note-on event must have a corresponding note-off event (value=0)."
    )
    chat_history[-1]["content"] = patched_user_content

    # Get provider from the map (returns tuple of (provider, model_name))
    provider, _ = MODEL_PROVIDER_MAP[model_name]

    if provider == "openai":
        log.debug(f"Generating MIDI with OpenAI model: {model_name}")
        return await _generate_midi_openai.call(model_name, chat_history)  # type: ignore [no-any-return]

    elif provider == "anthropic":
        log.debug(f"Generating MIDI with Anthropic model: {model_name}")
        return await _generate_midi_anthropic.call(model_name, chat_history)  # type: ignore [no-any-return]

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported model provider: {provider}")


class _GenerateMidi(weave.Model):
    """Weave model for generating MIDI events from user prompts.

    Attributes:
        model_name: Name of the LLM model to use (e.g., "claude-sonnet-4-5", "gpt-4o")
        system_prompt: System prompt to guide the model's behavior
    """

    model_name: ModelName
    system_prompt: str

    @weave.op()
    async def invoke(
        self,
        *,
        chat_history: str,
        expect_time_signature: TimeSignature,
        expect_bpm: int,
        expect_key: Key,
        expect_measures: int,
        expect_instrument: InstrumentType,
    ) -> "GenerateMidiResponse":
        """Generate MIDI events from a user prompt and save to database."""
        try:
            result: GenerateMidiCallResponse = await generate_midi(
                self.model_name,
                chat_history,
                expect_time_signature=expect_time_signature,
                expect_bpm=expect_bpm,
                expect_key=expect_key,
                expect_measures=expect_measures,
                expect_instrument=expect_instrument,
            )

            if not result or not result[0]:
                raise ValueError("Empty response from model.")

            midi_events, call = result

            score_result: ApplyScorerResult = await call.apply_scorer(
                midi_evals.evaluate_midi_events,
                additional_scorer_kwargs={
                    "expect_measures": expect_measures,
                    "expect_time_signature": expect_time_signature,
                },
            )
            score: midi_evals.EvalResult = score_result.result

            if not score.get("ok") or score.get("error"):
                raise ValueError(
                    f"The generated MIDI events failed evaluation, please fix and try again: {score.get('error', 'Unknown error')}"
                )

            # Success!
            return midi_events

        except pydantic.ValidationError as e:
            raise ValueError(
                f"The generated MIDI events failed validation, please fix and try again: {e.errors(include_url=False, include_context=False)}"
            ) from e

        except Exception as e:
            raise ValueError(f"Unexpected error: {e}") from e


def update_loop(
    *,
    user_id: str | UUID,
    loop_id: str | UUID,
    user_prompt: str,
    agent_description: str,
    midi_events: list[midi_models.MidiEvent],
) -> "loop_models.MidiLoop":
    """Save generated MIDI to database as a new loop with chat messages."""
    with SessionLocal() as db:
        loop = loop_utils.get_loop_for_user(db, user_id, loop_id)

        if not loop:
            raise HTTPException(status_code=404)

        # Update the loop with the new MIDI events
        loop.measures = max(event.measure for event in midi_events)
        loop.midi_events = [event.model_dump() for event in midi_events]
        db.add(loop)

        # Add the user prompt to the chat history
        message = chat_models.ChatMessage(
            id=str(uuid4()),
            role="user",
            msg=user_prompt,
            midi_events=None,
            loop_id=loop.id,
        )
        db.add(message)

        # Add the assistant message to the chat history
        assistant_message = chat_models.ChatMessage(
            id=str(uuid4()),
            role="assistant",
            msg=agent_description,  # Use LLM-generated description
            midi_events=[event.model_dump() for event in midi_events],
            loop_id=loop.id,
        )
        db.add(assistant_message)

        # Commit changes
        db.commit()

        # Refresh to eagerly load all relationships before closing session
        db.refresh(loop)

        return loop


class GeneratedMidiEvent(pydantic.BaseModel):
    """A MIDI event with optional timing fields (for LLM generation)."""

    chord: Chord | None = pydantic.Field(
        default=None, description="Underlying chord in the progression (does not necessarily match the current note)"
    )
    measure: int | None = pydantic.Field(None, gt=0, description="The measure, starting from 1")
    beat: int | None = pydantic.Field(None, gt=0, lt=9, description="The beat within the measure, starting from 1")
    beat_div4: int | None = pydantic.Field(None, gt=0, lt=9, description="Divides the beat into quarters")
    beat_div16: int | None = pydantic.Field(None, gt=0, lt=9, description="Divides the beat into 16ths")
    event: str | MidiEventType = pydantic.Field(
        description='MIDI note, cc, or GM drum name: "C#4", "Sustain", "Open Hi-Hat'
    )
    value: int = pydantic.Field(ge=0, le=100, description="Velocity or CC value, scaled 0-100")


class GenerateMidiResponse(pydantic.BaseModel):
    """Response from generation model with sparse MIDI events and description."""

    description: str = pydantic.Field(
        description="One-sentence description of the generated loop, describing its musical character, style, or key features"
    )
    midi_events: list[GeneratedMidiEvent] = pydantic.Field(description="List of sparse MIDI events")

    def to_midi_events(self) -> list["midi_models.MidiEvent"]:
        """Convert sparse MIDI events to fully resolved events with explicit timing."""
        result: list[midi_models.MidiEvent] = []

        chord: Chord | None = None
        measure = 1
        beat = 1
        beat_div4 = 1
        beat_div16 = 1

        for item in self.midi_events:
            event = midi_utils.str_to_midi_event(item.event)
            if event is None:
                log.warning(f"Skipping invalid MIDI event: {item.event}")
                continue

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
                midi_models.MidiEvent(
                    chord=chord,
                    measure=measure,
                    beat=beat,
                    beat_div4=beat_div4,
                    beat_div16=beat_div16,
                    event=event,
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


def load_chat_history(*, user_id: str | UUID | None, loop_id: str | UUID | None, system_prompt: str) -> ChatHistory:
    """
    Load chat history for the given loop (or just the system prompt if no loop ID is provided).
    """
    # Initialize history with the system prompt
    history: ChatHistory = [{"role": "system", "content": system_prompt}]

    # Nothing to load if no IDs were provided: the history is just the system prompt
    if not user_id or not loop_id:
        return history

    with SessionLocal() as db:
        loop = loop_utils.get_loop_for_user(db, user_id, loop_id)
        if not loop:
            raise HTTPException(status_code=404)

        # Convert database messages to OpenAI chat messages
        for chat in sorted(loop.chat_messages, key=lambda x: x.created_at):
            if chat.role == "system":
                history.append(ChatMessage(role="system", content=chat.msg))
            if chat.role == "user":
                history.append(ChatMessage(role="user", content=chat.msg))
            elif chat.role == "assistant":
                history.append(ChatMessage(role="assistant", content=chat.msg))
            else:
                log.error(f"Unknown message role: {chat.role}")
                raise HTTPException(status_code=500)

        return history


@weave.op()
async def _generate_midi_openai(model_name: "ModelName", chat_history: ChatHistory) -> "GenerateMidiResponse":
    client = AsyncOpenAI()
    messages = cast(list[ResponseInputItemParam], chat_history)
    response = await client.responses.parse(model=model_name, input=messages, text_format=GenerateMidiResponse)
    if not isinstance(response.output_parsed, GenerateMidiResponse):
        raise HTTPException(status_code=500, detail="Failed to parse MIDI response from OpenAI.")
    return response.output_parsed


@weave.op()
async def _generate_midi_anthropic(model_name: "ModelName", chat_history: ChatHistory) -> "GenerateMidiResponse":
    client = AsyncAnthropic()
    system_prompt = ""
    messages: list[BetaMessageParam] = []

    # Format messages for Anthropic
    for msg in chat_history:
        if msg["role"] == "system" and not system_prompt:
            system_prompt = msg["content"]
        elif msg["role"] == "user":
            messages.append(BetaMessageParam(role="user", content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(BetaMessageParam(role="assistant", content=msg["content"]))
        else:
            raise HTTPException(status_code=400, detail=f"Unknown message role: {msg['role']}")

    anthropic_response = await client.beta.messages.parse(
        model=model_name,
        max_tokens=4096,
        betas=["structured-outputs-2025-11-13"],
        system=system_prompt or SYSTEM_PROMPT,
        messages=messages,
        output_format=GenerateMidiResponse,
    )

    if not isinstance(anthropic_response.parsed_output, GenerateMidiResponse):
        raise HTTPException(status_code=500, detail="Failed to parse structured output from Anthropic.")

    return anthropic_response.parsed_output


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
    parser.add_argument("--prompt", "-p", required=True, help="User prompt for MIDI generation")
    parser.add_argument("--user-id", type=UUID, help="Optional User ID (UUID)")
    parser.add_argument("--track-id", type=UUID, help="Optional Track ID (UUID)")
    parser.add_argument("--loop-id", type=UUID, help="Optional Loop ID (UUID)")
    parser.add_argument("--system-prompt", "-s", default=SYSTEM_PROMPT, help="System prompt")
    parser.add_argument("--num-measures", "-n", type=int, default=1, help="Number of measures to generate")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL_NAME, help="Model name")
    args = parser.parse_args()

    # Create model instance
    model = _GenerateMidi(model_name=args.model, system_prompt=args.system_prompt)
    chat_history = load_chat_history(user_id=None, loop_id=None, system_prompt=SYSTEM_PROMPT)
    chat_history.append(ChatMessage(role="user", content=args.prompt))

    # Run async invoke
    async def main() -> None:
        try:
            response, _ = await generate_midi(
                model_name=args.model,
                expect_measures=args.num_measures,
                chat_history=chat_history,
            )
            midi_events = response.to_midi_events()
            print(json.dumps(midi_events, indent=2))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    asyncio.run(main())
