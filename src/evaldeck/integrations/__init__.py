"""Framework integrations for Evaldeck.

This module provides the OpenTelemetry/OpenInference adapter for capturing traces
from any instrumented AI framework (LangChain, CrewAI, LiteLLM, OpenAI, Anthropic, etc.)

Basic usage (manual setup):
    from evaldeck.integrations import EvaldeckSpanProcessor, setup_otel_tracing
    from openinference.instrumentation.langchain import LangChainInstrumentor

    processor = setup_otel_tracing()
    LangChainInstrumentor().instrument()

    # Run your agent...

    trace = processor.get_latest_trace()
    result = evaluator.evaluate(trace, test_case)

With framework integration (automatic setup via evaldeck.yaml):
    # evaldeck.yaml
    agent:
      module: my_agent
      function: create_agent
      framework: langchain

    # my_agent.py
    def create_agent():
        return create_react_agent(llm, tools)

    # Run: evaldeck run
"""

from evaldeck.integrations.opentelemetry import (
    EvaldeckSpanProcessor,
)
from evaldeck.integrations.opentelemetry import (
    setup_tracing as setup_otel_tracing,
)

__all__ = [
    "EvaldeckSpanProcessor",
    "setup_otel_tracing",
]
