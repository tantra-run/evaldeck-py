# OpenTelemetry / OpenInference Integration

The OpenTelemetry adapter provides **broad framework coverage with a single integration**. It uses [OpenInference](https://github.com/Arize-ai/openinference) semantic conventions to capture traces from any instrumented AI framework.

## Supported Frameworks

Any framework with an OpenInference instrumentor works automatically:

| Framework | Instrumentor Package |
|-----------|---------------------|
| LangChain / LangGraph | `openinference-instrumentation-langchain` |
| CrewAI | `openinference-instrumentation-crewai` |
| LiteLLM | `openinference-instrumentation-litellm` |
| OpenAI SDK | `openinference-instrumentation-openai` |
| Anthropic SDK | `openinference-instrumentation-anthropic` |
| AutoGen | `openinference-instrumentation-autogen` |
| LlamaIndex | `openinference-instrumentation-llama-index` |
| Haystack | `openinference-instrumentation-haystack` |
| DSPy | `openinference-instrumentation-dspy` |
| Bedrock | `openinference-instrumentation-bedrock` |
| Groq | `openinference-instrumentation-groq` |
| Mistral | `openinference-instrumentation-mistralai` |

See the [full list of instrumentors](https://github.com/Arize-ai/openinference).

## Installation

```bash
pip install evaldeck

# Install instrumentor(s) for your framework
pip install openinference-instrumentation-langchain
pip install openinference-instrumentation-crewai
pip install openinference-instrumentation-openai
# ... etc
```

## Quick Start

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from openinference.instrumentation.langchain import LangChainInstrumentor

from evaldeck.integrations import EvaldeckSpanProcessor

# 1. Setup tracing
processor = EvaldeckSpanProcessor()
provider = TracerProvider()
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# 2. Instrument your framework
LangChainInstrumentor().instrument()

# 3. Run your agent (no changes to your code needed)
result = agent.invoke({"input": "Book a flight to NYC"})

# 4. Get trace and evaluate
evaldeck_trace = processor.get_latest_trace()

evaluator = Evaluator()
result = evaluator.evaluate(evaldeck_trace, test_case)
```

## Convenience Setup

Use the helper function for simpler setup:

```python
from evaldeck.integrations import setup_otel_tracing
from openinference.instrumentation.langchain import LangChainInstrumentor

# One-line setup
processor = setup_otel_tracing()
LangChainInstrumentor().instrument()

# Run agent...
trace = processor.get_latest_trace()
```

## Multiple Frameworks

Instrument multiple frameworks at once:

```python
from evaldeck.integrations import setup_otel_tracing
from openinference.instrumentation.langchain import LangChainInstrumentor
from openinference.instrumentation.openai import OpenAIInstrumentor
from openinference.instrumentation.litellm import LiteLLMInstrumentor

processor = setup_otel_tracing()

# Instrument all frameworks you use
LangChainInstrumentor().instrument()
OpenAIInstrumentor().instrument()
LiteLLMInstrumentor().instrument()

# All traces go to the same processor
# regardless of which framework generated them
```

## Running Test Suites

```python
from evaldeck.integrations import setup_otel_tracing
from openinference.instrumentation.crewai import CrewAIInstrumentor
from evaldeck import Evaluator, EvalSuite

# Setup once at module level
processor = setup_otel_tracing()
CrewAIInstrumentor().instrument()

def run_agent(input_text: str):
    """Agent function that returns a trace."""
    processor.reset()  # Clear previous traces

    # Run your agent
    crew.kickoff(inputs={"query": input_text})

    return processor.get_latest_trace()

# Load and run test suite
suite = EvalSuite.from_directory("tests/evals/")
evaluator = Evaluator()
results = evaluator.evaluate_suite(suite, run_agent)
```

## How It Works

The `EvaldeckSpanProcessor` intercepts OpenTelemetry spans and converts them to Evaldeck's `Trace`/`Step` format:

| OpenInference Span Kind | Evaldeck StepType |
|------------------------|-------------------|
| `LLM` | `LLM_CALL` |
| `TOOL` | `TOOL_CALL` |
| `CHAIN` (root) | Trace container |
| `CHAIN` (nested) | `REASONING` |
| `EMBEDDING` | `TOOL_CALL` (tool_name="embedding") |
| `RETRIEVER` | `TOOL_CALL` (tool_name="retriever") |
| `RERANKER` | `TOOL_CALL` (tool_name="reranker") |
| `GUARDRAIL` | `REASONING` |

**Captured data:**
- LLM calls: model name, input/output messages, token usage
- Tool calls: tool name, arguments, results
- Timing: duration for each step
- Errors: captured with status and message
- Metadata: OpenTelemetry trace/span IDs for cross-referencing

## API Reference

### EvaldeckSpanProcessor

```python
processor = EvaldeckSpanProcessor()

# Get a specific trace by ID
trace = processor.get_trace("abc123...")

# Get the most recent trace
trace = processor.get_latest_trace()

# Get all captured traces
traces = processor.get_all_traces()

# Clear all traces (useful between test runs)
processor.reset()
```

### setup_otel_tracing()

```python
from evaldeck.integrations import setup_otel_tracing

# Create processor and configure OpenTelemetry
processor = setup_otel_tracing()

# Or pass an existing processor
existing_processor = EvaldeckSpanProcessor()
processor = setup_otel_tracing(processor=existing_processor)
```

## Using with Arize Phoenix

You can send traces to both Evaldeck and Phoenix simultaneously:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from evaldeck.integrations import EvaldeckSpanProcessor

# Evaldeck processor
evaldeck_processor = EvaldeckSpanProcessor()

# Phoenix exporter (or any OTLP endpoint)
phoenix_exporter = OTLPSpanExporter(endpoint="http://localhost:6006/v1/traces")
phoenix_processor = BatchSpanProcessor(phoenix_exporter)

# Add both to the provider
provider = TracerProvider()
provider.add_span_processor(evaldeck_processor)
provider.add_span_processor(phoenix_processor)
trace.set_tracer_provider(provider)

# Now traces go to both Evaldeck (for evaluation) and Phoenix (for visualization)
```

## Troubleshooting

### No traces captured

1. Ensure you call `setup_otel_tracing()` **before** instrumenting frameworks
2. Ensure you instrument the framework **before** importing/creating agents
3. Check that spans have `openinference.span.kind` attribute set

### Missing steps

Some frameworks may not emit all span types. Check which span kinds your instrumentor supports.

### Token counts missing

Not all LLM providers return token usage. The `tokens` field will have zeros if not available.
