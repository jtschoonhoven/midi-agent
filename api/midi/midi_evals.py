import logging
import random
from collections import defaultdict
from typing import TYPE_CHECKING, Optional, TypedDict, Union

import weave

from api.chats.chat_constants import MODEL_PROVIDER_MAP
from api.chats.chat_types import ModelName
from api.instruments.instrument_types import InstrumentType
from api.midi import midi_agents
from api.midi.midi_constants import MIDI_EVENT_TO_HEX
from api.songs.song_constants import ADJECTIVES, NOUNS, TIME_SIGNATURE_BEATS_PER_MEASURE
from api.songs.song_types import Key, TimeSignature

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)


class DatasetEntry(TypedDict):
    model_name: ModelName
    user_prompt: str
    expect_measures: int
    expect_time_signature: TimeSignature
    expect_bpm: int
    expect_key: Key
    expect_instrument: InstrumentType

    @staticmethod  # type: ignore [misc]
    def create(
        *,
        user_prompt: str,
        system_prompt: str,
        expect_measures: int,
        expect_time_signature: TimeSignature,
        expect_bpm: int,
        expect_key: Key,
        expect_instrument: InstrumentType,
    ) -> "DatasetEntry":
        chat_history = midi_agents.load_chat_history(user_id=None, loop_id=None, system_prompt=system_prompt)
        chat_history.append(midi_agents.ChatMessage(role="user", content=user_prompt))
        return DatasetEntry(
            chat_history=chat_history,
            expect_measures=expect_measures,
            expect_time_signature=expect_time_signature,
            expect_bpm=expect_bpm,
            expect_key=expect_key,
            expect_instrument=expect_instrument,
        )


def get_dataset(system_prompt: str) -> list["DatasetEntry"]:
    """
    Return an example dataset for evaluating the MIDI generation agent.
    """

    return [
        DatasetEntry.create(  # type: ignore [attr-defined]
            user_prompt="Edgy, modern pop melody",
            system_prompt=system_prompt,
            expect_measures=2,
            expect_time_signature="4/4",
            expect_bpm=120,
            expect_key="Dm",
            expect_instrument="piano",
        ),
        DatasetEntry.create(  # type: ignore [attr-defined]
            user_prompt="Experimental funk drum pattern with a fill in the last measure",
            system_prompt=system_prompt,
            expect_measures=4,
            expect_time_signature="5/4",
            expect_bpm=160,
            expect_key="G",
            expect_instrument="drum",
        ),
        DatasetEntry.create(  # type: ignore [attr-defined]
            user_prompt="Walking bass for a jazz standard",
            system_prompt=system_prompt,
            expect_measures=2,
            expect_time_signature="4/4",
            expect_bpm=120,
            expect_key="Dm",
            expect_instrument="piano",
        ),
        DatasetEntry.create(  # type: ignore [attr-defined]
            user_prompt="Moody chords for a slow waltz",
            system_prompt=system_prompt,
            expect_measures=2,
            expect_time_signature="3/4",
            expect_bpm=90,
            expect_key="Am",
            expect_instrument="piano",
        ),
    ]


class EvalResult(TypedDict):
    """A standard return type for scorers."""

    ok: bool
    error: str | None


@weave.op
def evaluate_midi_events(
    expect_measures: int,
    expect_time_signature: TimeSignature,
    output: Optional["midi_agents.GenerateMidiResponse"],
) -> EvalResult:
    """
    Check that MIDI events are well-formed.
    """
    # Hack: weave magically serializes pydantic models to dicts when running evals so we have to marshal back to the model type
    if isinstance(output, dict):
        output = midi_agents.GenerateMidiResponse.model_validate(output)

    beats_per_measure = TIME_SIGNATURE_BEATS_PER_MEASURE[expect_time_signature]

    # Group events by note (event name) and count note-on vs note-off
    note_counts: dict[str, int] = defaultdict(lambda: 0)

    try:
        if output is None:
            raise AssertionError("Invalid MIDI")

        for index, event in enumerate(output.to_midi_events()):
            # Validate measures
            if event.measure > expect_measures:
                raise AssertionError(f"Midi event at index {index} is outside the loop's length: {expect_measures}")

            # Validate time signature
            if event.beat > beats_per_measure:
                raise AssertionError(
                    f"Midi event at index {index} is outside the time signature: {expect_time_signature}"
                )

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
        log.exception(f"Generated MIDI failed validation: {e}")
        return EvalResult(ok=False, error=str(e))
    except Exception as e:
        log.exception(f"Unexpected system error: {e}")
        return EvalResult(ok=False, error="Unexpected system error")

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

    ALL_MODELS = MODEL_PROVIDER_MAP.keys()

    parser = argparse.ArgumentParser(description="Compare midi generation models")
    parser.add_argument("--trials", "-t", type=int, default=3)
    parser.add_argument("--models", "-m", nargs="+", choices=ALL_MODELS, default=ALL_MODELS)
    parser.add_argument("--system-prompt", "-s", default=midi_agents.SYSTEM_PROMPT)
    args = parser.parse_args()

    # Get or create the published evaluation
    try:
        eval_name = "generate_midi_eval"
        eval: weave.Evaluation = weave.ref(eval_name).get()
    except ValueError:
        eval = weave.Evaluation(
            name="generate_midi",
            dataset=get_dataset(args.system_prompt),  # type: ignore [arg-type]
            scorers=[evaluate_midi_events],
            trials=args.trials,
            evaluation_name=f"{random.choice(ADJECTIVES).lower()}-{random.choice(NOUNS).lower()}",
        )
        weave.publish(eval, eval_name)

    async def evaluate() -> None:
        tasks = []
        for model_name in args.models:
            model = midi_agents.get_model(model_name, args.system_prompt)
            tasks.append(eval.evaluate(model, __weave={"display_name": model_name}))
        await asyncio.gather(*tasks)

    asyncio.run(evaluate())
