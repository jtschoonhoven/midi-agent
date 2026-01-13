"""Weights & Biases evaluation scaffolding for MIDI generation pipeline."""

from __future__ import annotations

import os
from uuid import UUID, uuid4

import pydantic
import wandb
import weave

from api.midi.midi_routes import GenerateRequest, Key, ModelName, TimeSignature
from api.midi.midi_utils import MidiEvent, PlanResponse, run_generation_pipeline


# ==========================================================================
# Evaluation dataset schema
# ==========================================================================


class EvalExample(pydantic.BaseModel):
    """Single evaluation example."""

    prompt: str = pydantic.Field(description="User's musical generation request")
    key: Key | None = pydantic.Field(None, description="Optional key constraint")
    bpm: int | None = pydantic.Field(None, description="Optional BPM constraint")
    time_signature: TimeSignature | None = pydantic.Field(None, description="Optional time signature constraint")
    measures: int | None = pydantic.Field(None, description="Optional measures constraint")
    expected_style: str | None = pydantic.Field(None, description="Expected musical style (for reference)")
    expected_key: Key | None = pydantic.Field(None, description="Expected key (for reference)")


class EvalResult(pydantic.BaseModel):
    """Result from evaluating a single example."""

    prompt: str
    plan: PlanResponse
    midi_events: list[MidiEvent]
    num_events: int
    success: bool
    error: str | None = None


# ==========================================================================
# Dataset loading
# ==========================================================================


def load_eval_dataset() -> list[EvalExample]:
    """Load or create evaluation dataset.

    TODO: Implement dataset loading from:
    - JSON file
    - CSV file
    - W&B Artifacts
    - Database
    """
    # Example evaluation dataset
    return [
        EvalExample(
            prompt="Create a happy upbeat piano melody",
            expected_style="upbeat",
            expected_key="C",
        ),
        EvalExample(
            prompt="Generate a melancholic ballad in D minor",
            key="D",
            expected_style="melancholic",
            expected_key="D",
        ),
        EvalExample(
            prompt="Make a funky bassline with syncopation",
            bpm=110,
            expected_style="funk",
        ),
        EvalExample(
            prompt="Create a 4-measure jazz progression",
            measures=4,
            time_signature="4/4",
            expected_style="jazz",
        ),
    ]


# ==========================================================================
# Evaluation functions
# ==========================================================================


@weave.op()
def evaluate_single_example(
    example: EvalExample,
    plan_model: ModelName,
    generate_model: ModelName,
    user_id: UUID,
    thread_id: UUID,
) -> EvalResult:
    """Evaluate a single example through the generation pipeline.

    Args:
        example: Evaluation example to test
        plan_model: Model to use for planning
        generate_model: Model to use for generation
        user_id: User ID for tracking
        thread_id: Thread ID for tracking

    Returns:
        EvalResult with plan, MIDI events, and success status
    """
    try:
        # Create generation request from example
        request = GenerateRequest(
            user_id=user_id,
            thread_id=thread_id,
            plan_model=plan_model,
            generate_model=generate_model,
            key=example.key,
            bpm=example.bpm,
            time_signature=example.time_signature,
            measures=example.measures,
            prompt=example.prompt,
        )

        # Run generation pipeline
        plan, midi_events = run_generation_pipeline(request)

        return EvalResult(
            prompt=example.prompt,
            plan=plan,
            midi_events=midi_events,
            num_events=len(midi_events),
            success=True,
        )

    except Exception as e:
        return EvalResult(
            prompt=example.prompt,
            plan=PlanResponse(
                key="C",
                bpm=120,
                time_signature="4/4",
                measures=4,
                style="error",
                chord_progression=[],
                reasoning="Failed to generate",
            ),
            midi_events=[],
            num_events=0,
            success=False,
            error=str(e),
        )


def compute_metrics(results: list[EvalResult]) -> dict[str, float]:
    """Compute evaluation metrics from results.

    Args:
        results: List of evaluation results

    Returns:
        Dictionary of metric names to values
    """
    total = len(results)
    if total == 0:
        return {}

    successful = sum(1 for r in results if r.success)
    failed = total - successful

    # Basic success metrics
    success_rate = successful / total
    failure_rate = failed / total

    # MIDI event metrics
    total_events = sum(r.num_events for r in results)
    avg_events = total_events / total if total > 0 else 0
    avg_events_successful = sum(r.num_events for r in results if r.success) / successful if successful > 0 else 0

    # Plan quality metrics (could be expanded)
    avg_bpm = sum(r.plan.bpm for r in results if r.success) / successful if successful > 0 else 0
    avg_measures = sum(r.plan.measures for r in results if r.success) / successful if successful > 0 else 0

    return {
        "success_rate": success_rate,
        "failure_rate": failure_rate,
        "total_examples": total,
        "successful_examples": successful,
        "failed_examples": failed,
        "total_midi_events": total_events,
        "avg_events_per_example": avg_events,
        "avg_events_successful": avg_events_successful,
        "avg_bpm": avg_bpm,
        "avg_measures": avg_measures,
    }


# ==========================================================================
# Main evaluation run
# ==========================================================================


@weave.op()
def run_evaluation(
    plan_model: ModelName = "claude-sonnet-4-5",
    generate_model: ModelName = "claude-sonnet-4-5",
    wandb_project: str = "midi-agent-eval",
    wandb_entity: str | None = None,
) -> dict[str, float]:
    """Run full evaluation pipeline with W&B tracking.

    Args:
        plan_model: Model to use for planning stage
        generate_model: Model to use for generation stage
        wandb_project: W&B project name
        wandb_entity: W&B entity (username or team)

    Returns:
        Dictionary of evaluation metrics
    """
    # Initialize W&B run
    run = wandb.init(
        project=wandb_project,
        entity=wandb_entity,
        config={
            "plan_model": plan_model,
            "generate_model": generate_model,
        },
        job_type="evaluation",
    )

    # Initialize Weave
    weave.init(f"{wandb_entity}/{wandb_project}" if wandb_entity else wandb_project)

    # Load evaluation dataset
    dataset = load_eval_dataset()
    print(f"Loaded {len(dataset)} evaluation examples")

    # Run evaluation on each example
    results: list[EvalResult] = []
    user_id = uuid4()

    for i, example in enumerate(dataset):
        print(f"Evaluating example {i + 1}/{len(dataset)}: {example.prompt[:50]}...")
        thread_id = uuid4()

        result = evaluate_single_example(
            example=example,
            plan_model=plan_model,
            generate_model=generate_model,
            user_id=user_id,
            thread_id=thread_id,
        )

        results.append(result)

        # Log individual result to W&B
        wandb.log(
            {
                f"example_{i}_success": result.success,
                f"example_{i}_num_events": result.num_events,
                f"example_{i}_bpm": result.plan.bpm if result.success else 0,
            }
        )

    # Compute aggregate metrics
    metrics = compute_metrics(results)
    print("\nEvaluation Metrics:")
    for key, value in metrics.items():
        print(f"  {key}: {value:.4f}")

    # Log metrics to W&B
    wandb.log(metrics)

    # Create results table for W&B
    results_table = wandb.Table(
        columns=[
            "prompt",
            "success",
            "num_events",
            "key",
            "bpm",
            "time_signature",
            "measures",
            "style",
            "error",
        ]
    )

    for result in results:
        results_table.add_data(
            result.prompt,
            result.success,
            result.num_events,
            result.plan.key if result.success else None,
            result.plan.bpm if result.success else None,
            result.plan.time_signature if result.success else None,
            result.plan.measures if result.success else None,
            result.plan.style if result.success else None,
            result.error,
        )

    wandb.log({"results": results_table})

    # Finish W&B run
    if run:
        run.finish()

    return metrics


def main() -> None:
    """Main entry point for evaluation script."""
    # Check for required API keys
    if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        raise ValueError("Either ANTHROPIC_API_KEY or OPENAI_API_KEY must be set")

    if not os.getenv("WANDB_API_KEY"):
        print("Warning: WANDB_API_KEY not set. You may need to login with 'wandb login'")

    # Run evaluation with default configuration
    # TODO: Add CLI argument parsing for model selection and W&B config
    metrics = run_evaluation(
        plan_model="claude-sonnet-4-5",
        generate_model="claude-sonnet-4-5",
        wandb_project="midi-agent-eval",
        wandb_entity=None,  # Set to your W&B username or team
    )

    print(f"\nEvaluation complete. Final success rate: {metrics.get('success_rate', 0):.2%}")


if __name__ == "__main__":
    main()
