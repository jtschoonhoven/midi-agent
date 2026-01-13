"""Utilities for MIDI generation pipeline."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Literal, TypedDict

from langchain.chat_models import init_chat_model
from langchain_core.runnables import RunnableConfig
import pydantic

if TYPE_CHECKING:
    from api.midi.midi_routes import GenerateRequest

# Type aliases
Key = Literal["Ab", "A", "A#", "Bb", "B", "C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb", "G", "G#"]
TimeSignature = Literal["3/4", "4/4", "5/4", "6/8", "7/8"]
ModelName = Literal[
    "claude-haiku-4-5",
    "claude-sonnet-4-5",
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-5-2",
    "gpt-5-mini",
    "gpt-5-nano",
]
MidiEventType = Literal[
    "C-1",
    "C#-1",
    "Db-1",
    "D-1",
    "D#-1",
    "Eb-1",
    "E-1",
    "F-1",
    "F#-1",
    "Gb-1",
    "G-1",
    "G#-1",
    "Ab-1",
    "A-1",
    "A#-1",
    "Bb-1",
    "B-1",
    "C0",
    "C#0",
    "Db0",
    "D0",
    "D#0",
    "Eb0",
    "E0",
    "F0",
    "F#0",
    "Gb0",
    "G0",
    "G#0",
    "Ab0",
    "A0",
    "A#0",
    "Bb0",
    "B0",
    "C1",
    "C#1",
    "Db1",
    "D1",
    "D#1",
    "Eb1",
    "E1",
    "F1",
    "F#1",
    "Gb1",
    "G1",
    "G#1",
    "Ab1",
    "A1",
    "A#1",
    "Bb1",
    "B1",
    "C2",
    "C#2",
    "Db2",
    "D2",
    "D#2",
    "Eb2",
    "E2",
    "F2",
    "F#2",
    "Gb2",
    "G2",
    "G#2",
    "Ab2",
    "A2",
    "A#2",
    "Bb2",
    "B2",
    "C3",
    "C#3",
    "Db3",
    "D3",
    "D#3",
    "Eb3",
    "E3",
    "F3",
    "F#3",
    "Gb3",
    "G3",
    "G#3",
    "Ab3",
    "A3",
    "A#3",
    "Bb3",
    "B3",
    "C4",
    "C#4",
    "Db4",
    "D4",
    "D#4",
    "Eb4",
    "E4",
    "F4",
    "F#4",
    "Gb4",
    "G4",
    "G#4",
    "Ab4",
    "A4",
    "A#4",
    "Bb4",
    "B4",
    "C5",
    "C#5",
    "Db5",
    "D5",
    "D#5",
    "Eb5",
    "E5",
    "F5",
    "F#5",
    "Gb5",
    "G5",
    "G#5",
    "Ab5",
    "A5",
    "A#5",
    "Bb5",
    "B5",
    "C6",
    "C#6",
    "Db6",
    "D6",
    "D#6",
    "Eb6",
    "E6",
    "F6",
    "F#6",
    "Gb6",
    "G6",
    "G#6",
    "Ab6",
    "A6",
    "A#6",
    "Bb6",
    "B6",
    "C7",
    "C#7",
    "Db7",
    "D7",
    "D#7",
    "Eb7",
    "E7",
    "F7",
    "F#7",
    "Gb7",
    "G7",
    "G#7",
    "Ab7",
    "A7",
    "A#7",
    "Bb7",
    "B7",
    "C8",
    "C#8",
    "Db8",
    "D8",
    "D#8",
    "Eb8",
    "E8",
    "F8",
    "F#8",
    "Gb8",
    "G8",
    "G#8",
    "Ab8",
    "A8",
    "A#8",
    "Bb8",
    "B8",
    "C9",
    "C#9",
    "Db9",
    "D9",
    "D#9",
    "Eb9",
    "E9",
    "F9",
    "F#9",
    "Gb9",
    "G9",
    "Sustain",
    "ModWheel",
    "AllNotesOff",
    "ResetControllers",
]


# Pydantic models used by this module
class MidiEvent(pydantic.BaseModel):
    """A fully resolved MIDI event with explicit timing."""

    measure: int = pydantic.Field(gt=0, description="The measure, starting from 1")
    beat: int = pydantic.Field(gt=0, lt=9, description="The beat within the measure, starting from 1")
    beat_div4: int = pydantic.Field(gt=0, lt=9, description="Divides the beat into quarters (16th notes)")
    beat_div16: int = pydantic.Field(gt=0, lt=9, description="Divides the beat into 16ths (64th notes)")
    event: MidiEventType = pydantic.Field(description="MIDI note or CC event")
    value: int = pydantic.Field(ge=0, le=100, description="Velocity or CC value, scaled 0-100")


class PlanResponse(pydantic.BaseModel):
    """High-level musical plan from the planning stage."""

    key: Key = pydantic.Field(description="The musical key for the composition")
    bpm: int = pydantic.Field(gt=29, lt=361, description="Tempo in beats-per-minute, 30-360")
    time_signature: TimeSignature = pydantic.Field(description="Time signature for the piece")
    measures: int = pydantic.Field(gt=0, lt=33, description="Number of measures in the composition (1-32)")
    style: str = pydantic.Field(description="Brief description of the musical style/feel")
    chord_progression: list[str] = pydantic.Field(
        description="Chord progression using chord symbols (e.g. ['Gbm7', 'D', 'Em', 'C'])"
    )
    reasoning: str = pydantic.Field(description="Explanation of musical choices for evaluation")


class SparseMidiEvent(pydantic.BaseModel):
    """A MIDI event with optional timing fields (for LLM generation)."""

    measure: int | None = pydantic.Field(None, gt=0, description="The measure, starting from 1")
    beat: int | None = pydantic.Field(None, gt=0, lt=9, description="The beat within the measure, starting from 1")
    beat_div4: int | None = pydantic.Field(None, gt=0, lt=9, description="Divides the beat into quarters")
    beat_div16: int | None = pydantic.Field(None, gt=0, lt=9, description="Divides the beat into 16ths")
    event: MidiEventType = pydantic.Field(description="MIDI note or CC event")
    value: int = pydantic.Field(ge=0, le=100, description="Velocity or CC value, scaled 0-100")


class DslResponse(pydantic.BaseModel):
    """Response from generation model with sparse MIDI events."""

    dsl: list[SparseMidiEvent] = pydantic.Field(description="List of sparse MIDI events")


# Mapping from model name to (provider, model) tuple
MODEL_PROVIDER_MAP: dict[ModelName, tuple[str, str]] = {
    "claude-haiku-4-5": ("anthropic", "claude-haiku-4-5"),
    "claude-sonnet-4-5": ("anthropic", "claude-sonnet-4-5"),
    "gpt-4o-mini": ("openai", "gpt-4o-mini"),
    "gpt-4o": ("openai", "gpt-4o"),
    "gpt-5-2": ("openai", "gpt-5-2"),
    "gpt-5-mini": ("openai", "gpt-5-mini"),
    "gpt-5-nano": ("openai", "gpt-5-nano"),
}

# ==========================================================================
# System prompts
# ==========================================================================

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

# ==========================================================================
# Pipeline state
# ==========================================================================


class PipelineState(TypedDict):
    """State passed between nodes in the pipeline."""

    user_request: str
    key: Key | None
    bpm: int | None
    time_signature: TimeSignature | None
    measures: int | None
    plan: PlanResponse | None
    response: DslResponse | None


class PlanningNodeOutput(TypedDict):
    """Return type for planning_node."""

    plan: PlanResponse
    key: Key
    bpm: int
    time_signature: TimeSignature


class GenerationNodeOutput(TypedDict):
    """Return type for generation_node."""

    response: DslResponse


# ==========================================================================
# Utilities
# ==========================================================================


def sparse_to_full_midi_events(sparse_events: list[SparseMidiEvent]) -> list[MidiEvent]:
    """Convert sparse MIDI events to fully resolved events with explicit timing."""
    result: list[MidiEvent] = []

    measure = 1
    beat = 1
    beat_div4 = 1
    beat_div16 = 1

    for item in sparse_events:
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
    # )
    # all_notes_off = MidiEvent(
    #     measure=measure + 1, beat=1, beat_div4=1, beat_div16=1, event="AllNotesOff", value=100
    # )
    # reset_controllers = MidiEvent(
    #     measure=measure + 1, beat=1, beat_div4=1, beat_div16=1, event="ResetControllers", value=100
    # )

    # result.append(sustain_off)
    # result.append(all_notes_off)
    # result.append(reset_controllers)

    return result


# ==========================================================================
# Pipeline nodes
# ==========================================================================


def _build_constraints_str(state: PipelineState) -> str:
    """Build constraint info for the prompt from state."""
    constraints = []
    if state.get("key"):
        constraints.append(f"Current key: {state['key']}")
    if state.get("time_signature"):
        constraints.append(f"Current time signature: {state['time_signature']}")
    if state.get("bpm"):
        constraints.append(f"Current BPM: {state['bpm']}")

    if not constraints:
        return ""
    return "\n\nCurrent settings (use these unless the user explicitly requests otherwise):\n" + "\n".join(constraints)


def planning_node(state: PipelineState, config: RunnableConfig) -> PlanningNodeOutput:
    """Stage 1: Analyze user request and create a musical plan."""
    # Get model from config
    planning_model = config.get("configurable", {}).get("planning_model")
    if not planning_model:
        raise ValueError("planning_model must be provided in config")

    # Build constraint info for the prompt from state
    constraints = []
    if state.get("key"):
        constraints.append(f"Current key: {state['key']}")
    if state.get("time_signature"):
        constraints.append(f"Current time signature: {state['time_signature']}")
    if state.get("bpm"):
        constraints.append(f"Current BPM: {state['bpm']}")

    user_content = state["user_request"]
    user_content += _build_constraints_str(state)

    messages = [{"role": "system", "content": PLANNING_PROMPT}, {"role": "user", "content": user_content}]
    plan: PlanResponse = planning_model.invoke(messages, config)

    return {
        "plan": plan,
        "key": plan.key,
        "bpm": plan.bpm,
        "time_signature": plan.time_signature,
    }


def generation_node(state: PipelineState, config: RunnableConfig) -> GenerationNodeOutput:
    """Stage 2: Generate MIDI events based on the musical plan."""
    # Get model from config
    generation_model = config.get("configurable", {}).get("generation_model")
    if not generation_model:
        raise ValueError("generation_model must be provided in config")

    plan = state["plan"]
    if not plan:
        raise ValueError("Plan must be set before generation")

    # Build measures constraint if specified
    measures_info = f"\n    Measures: {state['measures']}" if state.get("measures") else ""

    generation_request = f"""Generate MIDI events for this musical plan:

    Key: {plan.key}
    BPM: {plan.bpm}
    Time Signature: {plan.time_signature}
    Style: {plan.style}
    Chord Progression: {" - ".join(plan.chord_progression)}{measures_info}

    Original user request: {state["user_request"]}
"""
    messages = [{"role": "system", "content": GENERATION_PROMPT}, {"role": "user", "content": generation_request}]
    response: DslResponse = generation_model.invoke(messages, config)
    return {"response": response}


# ==========================================================================
# Pipeline execution
# ==========================================================================


def run_generation_pipeline(request: GenerateRequest) -> tuple[PlanResponse, list[MidiEvent]]:
    """Execute the full MIDI generation pipeline.

    Returns:
        Tuple of (plan, midi_events) from the pipeline execution
    """
    # Get provider and model names from request
    plan_provider, plan_model_name = MODEL_PROVIDER_MAP[request.plan_model]
    generate_provider, generate_model_name = MODEL_PROVIDER_MAP[request.generate_model]

    # Check for required API keys based on providers
    if plan_provider == "anthropic" or generate_provider == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY environment variable is required for Anthropic models")

    if plan_provider == "openai" or generate_provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI models")

    # Initialize models with requested models
    planning_model = init_chat_model(plan_model_name, model_provider=plan_provider).with_structured_output(PlanResponse)
    generation_model = init_chat_model(generate_model_name, model_provider=generate_provider).with_structured_output(
        DslResponse
    )

    # Initial state
    initial_state: PipelineState = {
        "user_request": request.prompt,
        "key": request.key,
        "bpm": request.bpm,
        "time_signature": request.time_signature,
        "measures": request.measures,
        "plan": None,
        "response": None,
    }

    # Config with models and thread_id
    config: RunnableConfig = {
        "configurable": {
            "thread_id": str(request.thread_id),
            "planning_model": planning_model,
            "generation_model": generation_model,
        }
    }

    # Execute pipeline manually (without LangGraph for simplicity)
    state = initial_state.copy()

    # Step 1: Planning
    planning_output = planning_node(state, config)
    state["plan"] = planning_output["plan"]
    state["key"] = planning_output["key"]
    state["bpm"] = planning_output["bpm"]
    state["time_signature"] = planning_output["time_signature"]

    # Step 2: Generation
    generation_output = generation_node(state, config)
    state["response"] = generation_output["response"]

    # Convert sparse events to full events
    if not state["response"]:
        raise ValueError("Generation failed to produce a response")
    if not state["plan"]:
        raise ValueError("Planning failed to produce a plan")

    midi_events = sparse_to_full_midi_events(state["response"].dsl)

    return (state["plan"], midi_events)
