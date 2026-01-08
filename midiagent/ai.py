import os
from typing import Literal, TypedDict

import dotenv
import marimo
import pydantic
import weave
from langchain.chat_models import init_chat_model
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


class MidiEvent(pydantic.BaseModel):
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
    dsl: list[MidiEvent]


# ==========================================================================
# Graph state
# ==========================================================================


class PipelineState(TypedDict):
    """State passed between nodes in the pipeline."""

    user_request: str
    plan: PlanResponse | None
    response: DslResponse | None


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
"""

GENERATION_PROMPT = """You are a MIDI composer. Given a musical plan, generate the actual MIDI events.

The plan specifies: key, BPM, time signature, style, and chord progression.

Your job is to translate this into concrete MIDI events using the provided schema.
Follow the chord progression and style guidance exactly.
Create musical phrases that fit the specified feel.

Each MidiEvent has:
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
planning_model = init_chat_model("claude-sonnet-4-5", model_provider="anthropic").with_structured_output(PlanResponse)

generation_model = init_chat_model("claude-sonnet-4-5", model_provider="anthropic").with_structured_output(DslResponse)

config = {"configurable": {"thread_id": "1"}}  # `thread_id` is a unique identifier for a given conversation


def planning_node(state: PipelineState) -> dict[Literal["plan"], PlanResponse]:
    """Stage 1: Analyze user request and create a musical plan."""
    messages = [{"role": "system", "content": PLANNING_PROMPT}, {"role": "user", "content": state["user_request"]}]
    plan: PlanResponse = planning_model.invoke(messages, config)
    return {"plan": plan}


def generation_node(state: PipelineState) -> dict[Literal["response"], DslResponse]:
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


def get_response(messages: list[marimo.ai.ChatMessage], _: marimo.ai.ChatModelConfig) -> str:
    # Get the latest user message
    user_request = messages[-1].content if messages else ""

    # Run the pipeline
    result = pipeline.invoke(
        {"user_request": user_request, "plan": None, "response": None}, config={"configurable": {"thread_id": "1"}}
    )

    # Extract outputs
    plan: PlanResponse = result["plan"]
    response: DslResponse = result["response"]

    # Format response showing both stages
    response_parts = [
        "## Musical Plan (Stage 1)",
        f"**Key:** {plan.key}",
        f"**BPM:** {plan.bpm}",
        f"**Time Signature:** {plan.time_signature}",
        f"**Style:** {plan.style}",
        f"**Chord Progression:** {' → '.join(plan.chord_progression)}",
        f"**Reasoning:** {plan.reasoning}",
        "",
        "## Generated MIDI (Stage 2)",
        f"**Events:** {len(response.dsl)} MIDI events generated",
        f"**Chords:** {' → '.join(response.chord_progression)}",
    ]

    dsl_parts: list[str] = []
    measure = 1
    beat = 1
    beat_div4 = 1
    beat_div16 = 1

    for item in response.dsl:
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
        dsl_parts.append(f"{measure}-{beat}-{beat_div4}-{beat_div16} {item.event} {item.value}")

    return "\n".join(response_parts) + "\n" + "\n".join(dsl_parts)
