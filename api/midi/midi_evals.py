from typing import TYPE_CHECKING, TypedDict
from uuid import UUID
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import weave

from api.midi import midi_agents

if TYPE_CHECKING:
    from api.midi.midi_agents import GenerateMidiResponse
    from api.chats.chat_types import ModelName
    from api.midi.midi_agents import ChatHistory



EVAL_USER_ID = UUID("00000000-0000-0000-0000-000000000000")
EVAL_TRACK_ID = UUID("00000000-0000-0000-0000-000000000000")
EVAL_LOOP_ID = UUID("00000000-0000-0000-0000-000000000000")

class DatasetEntry(TypedDict):
    model_name: "ModelName"
    expect_measures: int
    chat_history: "ChatHistory"

    @staticmethod
    def create(model_name: "ModelName", expect_measures: int, user_msg: str) -> "DatasetEntry":
        history = midi_agents._GenerateMidi.load_chat_history(
            user_id=EVAL_USER_ID,
            track_id=EVAL_TRACK_ID,
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
        DatasetEntry.create(model_name, expect_measures=2, user_msg="Generate 2 bars of sad waltz in D minor with a 3/4 time signature"),
        DatasetEntry.create(model_name, expect_measures=4, user_msg="Generate 4 bars of experimental jazz in Gm in 7/8 at 180 BPM"),
    ]


def get_eval() -> weave.Evaluation:
    return weave.Evaluation(
        dataset=get_dataset(),
        scorers=[evaluate_num_measures]
    )

@weave.op
def evaluate_num_measures(expect_measures: int, output: "GenerateMidiResponse") -> dict:
    midi_events = output.midi_events
    actual_measures = max(event.measure for event in midi_events) + 1
    return {"ok": actual_measures == expect_measures}


