# Adding Integrations

Add support for new agent frameworks via OpenTelemetry or custom adapters.

## Recommended: OpenTelemetry/OpenInference

The preferred way to add framework support is through [OpenInference](https://github.com/Arize-ai/openinference) instrumentors. This approach:

- Works with Evaldeck's built-in `EvaldeckSpanProcessor`
- Requires no changes to Evaldeck itself
- Provides automatic trace capture

### If an OpenInference instrumentor exists

Many frameworks already have instrumentors:

- LangChain: `openinference-instrumentation-langchain`
- CrewAI: `openinference-instrumentation-crewai`
- OpenAI SDK: `openinference-instrumentation-openai`
- LiteLLM: `openinference-instrumentation-litellm`
- And many more...

Users simply install and instrument:

```python
from evaldeck.integrations import setup_otel_tracing
from openinference.instrumentation.crewai import CrewAIInstrumentor

processor = setup_otel_tracing()
CrewAIInstrumentor().instrument()

# Run agent - traces captured automatically
```

### If no instrumentor exists

Consider contributing one to the [OpenInference project](https://github.com/Arize-ai/openinference). This benefits the entire ecosystem.

## Alternative: Custom Adapter

For frameworks that can't use OpenTelemetry, create a custom adapter.

### Step 1: Understand the Framework

Study how the framework exposes execution events:

- Callbacks/hooks
- Event streams
- Logging
- Middleware

### Step 2: Create the Adapter

```python
# my_framework_adapter.py
from evaldeck import Trace, Step, TokenUsage


class MyFrameworkTracer:
    """Capture execution traces from MyFramework agents."""

    def __init__(self):
        self.trace: Trace | None = None
        self._current_step_start: float | None = None

    def on_agent_start(self, input: str, **kwargs):
        """Called when agent execution begins."""
        self.trace = Trace(
            input=input,
            framework="my_framework",
            metadata=kwargs
        )

    def on_llm_start(self, model: str, prompt: str, **kwargs):
        """Called before LLM call."""
        import time
        self._current_step_start = time.time()

    def on_llm_end(self, model: str, prompt: str, response: str, **kwargs):
        """Called after LLM call completes."""
        import time

        duration_ms = None
        if self._current_step_start:
            duration_ms = (time.time() - self._current_step_start) * 1000

        tokens = None
        if "usage" in kwargs:
            usage = kwargs["usage"]
            tokens = TokenUsage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )

        self.trace.add_step(Step.llm_call(
            model=model,
            input=prompt,
            output=response,
            tokens=tokens,
            duration_ms=duration_ms,
        ))

    def on_tool_start(self, tool_name: str, tool_args: dict, **kwargs):
        """Called before tool execution."""
        import time
        self._current_step_start = time.time()

    def on_tool_end(self, tool_name: str, tool_args: dict, result: any, **kwargs):
        """Called after tool execution."""
        import time

        duration_ms = None
        if self._current_step_start:
            duration_ms = (time.time() - self._current_step_start) * 1000

        self.trace.add_step(Step.tool_call(
            name=tool_name,
            args=tool_args,
            result=result,
            duration_ms=duration_ms,
        ))

    def on_tool_error(self, tool_name: str, tool_args: dict, error: Exception, **kwargs):
        """Called when tool execution fails."""
        self.trace.add_step(Step.tool_call(
            name=tool_name,
            args=tool_args,
            result=None,
            status="error",
            error=str(error),
        ))

    def on_agent_end(self, output: str, **kwargs):
        """Called when agent execution completes."""
        self.trace.complete(output=output, status="success")

    def on_agent_error(self, error: Exception, **kwargs):
        """Called when agent execution fails."""
        self.trace.complete(output=str(error), status="error")

    def get_trace(self) -> Trace:
        """Get the captured trace."""
        if self.trace is None:
            raise ValueError("No trace captured. Was on_agent_start called?")
        return self.trace

    def reset(self):
        """Reset for a new trace."""
        self.trace = None
        self._current_step_start = None
```

### Step 3: Hook into the Framework

Integrate with the framework's callback system:

```python
class MyFrameworkTracer:
    # ... above methods ...

    def as_callback(self):
        """Return a callback object for the framework."""
        tracer = self

        class TracerCallback:
            def on_llm_start(self, model, prompt, **kwargs):
                tracer.on_llm_start(model, prompt, **kwargs)

            def on_llm_end(self, model, prompt, response, **kwargs):
                tracer.on_llm_end(model, prompt, response, **kwargs)

            # ... other methods ...

        return TracerCallback()


# Usage
tracer = MyFrameworkTracer()
agent.run(input, callbacks=[tracer.as_callback()])
trace = tracer.get_trace()
```

### Step 4: Add Tests

```python
# tests/test_my_framework_adapter.py
import pytest
from my_framework_adapter import MyFrameworkTracer


class TestMyFrameworkTracer:
    def test_captures_llm_calls(self):
        tracer = MyFrameworkTracer()

        tracer.on_agent_start("test input")
        tracer.on_llm_start("gpt-4", "prompt")
        tracer.on_llm_end("gpt-4", "prompt", "response")
        tracer.on_agent_end("final output")

        trace = tracer.get_trace()

        assert trace.input == "test input"
        assert trace.output == "final output"
        assert len(trace.llm_calls) == 1

    def test_captures_tool_calls(self):
        tracer = MyFrameworkTracer()

        tracer.on_agent_start("test")
        tracer.on_tool_start("search", {"query": "test"})
        tracer.on_tool_end("search", {"query": "test"}, {"results": []})
        tracer.on_agent_end("done")

        trace = tracer.get_trace()

        assert len(trace.tool_calls) == 1
        assert trace.tool_calls[0].tool_name == "search"

    def test_handles_errors(self):
        tracer = MyFrameworkTracer()

        tracer.on_agent_start("test")
        tracer.on_tool_start("broken", {})
        tracer.on_tool_error("broken", {}, ValueError("oops"))
        tracer.on_agent_error(ValueError("agent failed"))

        trace = tracer.get_trace()

        assert trace.status.value == "error"
        assert trace.tool_calls[0].error == "oops"
```

### Step 5: Add Documentation

Add a page to `docs/user-guide/integrations/` explaining how to use your adapter.

## Best Practices

1. **Capture everything** - LLM calls, tool calls, errors, timing
2. **Handle edge cases** - Missing data, errors, interrupts
3. **Preserve metadata** - Model names, token usage, durations
4. **Thread safety** - If framework supports concurrent execution
5. **Minimal overhead** - Don't slow down agent execution
6. **Test thoroughly** - Unit tests and integration tests
