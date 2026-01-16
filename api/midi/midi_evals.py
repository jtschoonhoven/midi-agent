from collections import defaultdict
from typing import TYPE_CHECKING, TypedDict

import weave
from weave import ObjectRef

from api.chats.chat_constants import MODEL_PROVIDER_MAP
from api.chats.chat_types import ModelName
from api.midi import midi_agents
from api.midi.midi_constants import MIDI_EVENT_TO_HEX

if TYPE_CHECKING:
    from api.midi.midi_agents import GenerateMidiResponse


class DatasetEntry(TypedDict):
    model_name: ModelName
    expect_measures: int
    user_prompt: str

    @staticmethod
    def create(model_name: ModelName, expect_measures: int, user_prompt: str, system_prompt: str) -> "DatasetEntry":
        chat_history = midi_agents.load_chat_history(user_id=None, loop_id=None, system_prompt=system_prompt)
        chat_history.append(midi_agents.ChatMessage(role="user", content=user_prompt))
        return DatasetEntry(model_name=model_name, expect_measures=expect_measures, chat_history=chat_history)


def get_dataset(model_name: ModelName, system_prompt: str) -> list["DatasetEntry"]:
    """
    Return an example dataset for evaluating the MIDI generation agent.
    """

    return [
        DatasetEntry.create(
            model_name=model_name,
            expect_measures=1,
            user_prompt="Upbeat pop music in C major",
            system_prompt=system_prompt,
        ),
        # DatasetEntry.create(
        #     model_name=model_name,
        #     expect_measures=2,
        #     user_prompt="Sad waltz in D minor with a 3/4 time signature",
        #     system_prompt=system_prompt,
        # ),
        # DatasetEntry.create(
        #     model_name=model_name,
        #     expect_measures=4,
        #     user_prompt="Experimental jazz in Gm in 7/8 at 180 BPM",
        #     system_prompt=system_prompt,
        # ),
    ]


class EvalResult(TypedDict):
    """A standard return type for scorers."""

    ok: bool
    error: str | None


@weave.op
def evaluate_midi_events(expect_measures: int, output: "GenerateMidiResponse") -> EvalResult:
    """
    Check that MIDI events are well-formed.
    """
    # Hack: manually resolve ObjectRefs to work around a bug in the weave SDK when running evals
    if isinstance(expect_measures, ObjectRef):
        expect_measures = expect_measures.get()

    # Hack: weave magically serializes pydantic models to dicts when running evals so we have to marshal back to the model type
    if isinstance(output, dict):
        output = midi_agents.GenerateMidiResponse.model_validate(output)

    # Group events by note (event name) and count note-on vs note-off
    note_counts: dict[str, int] = defaultdict(lambda: 0)

    try:
        for index, event in enumerate(output.to_midi_events()):
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


if __name__ == "__main__":
    """
    Compare midi generation models.

    Docs:
    - https://docs.wandb.ai/weave/guides/core-types/evaluations
    https://docs.wandb.ai/weave/cookbooks/leaderboard_quickstart
    """
    import argparse
    import asyncio
    import os

    from dotenv import load_dotenv

    load_dotenv()
    weave.init(os.environ["PROJECT_ID"])

    all_models = MODEL_PROVIDER_MAP.keys()

    parser = argparse.ArgumentParser(description="Compare midi generation models")
    parser.add_argument("--trials", "-t", type=int, default=3, help="Trials per model (optional)")
    parser.add_argument("--models", "-m", nargs="+", choices=all_models, default=all_models, help="Models (optional)")
    parser.add_argument("--system-prompt", "-s", default=midi_agents.SYSTEM_PROMPT, help="System prompt (optional)")
    args = parser.parse_args()

    async def evaluate() -> None:
        for model_name in args.models:
            eval = weave.Evaluation(
                name="generate_midi",
                dataset=get_dataset(model_name, args.system_prompt),
                scorers=[evaluate_midi_events],
                trials=args.trials,
            )
            await eval.evaluate(midi_agents.generate_midi, __weave={"display_name": f"{eval.name}:{model_name}"})

    asyncio.run(evaluate())
