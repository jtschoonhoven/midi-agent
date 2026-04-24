"""OTel GenAI tracing configured to export to Weave's /otel/v1/genai/traces ingest endpoint.

Resource attributes `wandb.entity_name` and `wandb.project_id` route spans to the
correct W&B project. Auth via the `wandb-api-key` header.

Also exposes context managers for the GenAI operations that aren't (or aren't fully)
covered by the OpenAI/Anthropic auto-instrumentations: `invoke_agent`, `execute_tool`,
and `chat` for the untraced OpenAI Responses API and Anthropic structured-output calls.
"""

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor
from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span, SpanKind
from weave.trace.env import weave_trace_server_url

log = logging.getLogger(__name__)

WEAVE_INGEST_PATH = "/otel/v1/genai/traces"


def init_otel() -> None:
    """Set up OTel tracing with GenAI-compliant instrumentations for OpenAI and Anthropic.

    Env:
      PROJECT_ID: "entity/project" — maps to wb_entity / wb_project resource attributes.
      WANDB_API_KEY: auth for the Weave ingest endpoint.

    The trace server base URL is resolved by weave itself via `weave_trace_server_url()`
    (honors WF_TRACE_SERVER_URL, WANDB_BASE_URL, or the SaaS default); we append
    `/otel/v1/genai/traces` to it.
    """
    project_id = os.environ["PROJECT_ID"]
    api_key = os.environ["WANDB_API_KEY"]
    endpoint = weave_trace_server_url().rstrip("/") + WEAVE_INGEST_PATH

    if "/" not in project_id:
        raise ValueError(f"PROJECT_ID must be 'entity/project', got {project_id!r}")
    entity_name, project_name = project_id.split("/", 1)

    # Required by the GenAI instrumentations to include prompt/response content on spans.
    os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "true")

    resource = Resource.create(
        {
            "service.name": "midi-agent",
            # Resource attributes the Weave trace server uses to route spans to a project.
            "wb_entity": entity_name,
            "wb_project": project_name,
        }
    )

    provider = TracerProvider(resource=resource)
    # Also send project_id as a header — belt-and-suspenders in case the server prefers
    # it over resource attributes on certain ingest routes.
    exporter = OTLPSpanExporter(
        endpoint=endpoint,
        headers={"wandb-api-key": api_key, "project_id": project_id},
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    OpenAIInstrumentor().instrument()
    AnthropicInstrumentor().instrument()

    log.info(f"OTel GenAI tracing → {endpoint} (entity={entity_name}, project={project_name})")


def _tracer() -> trace.Tracer:
    """Fetch the current tracer. Called lazily so the provider set by init_otel wins."""
    return trace.get_tracer("api.midi")


@contextmanager
def invoke_agent_span(*, agent_name: str, provider: str, model: str) -> Iterator[Span]:
    """GenAI `invoke_agent` span — wraps one full agent run."""
    with _tracer().start_as_current_span(
        f"invoke_agent {agent_name}",
        kind=SpanKind.CLIENT,
        attributes={
            "gen_ai.operation.name": "invoke_agent",
            "gen_ai.agent.name": agent_name,
            "gen_ai.provider.name": provider,
            "gen_ai.request.model": model,
        },
    ) as span:
        yield span


@contextmanager
def execute_tool_span(*, tool_name: str, call_id: str | None = None) -> Iterator[Span]:
    """GenAI `execute_tool` span — wraps one tool invocation."""
    attrs: dict[str, Any] = {
        "gen_ai.operation.name": "execute_tool",
        "gen_ai.tool.name": tool_name,
    }
    if call_id:
        attrs["gen_ai.tool.call.id"] = call_id
    with _tracer().start_as_current_span(
        f"execute_tool {tool_name}",
        kind=SpanKind.INTERNAL,
        attributes=attrs,
    ) as span:
        yield span


@contextmanager
def chat_span(*, provider: str, model: str) -> Iterator[Span]:
    """GenAI `chat` span — used for LLM calls the auto-instrumentations don't cover."""
    with _tracer().start_as_current_span(
        f"chat {model}",
        kind=SpanKind.CLIENT,
        attributes={
            "gen_ai.operation.name": "chat",
            "gen_ai.provider.name": provider,
            "gen_ai.request.model": model,
        },
    ) as span:
        yield span


def record_usage(
    span: Span, *, input_tokens: int | None, output_tokens: int | None, response_model: str | None = None
) -> None:
    """Set GenAI response/usage attributes on a span from an LLM response."""
    if input_tokens is not None:
        span.set_attribute("gen_ai.usage.input_tokens", input_tokens)
    if output_tokens is not None:
        span.set_attribute("gen_ai.usage.output_tokens", output_tokens)
    if response_model is not None:
        span.set_attribute("gen_ai.response.model", response_model)
