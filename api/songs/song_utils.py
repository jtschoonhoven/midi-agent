"""Utilities for MIDI generation pipeline."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Literal, TypedDict

import pydantic
from langchain.chat_models import init_chat_model
from langchain_core.runnables import RunnableConfig

# Import types from song_types, audio_types, and chat_types modules
from api.songs.song_types import Key, TimeSignature
from api.audio.audio_types import MidiEventType
from api.chats.chat_types import ModelName





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


# class SparseMidiEvent(pydantic.BaseModel):
#     """A MIDI event with optional timing fields (for LLM generation)."""

#     measure: int | None = pydantic.Field(None, gt=0, description="The measure, starting from 1")
#     beat: int | None = pydantic.Field(None, gt=0, lt=9, description="The beat within the measure, starting from 1")
#     beat_div4: int | None = pydantic.Field(None, gt=0, lt=9, description="Divides the beat into quarters")
#     beat_div16: int | None = pydantic.Field(None, gt=0, lt=9, description="Divides the beat into 16ths")
#     event: MidiEventType = pydantic.Field(description="MIDI note or CC event")
#     value: int = pydantic.Field(ge=0, le=100, description="Velocity or CC value, scaled 0-100")


# class DslResponse(pydantic.BaseModel):
#     """Response from generation model with sparse MIDI events."""

#     dsl: list[SparseMidiEvent] = pydantic.Field(description="List of sparse MIDI events")

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
