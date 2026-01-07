import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium", app_title="midi-agent")


@app.cell
def init():
    import dotenv
    import os
    import weave
    import anywidget
    import traitlets
    import marimo

    dotenv.load_dotenv()
    if not os.getenv("WANDB_PROJECT"):
        raise Exception("Missing environment variable \"WANDB_PROJECT\"")

    if not os.getenv("WANDB_API_KEY"):
        raise Exception("Missing environment variable \"WANDB_API_KEY\"")

    weave.init(os.environ["WANDB_PROJECT"])
    return anywidget, marimo, traitlets, weave


@app.cell
def _(anywidget, marimo, traitlets):
    class MidiWidget(anywidget.AnyWidget):
        notes = traitlets.List(traitlets.Int, default_value=[]).tag(sync=True)
        log = traitlets.List(traitlets.Unicode, default_value=[]).tag(sync=True)
        _esm = """
    function render({ model, el }) {
        // Create container with all required elements
        el.innerHTML = `
            <div class="midi-widget">
                <div class="controls">
                    <button id="enable">Enable MIDI</button>
                    <select id="outs"><option>-- select output --</option></select>
                </div>
            </div>
        `;

        // Get references to elements within this widget's container
        const outsEl = el.querySelector("#outs");
        const enableBtn = el.querySelector("#enable");

        const log = (s) => {
            const current = model.get("log") || [];
            model.set("log", [...current, s]);
            model.save_changes();
        };

        let midiAccess = null;
        let output = null;

        function fillOutputs() {
            const outs = [...midiAccess.outputs.values()];
            outsEl.innerHTML = outs
                .map((o) => `<option value="${o.id}">${o.name ?? "MIDI Output"} (${o.manufacturer ?? ""})</option>`)
                .join("");

            outsEl.onchange = () => {
                output = midiAccess.outputs.get(outsEl.value);
                log("Selected output: " + (output?.name || "(none)"));
            };

            // auto-select first output if available
            if (outs.length) {
                outsEl.value = outs[0].id;
                output = outs[0];
                log("Selected output: " + (output?.name || "(none)"));
            } else {
                log("No MIDI outputs found.");
            }
        }

        enableBtn.onclick = async () => {
            try {
                midiAccess = await navigator.requestMIDIAccess();
                log("MIDI enabled.");
                fillOutputs();

                midiAccess.onstatechange = () => {
                    log("MIDI ports changed; refreshing list.");
                    fillOutputs();
                };
            } catch (e) {
                log("Failed to enable MIDI: " + e);
            }
        };

        // Auto-play notes when they change
        model.on("change:notes", () => {
            const notes = model.get("notes");
            if (!notes || notes.length === 0) return;

            log(`Received notes: [${notes.join(", ")}]`);

            if (!output) {
                log("No MIDI output selected.");
                return;
            }

            const ch = 0;      // MIDI channel 1
            const vel = 100;

            notes.forEach((note, i) => {
                const delay = i * 250;  // stagger notes by 250ms
                setTimeout(() => {
                    output.send([0x90 | ch, note, vel]);      // Note On
                    setTimeout(() => output.send([0x80 | ch, note, 0]), 200); // Note Off
                    log(`Played note ${note}`);
                }, delay);
            });
        });
    }
    export default { render };
      """
        _css = """
    .midi-widget {
      font-family: system-ui, -apple-system, sans-serif;
    }
    .midi-widget .controls {
      display: flex;
      gap: 8px;
      margin-bottom: 12px;
      flex-wrap: wrap;
    }
    .midi-widget button {
      padding: 8px 16px;
      border-radius: 6px;
      border: 1px solid #ccc;
      background: linear-gradient(to bottom, #fafafa, #e8e8e8);
      cursor: pointer;
      font-size: 14px;
      transition: all 0.15s ease;
    }
    .midi-widget button:hover {
      background: linear-gradient(to bottom, #e8f4fc, #c8e4f8);
      border-color: #7ab8e0;
    }
    .midi-widget button:active {
      transform: translateY(1px);
    }
    .midi-widget select {
      padding: 8px 12px;
      border-radius: 6px;
      border: 1px solid #ccc;
      background: white;
      font-size: 14px;
      min-width: 200px;
    }
        """

    widget = marimo.ui.anywidget(MidiWidget())
    widget
    return (widget,)


@app.cell
def _(marimo):
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
    send_note_btn = marimo.ui.button(label="Send Note")
    marimo.hstack([note_dropdown, send_note_btn])
    return note_dropdown, send_note_btn


@app.cell
def _(note_dropdown, send_note_btn, widget):
    # When button is clicked, set widget notes to selected note
    send_note_btn
    if note_dropdown.value is not None:
        widget.notes = [note_dropdown.value]
    return


@app.cell
def _(marimo, widget):
    # Display the shared log from the widget
    _log_text = "\n".join(widget.log) if widget.log else "(no log messages)"
    marimo.md(f"```\n{_log_text}\n```")
    return


@app.cell
def chat(marimo, weave):
    @weave.op
    def example_model(messages: list[marimo.ai.ChatMessage], config: marimo.ai.ChatModelConfig) -> str:
        return f"You said: {messages[-1].content}"

    marimo.ui.chat(
        example_model,
        prompts=["Hello", "How are you?"],
    )
    return


if __name__ == "__main__":
    app.run()
