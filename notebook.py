import marimo

from midiagent.midi_playback import play_midi

__generated_with = "0.18.4"
app = marimo.App(width="medium", app_title="midi-agent")


@app.cell
def _():
    import marimo

    from midiagent.midi_widget import MidiWidget

    midi = marimo.ui.anywidget(MidiWidget())

    # Note options: C4 through C5
    note_options = {
        "C4": 60, "D4": 62, "E4": 64, "F4": 65,
        "G4": 67, "A4": 69, "B4": 71, "C5": 72
    }

    note_dropdown = marimo.ui.dropdown(
        options=note_options,
        value="C4",
        label="Note"
    )

    def send_note(_: None) -> None:
        midi.events = [(0x90, note_dropdown.value, 100)]

    send_note_btn = marimo.ui.button(label="Send Note", on_click=send_note)

    marimo.vstack([midi, marimo.hstack([note_dropdown, send_note_btn])])
    return marimo, midi


@app.cell
def _(marimo, midi):
    # Separate cell for log display - re-renders when widget changes
    _log_text = "\n".join(midi.log) if midi.log else "(no log messages)"
    marimo.md(f"```\n{_log_text}\n```")
    return


@app.cell
def _(marimo):
    # Create state for constraint values that can be updated by the LLM
    get_key, set_key = marimo.state(None)
    get_time_signature, set_time_signature = marimo.state(None)
    get_bpm, set_bpm = marimo.state(None)
    get_dsl_str, set_dsl_str = marimo.state("")
    return (
        get_bpm,
        get_dsl_str,
        get_key,
        get_time_signature,
        set_bpm,
        set_dsl_str,
        set_key,
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
def chat(
    bpm,
    get_dsl_str,
    key,
    marimo,
    midi,
    set_bpm,
    set_dsl_str,
    set_key,
    set_time_signature,
    time_signature,
):
    from midiagent.ai import DslResponse, PlanResponse, PipelineState, pipeline
    from midiagent.constants import MIDI_EVENT_TO_HEX
    from midiagent.midi_playback import play_midi

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

        # Run the pipeline - constraints are now in state
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
        # set_dsl_str("\n".join([f"{event.measure}-{event.beat}-{event.beat_div4}-{event.beat_div16} {event.event}: {event.value}" for event in response.get_midi_events()]))
        set_dsl_str("\n".join([
            f"{event.measure or 'X'}-{event.beat or 'X'}-{event.beat_div4 or 'X'}-{event.beat_div16 or 'X'} {event.event}: {event.value}"
            for event in response.dsl
        ]))

        play_midi(plan.bpm, plan.time_signature, response.get_midi_events(), midi)

        return plan.reasoning

    dsl = marimo.plain_text(get_dsl_str())

    chat = marimo.ui.chat(
        get_response,
        prompts=["Write 4 bars of bouncy piano in the key of G."],
    )

    marimo.vstack([chat, dsl])
    return


if __name__ == "__main__":
    app.run()
