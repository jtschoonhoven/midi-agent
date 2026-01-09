from dataclasses import dataclass
import os
from typing import TypedDict

import dotenv
import marimo
import pydantic
import weave
from langchain.chat_models import init_chat_model
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from midiagent.types import Key, MidiEventType, TimeSignature


dotenv.load_dotenv()
if not os.getenv("PROJECT_ID"):
    raise Exception('Missing environment variable "PROJECT_ID"')

if not os.getenv("WANDB_API_KEY"):
    raise Exception('Missing environment variable "WANDB_API_KEY"')

weave.init(os.environ["PROJECT_ID"])

# ==========================================================================
# Pydantic schemas
# ==========================================================================


class SparseMidiEvent(pydantic.BaseModel):
    """
    A MIDI event (note or CC) at a given point in time.
    Measure, beat, beat_div4, & beat_div16 collectively specify the timing.
    If unspecified, timing fields are assumed unchanged from the previous event, resetting to "1" whenever their parent is updated.
    """

    measure: int | None = pydantic.Field(None, gt=0, description="The measure, starting from 1.")
    beat: int | None = pydantic.Field(None, gt=0, lt=9, description="The beat within the measure, starting from 1 (quarter notes in */4 time).")
    beat_div4: int | None = pydantic.Field(None, gt=0, lt=9, description="Divides the beat into quarters (16th notes in */4 time).")
    beat_div16: int | None = pydantic.Field(None, gt=0, lt=9, description="Divides the beat into 16ths (64th notes in */4 time).")
    event: MidiEventType = pydantic.Field(description="Human-readable representation of a MIDI note or CC event. Use the provided schema.")
    value: int = pydantic.Field(gt=-1, lt=101, description="The value of a CC event, or the velocity of a note event, scaled 0-100 (inclusive).")


@dataclass
class MidiEvent:
    """Clone of SparseMidiEvent with required fields."""
    measure: int
    beat: int
    beat_div4: int
    beat_div16: int
    event: MidiEventType
    value: int

class PlanResponse(pydantic.BaseModel):
    """
    High-level musical decisions before MIDI generation.
    """

    key: Key = pydantic.Field(description="The musical key for the composition")
    bpm: int = pydantic.Field(gt=29, lt=361, description="Tempo in beats-per-minute, 30-360")
    time_signature: TimeSignature = pydantic.Field(description="Time signature for the piece")
    style: str = pydantic.Field(description="Brief description of the musical style/feel")
    chord_progression: list[str] = pydantic.Field(
        description="Chord progression using chord symbols (e.g. ['Gbm7', 'D', 'Em', 'C'])"
    )
    reasoning: str = pydantic.Field(description="Explanation of musical choices for evaluation")


class DslResponse(pydantic.BaseModel):
    """Final response schema with full MIDI events."""
    dsl: list[SparseMidiEvent]

    def get_midi_events(self) -> list[MidiEvent]:
        result: list[MidiEvent] = []

        measure = 1
        beat = 1
        beat_div4 = 1
        beat_div16 = 1

        for item in self.dsl:
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

            result.append(MidiEvent(measure=measure, beat=beat, beat_div4=beat_div4, beat_div16=beat_div16, event=item.event, value=item.value))

        return result


# ==========================================================================
# Graph state
# ==========================================================================


class PipelineState(TypedDict):
    """State passed between nodes in the pipeline."""

    user_request: str
    # Optional constraints - if set, planning node must use these values
    key: Key | None
    bpm: int | None
    time_signature: TimeSignature | None
    # Outputs from pipeline nodes
    plan: PlanResponse | None
    response: DslResponse | None


class PlanningNodeOutput(TypedDict):
    """Return type for planning_node - updates plan and constraint fields."""

    plan: PlanResponse
    key: Key
    bpm: int
    time_signature: TimeSignature


class GenerationNodeOutput(TypedDict):
    """Return type for generation_node - updates response field."""

    response: DslResponse


# ==========================================================================
# System prompts
# ==========================================================================

PLANNING_PROMPT = """You are a music theory expert and composition planner.

Your job is to analyze a user's musical request and create a high-level plan that includes:
- The appropriate key for the piece
- A suitable tempo (BPM)
- The time signature
- A chord progression that fits the style
- A brief description of the style/feel

Be thoughtful about your choices. Consider the mood, genre, and any specific requests the user made.
Explain your reasoning so your choices can be evaluated.

Examples of good reasoning:
- "The user requested 'bouncy piano' which suggests an upbeat feel. I chose 120 BPM in G major with a I-V-vi-IV progression for its bright, accessible sound."
- "For a melancholic ballad, I selected D minor at 72 BPM with a i-VI-III-VII progression to create emotional depth."

IMPORTANT: If the user has specified constraints (key, time signature, or BPM), you MUST use those exact values in your plan (unless explicitly asked to change them). Only generate values for parameters that are not constrained.
"""

GENERATION_PROMPT = """You are a MIDI composer. Given a musical plan, generate the actual MIDI events.

The plan specifies: key, BPM, time signature, style, and chord progression.

Your job is to translate this into concrete MIDI events using the provided schema.
Follow the chord progression and style guidance exactly.
Create musical phrases that fit the specified feel.

Each SparseMidiEvent has:
- measure: which measure (starting from 1)
- beat: which beat in the measure (starting from 1)
- beat_div4: subdivision of the beat into quarters
- beat_div16: further subdivision into 16ths
- event: the note name (e.g. "C4", "G3") or control ("Sustain", "ModWheel")
- value: velocity/intensity 0-100

Generate a musically coherent sequence that realizes the plan."""

# ==========================================================================
# Pipeline nodes
# ==========================================================================

if not os.getenv("ANTHROPIC_API_KEY"):
    raise Exception('Missing environment variable "ANTHROPIC_API_KEY"')

# Initialize models with structured output
planning_model = init_chat_model("claude-haiku-4-5", model_provider="anthropic").with_structured_output(PlanResponse)
generation_model = init_chat_model("claude-haiku-4-5", model_provider="anthropic").with_structured_output(DslResponse)



def planning_node(state: PipelineState, config: RunnableConfig) -> PlanningNodeOutput:
    """Stage 1: Analyze user request and create a musical plan."""
    # Build constraint info for the prompt from state
    constraints = []
    if state.get("key"):
        constraints.append(f"Musical Key: {state['key']} (REQUIRED - use this exact key unless the user explicitly requests another)")
    if state.get("time_signature"):
        constraints.append(f"Time Signature: {state['time_signature']} (REQUIRED - use this exact time signature unless the user explicitly requests another)")
    if state.get("bpm"):
        constraints.append(f"BPM: {state['bpm']} (REQUIRED - use this exact tempo unless the user explicitly requests another)")

    user_content = state["user_request"]
    if constraints:
        user_content += "\n\nUser constraints (you MUST use these values):\n" + "\n".join(constraints)

    messages = [{"role": "system", "content": PLANNING_PROMPT}, {"role": "user", "content": user_content}]
    plan: PlanResponse = planning_model.invoke(messages, config)
    
    # Update state with both the plan and the LLM's chosen values
    return {
        "plan": plan,
        "key": plan.key,
        "bpm": plan.bpm,
        "time_signature": plan.time_signature,
    }


def generation_node(state: PipelineState, config: RunnableConfig) -> GenerationNodeOutput:
    """
    Stage 2: Generate MIDI events based on the musical plan.
    """
    plan = state["plan"]
    generation_request = f"""Generate MIDI events for this musical plan:

    Key: {plan.key}
    BPM: {plan.bpm}
    Time Signature: {plan.time_signature}
    Style: {plan.style}
    Chord Progression: {" - ".join(plan.chord_progression)}

    Original user request: {state["user_request"]}
"""
    messages = [{"role": "system", "content": GENERATION_PROMPT}, {"role": "user", "content": generation_request}]
    response: DslResponse = generation_model.invoke(messages, config)
    return {"response": response}


# ==========================================================================
# Build the graph
# ==========================================================================

workflow = StateGraph(PipelineState)

# Add nodes
workflow.add_node("planning", planning_node)
workflow.add_node("generation", generation_node)

# Wire edges: START → planning → generation → END
workflow.add_edge(START, "planning")
workflow.add_edge("planning", "generation")
workflow.add_edge("generation", END)

# Compile with checkpointing for state inspection
pipeline = workflow.compile(checkpointer=InMemorySaver())

# ==========================================================================
# Chat interface
# ==========================================================================



def get_response(
    messages: list[marimo.ai.ChatMessage],
    config: marimo.ai.ChatModelConfig,
) -> tuple[PlanResponse, DslResponse]:
    """Chat handler that uses config for constraints."""
    # Get the latest user message
    user_request = messages[-1].content if messages else ""

    # Extract constraints from marimo config and pass them via state
    initial_state: PipelineState = {
        "user_request": user_request,
        "key": getattr(config, "key", None),
        "bpm": getattr(config, "bpm", None),
        "time_signature": getattr(config, "time_signature", None),
        "plan": None,
        "response": None,
    }

    # Run the pipeline - constraints are now in state
    result = pipeline.invoke(
        initial_state,
        config={"configurable": {"thread_id": "1"}},
    )

    # Extract outputs
    plan: PlanResponse = result["plan"]
    response: DslResponse = result["response"]

    return plan, response