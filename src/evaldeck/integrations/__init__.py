"""Framework integrations for Evaldeck.

This module provides the OpenTelemetry/OpenInference adapter for capturing traces
from any instrumented AI framework (LangChain, CrewAI, LiteLLM, OpenAI, Anthropic, etc.)

Usage:
    from evaldeck.integrations import EvaldeckSpanProcessor, setup_otel_tracing
    from openinference.instrumentation.langchain import LangChainInstrumentor

    processor = setup_otel_tracing()
    LangChainInstrumentor().instrument()

    # Run your agent...

    trace = processor.get_latest_trace()
    result = evaluator.evaluate(trace, test_case)
"""

from evaldeck.integrations.opentelemetry import (
    EvaldeckSpanProcessor,
    setup_tracing as setup_otel_tracing,
)

__all__ = [
    "EvaldeckSpanProcessor",
    "setup_otel_tracing",
]
