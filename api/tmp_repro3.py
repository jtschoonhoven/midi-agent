import asyncio
import os

import weave
from dotenv import load_dotenv

load_dotenv()
weave.init(os.environ["PROJECT_ID"])

QUESTION = "What is the capital of France?"
ANSWER = "Paris"
DATASET = weave.Dataset(
    rows=[
        {"question": QUESTION, "answer": ANSWER},
    ]
)


@weave.op()
def model_inner(question: str) -> str:
    return "Paris"


class Model(weave.Model):
    @weave.op()
    async def predict(self, question: str) -> str:
        result, call = model_inner.call(question)
        await call.apply_scorer(scorer, additional_scorer_kwargs={"answer": ANSWER})
        return result


@weave.op()
def scorer(question: str, answer: str, output) -> dict:
    print(f"{type(question)} {type(answer)} {type(output)}")
    print(len(question))
    return {"correct": question == answer}


if __name__ == "__main__":
    model = Model(name="test")
    evaluate = weave.Evaluation(dataset=DATASET, scorers=[scorer])
    asyncio.run(evaluate.evaluate(model))
