"""OpenTelemetry/OpenInference integration for Evaldeck.

This module provides an OpenTelemetry SpanProcessor that captures traces from
any OpenInference-instrumented framework (LangChain, CrewAI, LiteLLM, OpenAI SDK,
Anthropic SDK, etc.) and converts them to Evaldeck's Trace format.

Installation:
    pip install opentelemetry-sdk openinference-semantic-conventions

    # Then install instrumentors for your framework(s):
    pip install openinference-instrumentation-langchain
    pip install openinference-instrumentation-crewai
    pip install openinference-instrumentation-litellm
    pip install openinference-instrumentation-openai

Usage:
    from evaldeck.integrations import EvaldeckSpanProcessor, setup_otel_tracing
    from openinference.instrumentation.langchain import LangChainInstrumentor

    # Setup tracing
    processor = setup_otel_tracing()
    LangChainInstrumentor().instrument()

    # Run your agent
    result = agent.invoke({"input": "Book a flight to NYC"})

    # Get the evaldeck trace and evaluate
    trace = processor.get_latest_trace()
    result = evaluator.evaluate(trace, test_case)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from evaldeck.trace import Step, StepStatus, StepType, TokenUsage, Trace, TraceStatus

# OpenTelemetry imports
try:
    from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor
    from opentelemetry.trace import StatusCode

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

    if TYPE_CHECKING:
        from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor
        from opentelemetry.trace import StatusCode
    else:
        SpanProcessor = object
        ReadableSpan = object


# OpenInference span kinds
SPAN_KIND_LLM = "LLM"
SPAN_KIND_TOOL = "TOOL"
SPAN_KIND_CHAIN = "CHAIN"
SPAN_KIND_EMBEDDING = "EMBEDDING"
SPAN_KIND_RETRIEVER = "RETRIEVER"
SPAN_KIND_RERANKER = "RERANKER"
SPAN_KIND_GUARDRAIL = "GUARDRAIL"
SPAN_KIND_AGENT = "AGENT"


class EvaldeckSpanProcessor(SpanProcessor):  # type: ignore[misc]
    """OpenTelemetry SpanProcessor that builds Evaldeck Traces from OpenInference spans.

    This processor intercepts OpenTelemetry spans as they complete and converts them
    to Evaldeck's Trace/Step format. It supports all OpenInference span kinds:
    LLM, TOOL, CHAIN, EMBEDDING, RETRIEVER, RERANKER, GUARDRAIL, AGENT.

    Example:
        from evaldeck.integrations import EvaldeckSpanProcessor
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider

        processor = EvaldeckSpanProcessor()
        provider = TracerProvider()
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        # After running instrumented code:
        evaldeck_trace = processor.get_latest_trace()
    """

    def __init__(self) -> None:
        if not OTEL_AVAILABLE:
            raise ImportError(
                "OpenTelemetry is not installed. Install with: "
                "pip install opentelemetry-sdk openinference-semantic-conventions"
            )

        self._traces: dict[str, Trace] = {}
        self._trace_order: list[str] = []  # Track order for get_latest_trace

    def on_start(self, span: ReadableSpan, parent_context: Any = None) -> None:
        """Called when a span starts. We don't need to do anything here."""
        pass

    def on_end(self, span: ReadableSpan) -> None:
        """Called when a span ends. Convert to Evaldeck format."""
        attrs = dict(span.attributes or {})
        span_kind = str(attrs.get("openinference.span.kind", "")).upper()

        # Skip spans without OpenInference kind
        if not span_kind:
            return

        trace_id = format(span.context.trace_id, "032x")

        # Ensure trace exists
        if trace_id not in self._traces:
            self._traces[trace_id] = Trace(
                id=trace_id,
                input="",
                framework="openinference",
            )
            self._trace_order.append(trace_id)

        trace = self._traces[trace_id]

        # CHAIN/AGENT spans with no parent become the root trace
        if span_kind in (SPAN_KIND_CHAIN, SPAN_KIND_AGENT) and span.parent is None:
            self._update_trace_from_root_span(trace, span, attrs)
            return

        # Convert other spans to Steps
        step = self._span_to_step(span, span_kind, attrs)
        if step:
            trace.add_step(step)

    def _update_trace_from_root_span(
        self, trace: Trace, span: ReadableSpan, attrs: dict[str, Any]
    ) -> None:
        """Update trace metadata from the root CHAIN/AGENT span."""
        trace.input = str(attrs.get("input.value", trace.input or ""))
        trace.output = attrs.get("output.value")
        trace.status = self._map_trace_status(span)
        trace.started_at = self._ns_to_datetime(span.start_time)
        trace.completed_at = self._ns_to_datetime(span.end_time)
        trace.duration_ms = (span.end_time - span.start_time) / 1_000_000

        # Extract agent/framework info
        if "llm.system" in attrs:
            trace.framework = str(attrs["llm.system"])

        trace.metadata["otel_trace_id"] = format(span.context.trace_id, "032x")
        trace.metadata["otel_root_span_id"] = format(span.context.span_id, "016x")

    def _span_to_step(self, span: ReadableSpan, kind: str, attrs: dict[str, Any]) -> Step | None:
        """Convert an OpenTelemetry span to an Evaldeck Step."""

        if kind == SPAN_KIND_LLM:
            return self._convert_llm_span(span, attrs)

        elif kind == SPAN_KIND_TOOL:
            return self._convert_tool_span(span, attrs)

        elif kind in (SPAN_KIND_EMBEDDING, SPAN_KIND_RETRIEVER, SPAN_KIND_RERANKER):
            return self._convert_retrieval_span(span, kind, attrs)

        elif kind == SPAN_KIND_GUARDRAIL:
            return self._convert_guardrail_span(span, attrs)

        elif kind in (SPAN_KIND_CHAIN, SPAN_KIND_AGENT):
            # Nested chains/agents become reasoning steps
            return self._convert_chain_span(span, attrs)

        return None

    def _convert_llm_span(self, span: ReadableSpan, attrs: dict[str, Any]) -> Step:
        """Convert an LLM span to a Step."""
        return Step(
            type=StepType.LLM_CALL,
            model=attrs.get("llm.model_name") or attrs.get("gen_ai.request.model"),
            input=self._extract_messages(attrs, "input"),
            output=self._extract_messages(attrs, "output"),
            tokens=TokenUsage(
                prompt_tokens=int(attrs.get("llm.token_count.prompt", 0)),
                completion_tokens=int(attrs.get("llm.token_count.completion", 0)),
                total_tokens=int(attrs.get("llm.token_count.total", 0)),
            ),
            status=self._map_step_status(span),
            duration_ms=self._calc_duration_ms(span),
            error=self._extract_error(span),
            metadata={
                "otel_span_id": format(span.context.span_id, "016x"),
                "llm_provider": attrs.get("llm.provider") or attrs.get("llm.system"),
            },
        )

    def _convert_tool_span(self, span: ReadableSpan, attrs: dict[str, Any]) -> Step:
        """Convert a TOOL span to a Step."""
        tool_name = attrs.get("tool.name") or attrs.get("tool_call.function.name") or "unknown_tool"

        tool_args = self._parse_json(
            attrs.get("tool.parameters")
            or attrs.get("tool_call.function.arguments")
            or attrs.get("input.value")
        )

        return Step(
            type=StepType.TOOL_CALL,
            tool_name=str(tool_name),
            tool_args=tool_args if isinstance(tool_args, dict) else {"input": tool_args},
            tool_result=attrs.get("output.value"),
            status=self._map_step_status(span),
            duration_ms=self._calc_duration_ms(span),
            error=self._extract_error(span),
            metadata={
                "otel_span_id": format(span.context.span_id, "016x"),
                "tool_id": attrs.get("tool.id") or attrs.get("tool_call.id"),
            },
        )

    def _convert_retrieval_span(self, span: ReadableSpan, kind: str, attrs: dict[str, Any]) -> Step:
        """Convert EMBEDDING/RETRIEVER/RERANKER spans to tool call Steps."""
        return Step(
            type=StepType.TOOL_CALL,
            tool_name=kind.lower(),  # "embedding", "retriever", "reranker"
            tool_args={"input": attrs.get("input.value")},
            tool_result=attrs.get("output.value"),
            status=self._map_step_status(span),
            duration_ms=self._calc_duration_ms(span),
            error=self._extract_error(span),
            metadata={
                "otel_span_id": format(span.context.span_id, "016x"),
                "span_kind": kind,
            },
        )

    def _convert_guardrail_span(self, span: ReadableSpan, attrs: dict[str, Any]) -> Step:
        """Convert GUARDRAIL spans to reasoning Steps."""
        return Step(
            type=StepType.REASONING,
            reasoning_text=f"Guardrail check: {attrs.get('output.value', 'passed')}",
            status=self._map_step_status(span),
            duration_ms=self._calc_duration_ms(span),
            error=self._extract_error(span),
            metadata={
                "otel_span_id": format(span.context.span_id, "016x"),
                "guardrail_input": attrs.get("input.value"),
            },
        )

    def _convert_chain_span(self, span: ReadableSpan, attrs: dict[str, Any]) -> Step:
        """Convert nested CHAIN/AGENT spans to reasoning Steps."""
        return Step(
            type=StepType.REASONING,
            reasoning_text=f"Chain: {span.name} - {attrs.get('output.value', '')}",
            status=self._map_step_status(span),
            duration_ms=self._calc_duration_ms(span),
            metadata={
                "otel_span_id": format(span.context.span_id, "016x"),
                "chain_input": attrs.get("input.value"),
            },
        )

    def _extract_messages(self, attrs: dict[str, Any], direction: str) -> str:
        """Extract message content from OpenInference indexed attributes.

        OpenInference uses indexed prefixes like:
            llm.input_messages.0.message.content
            llm.input_messages.1.message.content
        """
        messages = []
        i = 0
        while True:
            content_key = f"llm.{direction}_messages.{i}.message.content"
            if content_key in attrs:
                content = attrs[content_key]
                role_key = f"llm.{direction}_messages.{i}.message.role"
                role = attrs.get(role_key, "")
                if role:
                    messages.append(f"[{role}]: {content}")
                else:
                    messages.append(str(content))
                i += 1
            else:
                break

        if messages:
            return "\n".join(messages)

        # Fallback to simple input/output value
        return str(attrs.get(f"{direction}.value", ""))

    def _parse_json(self, value: Any) -> Any:
        """Parse JSON string if possible, return as-is otherwise."""
        if value is None:
            return {}
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value

    def _map_trace_status(self, span: ReadableSpan) -> TraceStatus:
        """Map OTel span status to Evaldeck TraceStatus."""
        if span.status.status_code == StatusCode.ERROR:
            return TraceStatus.ERROR
        return TraceStatus.SUCCESS

    def _map_step_status(self, span: ReadableSpan) -> StepStatus:
        """Map OTel span status to Evaldeck StepStatus."""
        if span.status.status_code == StatusCode.ERROR:
            return StepStatus.FAILURE
        return StepStatus.SUCCESS

    def _extract_error(self, span: ReadableSpan) -> str | None:
        """Extract error message from span if present."""
        if span.status.status_code == StatusCode.ERROR:
            return span.status.description  # type: ignore[no-any-return]
        return None

    def _calc_duration_ms(self, span: ReadableSpan) -> float:
        """Calculate span duration in milliseconds."""
        return (span.end_time - span.start_time) / 1_000_000  # type: ignore[no-any-return]

    def _ns_to_datetime(self, ns: int) -> datetime:
        """Convert nanoseconds timestamp to datetime."""
        return datetime.fromtimestamp(ns / 1_000_000_000, tz=timezone.utc)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get_trace(self, trace_id: str) -> Trace | None:
        """Get a trace by its ID.

        Args:
            trace_id: The OpenTelemetry trace ID (32 hex chars)

        Returns:
            The Evaldeck Trace, or None if not found
        """
        return self._traces.get(trace_id)

    def get_latest_trace(self) -> Trace | None:
        """Get the most recently completed trace.

        Returns:
            The most recent Evaldeck Trace, or None if no traces captured
        """
        if self._trace_order:
            return self._traces.get(self._trace_order[-1])
        return None

    def get_all_traces(self) -> list[Trace]:
        """Get all captured traces in order.

        Returns:
            List of all Evaldeck Traces
        """
        return [self._traces[tid] for tid in self._trace_order if tid in self._traces]

    def reset(self) -> None:
        """Clear all captured traces."""
        self._traces.clear()
        self._trace_order.clear()

    def shutdown(self) -> None:
        """Shutdown the processor (required by SpanProcessor interface)."""
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush (required by SpanProcessor interface)."""
        return True


def setup_tracing(processor: EvaldeckSpanProcessor | None = None) -> EvaldeckSpanProcessor:
    """Setup OpenTelemetry tracing with the Evaldeck processor.

    This is a convenience function that sets up the tracer provider
    with the Evaldeck processor.

    Args:
        processor: Optional existing processor. If None, creates a new one.

    Returns:
        The EvaldeckSpanProcessor (for later trace retrieval)

    Example:
        from evaldeck.integrations import setup_otel_tracing
        from openinference.instrumentation.langchain import LangChainInstrumentor

        processor = setup_otel_tracing()
        LangChainInstrumentor().instrument()

        # Run agent...

        trace = processor.get_latest_trace()
    """
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider

    if processor is None:
        processor = EvaldeckSpanProcessor()

    provider = TracerProvider()
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    return processor
