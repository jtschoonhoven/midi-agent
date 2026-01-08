import anywidget
import traitlets


class MidiWidget(anywidget.AnyWidget):
    """
    A widget for controlling MIDI output.
    """

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
