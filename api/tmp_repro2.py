import asyncio
import os

import weave
from dotenv import load_dotenv
from weave import Scorer

load_dotenv()
weave.init(os.environ["PROJECT_ID"])


@weave.op
def generate_styled_text(prompt: str, style: str, temperature: float) -> str:
    """Generate text in a specific style."""
    return "Generated text in requested style..."


class StyleScorer(Scorer):
    @weave.op
    def score(self, output: str, prompt: str, style: str) -> dict:
        """
        Evaluate if the output matches the requested style.

        Args:
            output: The generated text (automatically provided)
            prompt: Original prompt (matched from function input)
            style: Requested style (matched from function input)
        """
        return {
            "style_match": 0.9,  # How well it matches requested style
            "prompt_relevance": 0.8,  # How relevant to the prompt
        }


# Example usage
@weave.op
async def generate_and_score():
    # Generate text with style
    result, call = generate_styled_text.call(prompt="Write a story", style="noir", temperature=0.7)

    # Score the result
    score = await call.apply_scorer(StyleScorer())
    print(f"Style match score: {score.result['style_match']}")


# Now you can apply scorers
asyncio.run(generate_and_score())
