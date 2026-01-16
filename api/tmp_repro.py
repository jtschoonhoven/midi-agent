import asyncio
import os

import weave
from dotenv import load_dotenv

load_dotenv()
weave.init(os.environ["PROJECT_ID"])

QUESTION = "What is the capital of France?"
ANSWER = "Paris"
DATASET = [{"question": QUESTION, "answer": ANSWER}]


@weave.op()
def model_fn(question: str, answer: str) -> str:
    return "I don't know."


@weave.op()
async def model_fn_with_scorer(question: str) -> str:
    result, call = model_fn.call(question, ANSWER)
    await call.apply_scorer(scorer)
    return result


@weave.op()
def scorer(question: str, answer: str, output: str) -> dict:
    # ERROR: When this scorer is called as `call.apply_scorer(...)` then `question` is an ObjectRef:
    # ERROR: "TypeError: object of type 'ObjectRef' has no len()"
    question_len = len(question)  # Error!
    return {"correct": output == answer, "question_len": question_len}


if __name__ == "__main__":
    evaluation = weave.Evaluation(dataset=DATASET, scorers=[scorer])

    # OK: Evaluate a model function
    asyncio.run(evaluation.evaluate(model_fn))

    # OK: Call a model function that applies a scorer
    asyncio.run(model_fn_with_scorer(QUESTION))

    # NOT OK: Evaluate a model function that applies a scorer
    asyncio.run(evaluation.evaluate(model_fn_with_scorer))
