"""OTel GenAI tracing configured to export to Weave's /agents/otel/v1/traces ingest endpoint.

Resource attributes `wb_entity` and `wb_project` (plus a `project_id` header) route
spans to the correct W&B project. Auth via the `wandb-api-key` header.

Also exposes context managers for the GenAI operations that aren't (or aren't fully)
covered by the OpenAI/Anthropic auto-instrumentations: `invoke_agent`, `execute_tool`,
and `chat` for the untraced OpenAI Responses API and Anthropic structured-output calls.
"""

import json
import logging
import os
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Any

from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor
from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, Span as SdkSpan, SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span, SpanKind
from weave.trace.env import weave_trace_server_url

log = logging.getLogger(__name__)

WEAVE_INGEST_PATH = "/agents/otel/v1/traces"

CONVERSATION_ID_ATTR = "gen_ai.conversation.id"


class ConversationIdPropagator(SpanProcessor):
    """Copy `gen_ai.conversation.id` from the active parent span onto each child at start.

    Auto-instrumentation spans (OpenAI, Anthropic) don't know about our conversation ID,
    so we propagate it down from the surrounding `invoke_agent` / `chat` span we set
    manually. Reading attributes via the readable-span view works because attributes
    set in `start_as_current_span(attributes=...)` are present by the time `on_start`
    fires for child spans.
    """

    def on_start(self, span: SdkSpan, parent_context: otel_context.Context | None = None) -> None:
        parent = trace.get_current_span(parent_context)
        if not parent or not parent.get_span_context().is_valid:
            return
        # Only SDK spans expose attributes; auto-instrumented parents are SDK spans here.
        parent_attrs = getattr(parent, "attributes", None)
        if not parent_attrs:
            return
        conv_id = parent_attrs.get(CONVERSATION_ID_ATTR)
        if conv_id and span.attributes.get(CONVERSATION_ID_ATTR) is None:
            span.set_attribute(CONVERSATION_ID_ATTR, conv_id)

    def on_end(self, span: ReadableSpan) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


def init_otel() -> None:
    """Set up OTel tracing with GenAI-compliant instrumentations for OpenAI and Anthropic.

    Env:
      PROJECT_ID: "entity/project" — maps to wb_entity / wb_project resource attributes.
      WANDB_API_KEY: auth for the Weave ingest endpoint.

    The trace server base URL is resolved by weave itself via `weave_trace_server_url()`
    (honors WF_TRACE_SERVER_URL, WANDB_BASE_URL, or the SaaS default); we append
    `/agents/otel/v1/traces` to it.
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
            # Resource attribute names expected by the /agents/otel/v1/traces route on the
            # W&B trace server. (The standard /otel/v1/traces route uses wb_entity/wb_project
            # instead — different name conventions per route.)
            "wandb.entity": entity_name,
            "wandb.project": project_name,
        }
    )

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, headers={"wandb-api-key": api_key})
    # Register the propagator BEFORE the exporter so attributes are set before export.
    provider.add_span_processor(ConversationIdPropagator())
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    OpenAIInstrumentor().instrument()
    AnthropicInstrumentor().instrument()

    log.info(f"OTel GenAI tracing → {endpoint} (entity={entity_name}, project={project_name})")


def _tracer() -> trace.Tracer:
    """Fetch the current tracer. Called lazily so the provider set by init_otel wins."""
    return trace.get_tracer("api.midi")


@contextmanager
def invoke_agent_span(
    *,
    agent_name: str,
    provider: str,
    model: str,
    conversation_id: str | None = None,
    input_messages: Sequence[Mapping[str, Any]] | None = None,
    system_instructions: str | None = None,
) -> Iterator[Span]:
    """GenAI `invoke_agent` span — wraps one full agent run.

    `input_messages` is the chat history fed to the agent (list of {"role", "content"} dicts).
    `system_instructions` is the system prompt. Both are serialized per the GenAI semconv so
    the root span carries the full turn context, not just the child LLM spans.
    """
    attrs: dict[str, Any] = {
        "gen_ai.operation.name": "invoke_agent",
        "gen_ai.agent.name": agent_name,
        "gen_ai.provider.name": provider,
        "gen_ai.request.model": model,
    }
    if conversation_id:
        attrs["gen_ai.conversation.id"] = conversation_id
    if system_instructions:
        attrs["gen_ai.system_instructions"] = system_instructions
    if input_messages is not None:
        attrs["gen_ai.input.messages"] = _serialize_messages(input_messages)
    with _tracer().start_as_current_span(
        f"invoke_agent {agent_name}",
        kind=SpanKind.CLIENT,
        attributes=attrs,
    ) as span:
        yield span


@contextmanager
def execute_tool_span(
    *, tool_name: str, call_id: str | None = None, conversation_id: str | None = None
) -> Iterator[Span]:
    """GenAI `execute_tool` span — wraps one tool invocation."""
    attrs: dict[str, Any] = {
        "gen_ai.operation.name": "execute_tool",
        "gen_ai.tool.name": tool_name,
    }
    if call_id:
        attrs["gen_ai.tool.call.id"] = call_id
    if conversation_id:
        attrs["gen_ai.conversation.id"] = conversation_id
    with _tracer().start_as_current_span(
        f"execute_tool {tool_name}",
        kind=SpanKind.INTERNAL,
        attributes=attrs,
    ) as span:
        yield span


@contextmanager
def chat_span(*, provider: str, model: str, conversation_id: str | None = None) -> Iterator[Span]:
    """GenAI `chat` span — used for LLM calls the auto-instrumentations don't cover."""
    attrs: dict[str, Any] = {
        "gen_ai.operation.name": "chat",
        "gen_ai.provider.name": provider,
        "gen_ai.request.model": model,
    }
    if conversation_id:
        attrs["gen_ai.conversation.id"] = conversation_id
    with _tracer().start_as_current_span(
        f"chat {model}",
        kind=SpanKind.CLIENT,
        attributes=attrs,
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


def record_agent_output(span: Span, content: Any) -> None:
    """Record the agent's final output on an invoke_agent span as a single assistant message.

    `content` may be a string or anything JSON-serializable (pydantic models are dumped via
    model_dump if available, otherwise str()).
    """
    if hasattr(content, "model_dump"):
        body = json.dumps(content.model_dump(), default=str)
    elif isinstance(content, str):
        body = content
    else:
        try:
            body = json.dumps(content, default=str)
        except (TypeError, ValueError):
            body = str(content)
    span.set_attribute(
        "gen_ai.output.messages",
        json.dumps([{"role": "assistant", "parts": [{"type": "text", "content": body}]}]),
    )


def _serialize_messages(messages: Sequence[Mapping[str, Any]]) -> str:
    """Convert a chat history (list of {"role", "content"}) to GenAI semconv JSON.

    Skips entries with role="system" — the system prompt is carried on `gen_ai.system_instructions`.
    """
    return json.dumps(
        [
            {"role": m["role"], "parts": [{"type": "text", "content": str(m.get("content", ""))}]}
            for m in messages
            if m.get("role") != "system"
        ]
    )
