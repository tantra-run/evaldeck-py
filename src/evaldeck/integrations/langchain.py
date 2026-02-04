"""LangChain integration for evaldeck.

Provides automatic instrumentation and trace capture for LangChain/LangGraph agents.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from evaldeck.trace import Trace


class LangChainIntegration:
    """LangChain/LangGraph integration.

    Automatically sets up OpenTelemetry tracing and provides a wrapper
    that invokes the agent and returns a Trace.

    Thread-safe: uses thread-local storage to track traces per thread,
    allowing parallel test execution.
    """

    def __init__(self) -> None:
        self._processor: Any = None
        self._agent: Any = None
        self._initialized = False
        self._lock = threading.Lock()
        self._local = threading.local()

    def setup(self, agent_factory: Callable[[], Any]) -> None:
        """Set up instrumentation and create the agent.

        Args:
            agent_factory: Function that returns the agent instance.
        """
        if self._initialized:
            return

        # Import here to make langchain an optional dependency
        try:
            from openinference.instrumentation.langchain import LangChainInstrumentor
        except ImportError as e:
            raise ImportError(
                "LangChain integration requires openinference-instrumentation-langchain. "
                "Install with: pip install evaldeck[langchain]"
            ) from e

        from evaldeck.integrations import setup_otel_tracing

        # Set up OTel tracing
        self._processor = setup_otel_tracing()

        # Instrument LangChain (only once)
        LangChainInstrumentor().instrument()

        # Create the agent
        self._agent = agent_factory()
        self._initialized = True

    def run(self, input: str) -> Trace:
        """Run the agent and return a trace.

        Note: Agent invocations are serialized (one at a time) to ensure
        clean trace capture. Evaluations (grading) can still run in parallel.

        Args:
            input: The input string to send to the agent.

        Returns:
            Trace captured from the agent execution.
        """
        if not self._initialized:
            raise RuntimeError("Integration not initialized. Call setup() first.")

        # Serialize agent invocations to ensure clean trace capture
        # (OTel trace IDs can get mixed when agents run truly in parallel)
        with self._lock:
            # Record traces before
            traces_before = set(self._processor._traces.keys())

            # Invoke the agent
            self._invoke_agent(input)

            # Find the new trace created by this invocation
            traces_after = set(self._processor._traces.keys())
            new_trace_ids = traces_after - traces_before

            if not new_trace_ids:
                raise RuntimeError("No trace captured from agent execution")

            # Get the trace
            trace_id = new_trace_ids.pop()
            trace: Trace | None = self._processor.get_trace(trace_id)

            if trace is None:
                raise RuntimeError("No trace captured from agent execution")

            return trace

    def _invoke_agent(self, input: str) -> Any:
        """Invoke the agent with the appropriate format.

        Auto-detects LangGraph vs legacy LangChain format.
        """
        # LangGraph style (current)
        if hasattr(self._agent, "invoke"):
            # Try LangGraph message format first
            try:
                return self._agent.invoke({"messages": [("human", input)]})
            except (TypeError, KeyError):
                # Fall back to simple input
                try:
                    return self._agent.invoke({"input": input})
                except (TypeError, KeyError):
                    return self._agent.invoke(input)

        # Legacy LangChain style
        if hasattr(self._agent, "run"):
            return self._agent.run(input)

        # Callable
        if callable(self._agent):
            return self._agent(input)

        raise RuntimeError(
            f"Don't know how to invoke agent of type {type(self._agent)}. "
            "Agent must have invoke(), run(), or be callable."
        )


def create_langchain_runner(agent_factory: Callable[[], Any]) -> Callable[[str], Trace]:
    """Create a runner function for LangChain agents.

    This is the main entry point used by evaldeck's EvaluationRunner.

    Args:
        agent_factory: Function that returns the agent instance.

    Returns:
        A function that takes input and returns a Trace.
    """
    integration = LangChainIntegration()
    integration.setup(agent_factory)
    return integration.run
