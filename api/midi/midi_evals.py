from collections import defaultdict
from typing import TYPE_CHECKING, TypedDict
from uuid import UUID

import weave
from langchain_core.messages import HumanMessage

from api.midi import midi_agents
from api.midi.midi_constants import MIDI_EVENT_TO_HEX

if TYPE_CHECKING:
    from api.chats.chat_types import ModelName
    from api.midi.midi_agents import ChatHistory, GenerateMidiResponse


EVAL_USER_ID = UUID("00000000-0000-0000-0000-000000000000")
EVAL_LOOP_ID = UUID("00000000-0000-0000-0000-000000000000")


class DatasetEntry(TypedDict):
    model_name: "ModelName"
    expect_measures: int
    chat_history: "ChatHistory"

    @staticmethod
    def create(model_name: "ModelName", expect_measures: int, user_msg: str) -> "DatasetEntry":
        history = midi_agents._GenerateMidi.load_chat_history(
            user_id=EVAL_USER_ID,
            loop_id=EVAL_LOOP_ID,
            system_prompt=midi_agents.GENERATION_PROMPT,
        )
        return DatasetEntry(model_name, expect_measures, history + [HumanMessage(content=user_msg)])


def get_dataset() -> list["DatasetEntry"]:
    """
    Return an example dataset for evaluating the MIDI generation agent.
    """
    model_name = midi_agents.DEFAULT_MODEL_NAME
    return [
        DatasetEntry.create(model_name, expect_measures=1, user_msg="Generate 1 bar of upbeat pop music in C major"),
        DatasetEntry.create(
            model_name, expect_measures=2, user_msg="Generate 2 bars of sad waltz in D minor with a 3/4 time signature"
        ),
        DatasetEntry.create(
            model_name, expect_measures=4, user_msg="Generate 4 bars of experimental jazz in Gm in 7/8 at 180 BPM"
        ),
    ]


def get_eval() -> weave.Evaluation:
    return weave.Evaluation(dataset=get_dataset(), scorers=[evaluate_midi_events])


class EvalResult(TypedDict):
    """A standard return type for scorers."""

    ok: bool
    error: str | None


@weave.op
def evaluate_midi_events(expect_measures: int, output: "GenerateMidiResponse") -> EvalResult:
    """
    Check that MIDI events are well-formed.
    """
    midi_events = output.midi_events

    # Group events by note (event name) and count note-on vs note-off
    note_counts: dict[str, int] = defaultdict(lambda: 0)

    try:
        for index, event in enumerate(midi_events):
            # Validate measures
            if event.measure > expect_measures:
                raise AssertionError(f"Midi event at index {index} is outside the loop's length: {expect_measures}")

            # Validate event type
            if event.event not in MIDI_EVENT_TO_HEX:
                raise AssertionError(f"Invalid midi event at index {index}: {event.event}")

            # Validate note number
            note_type, note_number = MIDI_EVENT_TO_HEX[event.event]
            if note_number < 0 or note_number > 127:
                raise AssertionError(f"Invalid note number at index {index}: {note_number}")

            # Skip control events
            if note_type != 0x90:
                continue

            note_counts[event.event] += 1 if event.value > 0 else -1

            # Check that note-off events don't precede note-on events
            if note_counts[event.event] < 0:
                raise AssertionError(f"Note off event at index {index} has no matching note on event")

    except AssertionError as e:
        return EvalResult(ok=False, error=str(e))

    for note, count in note_counts.items():
        if count != 0:
            return EvalResult(
                ok=False,
                error=f"Note {note} has an unbalanced number of note-on and note-off events: {count}",
            )

    return EvalResult(ok=True, error=None)
