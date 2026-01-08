import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium", app_title="midi-agent")


@app.cell
def _():
    import marimo

    from midiagent.midi_widget import MidiWidget

    widget = marimo.ui.anywidget(MidiWidget())
    widget
    return marimo, widget


@app.cell
def _(marimo):
    # Note options: C4 through C5
    note_options = {"C4": 60, "D4": 62, "E4": 64, "F4": 65, "G4": 67, "A4": 69, "B4": 71, "C5": 72}
    note_dropdown = marimo.ui.dropdown(options=note_options, value="C4", label="Note")
    send_note_btn = marimo.ui.button(label="Send Note")
    marimo.hstack([note_dropdown, send_note_btn])
    return note_dropdown, send_note_btn


@app.cell
def _(marimo, note_dropdown, send_note_btn, widget):
    # When button is clicked, set widget notes to selected note
    send_note_btn
    if note_dropdown.value is not None:
        widget.notes = [note_dropdown.value]
    return (marimo,)


@app.cell
def _(marimo, widget):
    # Display the shared log from the widget
    _log_text = "\n".join(widget.log) if widget.log else "(no log messages)"
    marimo.md(f"```\n{_log_text}\n```")
    return (marimo,)


@app.cell
def chat(marimo):
    from midiagent.ai import get_response

    marimo.ui.chat(
        get_response,
        prompts=["Write 4 bars of bouncy piano in the key of G."],
    )

    return


if __name__ == "__main__":
    app.run()
