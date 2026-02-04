"""LangChain integration for evaldeck.

Provides automatic instrumentation and trace capture for LangChain/LangGraph agents.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from evaldeck.trace import Trace


class LangChainIntegration:
    """LangChain/LangGraph integration.

    Automatically sets up OpenTelemetry tracing and provides a wrapper
    that invokes the agent and returns a Trace.
    """

    def __init__(self) -> None:
        self._processor: Any = None
        self._agent: Any = None
        self._initialized = False

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

        # Instrument LangChain
        LangChainInstrumentor().instrument()

        # Create the agent
        self._agent = agent_factory()
        self._initialized = True

    def run(self, input: str) -> Trace:
        """Run the agent and return a trace.

        Args:
            input: The input string to send to the agent.

        Returns:
            Trace captured from the agent execution.
        """
        if not self._initialized:
            raise RuntimeError("Integration not initialized. Call setup() first.")

        # Reset processor for fresh trace
        self._processor.reset()

        # Invoke the agent - auto-detect format
        self._invoke_agent(input)

        # Get and return trace
        trace = self._processor.get_latest_trace()
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
