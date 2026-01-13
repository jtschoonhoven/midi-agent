import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium", app_title="midi-agent")


@app.cell
def _():
    import marimo
    from midiagent.midi_widget import MidiWidget

    midi = marimo.ui.anywidget(MidiWidget())
    midi
    return marimo, midi


@app.cell
def _(marimo, midi):
    # Separate cell for log display - re-renders when widget changes
    log_text = "\n".join(midi.log) if midi.log else "(no log messages)"
    marimo.Html(
        f"""
        <div id="midi-logs", style="max-height: 200px; overflow: auto; white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; color: #334; font-size: 12px;">{log_text}</div>
        <script>const el = document.getElementById("midi-logs"); el.scrollTop = el.scrollHeight;</script>
        """
    )
    return


@app.cell
def _(marimo):
    # Create state for constraint values that can be updated by the LLM
    get_key, set_key = marimo.state(None)
    get_time_signature, set_time_signature = marimo.state(None)
    get_bpm, set_bpm = marimo.state(None)
    get_midi_events, set_midi_events = marimo.state([])
    return (
        get_bpm,
        get_key,
        get_midi_events,
        get_time_signature,
        set_bpm,
        set_key,
        set_midi_events,
        set_time_signature,
    )


@app.cell
def _(
    get_bpm,
    get_key,
    get_time_signature,
    marimo,
    set_bpm,
    set_key,
    set_time_signature,
):
    from midiagent.constants import KEYS, TIME_SIGNATURES

    key = marimo.ui.dropdown(
        options=KEYS,
        value=get_key(),
        label="Key",
        allow_select_none=True,
        searchable=False,
        on_change=set_key,
    )

    time_signature = marimo.ui.dropdown(
        options=TIME_SIGNATURES,
        value=get_time_signature(),
        label="Time Signature",
        allow_select_none=True,
        searchable=False,
        on_change=set_time_signature,
    )

    bpm = marimo.ui.dropdown(
        options=[n for n in range(30, 361)],
        value=get_bpm(),
        label="BPM",
        allow_select_none=True,
        searchable=True,
        on_change=set_bpm,
    )

    marimo.hstack([key, time_signature, bpm], justify="start")
    return bpm, key, time_signature


@app.cell
def _(marimo):
    from midiagent.constants import SUPPORTED_MODELS

    planning_model_name = marimo.ui.dropdown(
        options={m[1]: m for m in SUPPORTED_MODELS},
        value=SUPPORTED_MODELS[-1][1],
        label="Planning Model",
        allow_select_none=True,
        searchable=False,
    )

    generation_model_name = marimo.ui.dropdown(
        options={m[1]: m for m in SUPPORTED_MODELS},
        value=SUPPORTED_MODELS[-1][1],
        label="Generation Model",
        allow_select_none=True,
        searchable=False,
    )
    return generation_model_name, planning_model_name


@app.cell
def chat(
    bpm,
    generation_model_name,
    key,
    marimo,
    planning_model_name,
    set_bpm,
    set_key,
    set_midi_events,
    set_time_signature,
    time_signature,
):
    import os

    from langchain.chat_models import BaseChatModel, init_chat_model
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.graph import END, START, StateGraph
    from midiagent.ai import (
        GENERATION_PROMPT,
        PLANNING_PROMPT,
        DslResponse,
        GenerationNodeOutput,
        PipelineState,
        PlanningNodeOutput,
        PlanResponse,
    )
    from midiagent.types import SupportedModel

    def get_model(supported_model: SupportedModel) -> BaseChatModel:
        model_provider, model_name = supported_model
        if model_provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
            raise Exception('Missing required environment variable "ANTHROPIC_API_KEY"')
        if model_provider == "openai" and not os.getenv("OPENAI_API_KEY"):
            raise Exception('Missing required environment variable "OPENAI_API_KEY"')
        return init_chat_model(model_name, model_provider=model_provider)

    # Initialize models with structured output
    planning_model = get_model(planning_model_name.value).with_structured_output(PlanResponse)
    generation_model = get_model(generation_model_name.value).with_structured_output(DslResponse)

    def planning_node(state: PipelineState, config: RunnableConfig) -> PlanningNodeOutput:
        """Stage 1: Analyze user request and create a musical plan."""
        # Build constraint info for the prompt from state
        constraints = []
        if state.get("key"):
            constraints.append(f"Current key: {state['key']}")
        if state.get("time_signature"):
            constraints.append(f"Current time signature: {state['time_signature']}")
        if state.get("bpm"):
            constraints.append(f"Current BPM: {state['bpm']}")

        user_content = state["user_request"]
        if constraints:
            user_content += (
                "\n\nCurrent settings (use these unless the user explicitly requests otherwise):\n"
                + "\n".join(constraints)
            )

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
            "key": key.value,
            "bpm": bpm.value,
            "time_signature": time_signature.value,
            "plan": None,
            "response": None,
        }

        result = pipeline.invoke(
            initial_state,
            config={"configurable": {"thread_id": "1"}},
        )

        # Extract outputs
        plan: PlanResponse = result["plan"]
        response: DslResponse = result["response"]

        # Update notebook state using mo.state setters
        set_key(plan.key)
        set_time_signature(plan.time_signature)
        set_bpm(plan.bpm)

        midi_events = response.get_midi_events()
        set_midi_events(midi_events)

        return plan.reasoning

    chat = marimo.ui.chat(
        get_response,
        prompts=["Write 4 bars of bouncy piano in the key of G."],
    )

    marimo.vstack([marimo.hstack([planning_model_name, generation_model_name], justify="start"), chat])
    return


@app.cell
def _(get_bpm, get_midi_events, get_time_signature, marimo, midi):
    from midiagent.midi_playback import play_midi

    midi_events = get_midi_events()

    loop = marimo.ui.switch(False, label="Loop", disabled=(not midi_events))

    def play() -> None:
        play_midi(get_bpm(), get_time_signature(), midi_events, midi)
        if loop.value is True:
            print("looping!")
            print(str(loop.value))
            play()

    table = marimo.ui.table(
        [event.model_dump() for event in midi_events], pagination=False, selection=None, on_change=lambda _: play()
    )
    button = marimo.ui.button(label="Play", disabled=(not midi_events), on_click=lambda _: play())

    marimo.vstack([marimo.hstack([button, loop], justify="start"), table])
    return


if __name__ == "__main__":
    app.run()
