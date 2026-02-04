# LangChain Agent

Evaluate LangChain and LangGraph agents using Evaldeck.

## Quick Start

The easiest way to get started is to use the built-in LangChain integration in `evaldeck.yaml`:

```yaml
# evaldeck.yaml
version: 1

agent:
  module: my_agent
  function: create_agent
  framework: langchain  # Auto-instruments LangChain

test_dir: tests/evals
```

```python
# my_agent.py
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

def create_agent():
    llm = ChatOpenAI(model="gpt-4o-mini")
    tools = [...]  # Your tools
    return create_react_agent(llm, tools)
```

Then run:

```bash
evaldeck run
```

## Complete Example Project

See the **[evaldeck-langchain-example](https://github.com/tantra-run/evaldeck-langchain-example)** repository for a complete working example with:

- LangGraph ReAct agent with tools
- Multiple test cases (weather, calculator, flights, booking)
- LLM-as-judge grading
- Proper project structure

```bash
git clone https://github.com/tantra-run/evaldeck-langchain-example
cd evaldeck-langchain-example
pip install -e .
evaldeck run
```

## Test Cases

Define test cases in YAML:

```yaml
# tests/evals/book_flight.yaml
name: book_flight
description: Agent should find and book the cheapest flight
turns:
  - user: "Find the cheapest flight from NYC to LA and book it"
    expected:
      tools_called:
        - search_flights
        - book_flight
      output_contains:
        - confirmation
        - booked
      max_tool_calls: 5
tags:
  - flights
  - booking
```

## Manual Tracing (Advanced)

If you need more control over tracing, you can use the OpenTelemetry integration directly:

```python
from evaldeck import Trace
from evaldeck.integrations import setup_otel_tracing
from openinference.instrumentation.langchain import LangChainInstrumentor

# Setup tracing once at module level
processor = setup_otel_tracing()
LangChainInstrumentor().instrument()

def run_agent(input: str, history=None) -> Trace:
    """Run agent and return trace."""
    processor.reset()

    # Your agent invocation
    agent.invoke({"messages": [("user", input)]})

    return processor.get_latest_trace()
```

## Installation

```bash
pip install evaldeck[langchain]
```

This installs:
- `opentelemetry-sdk`
- `openinference-instrumentation-langchain`

You also need LangChain itself:

```bash
pip install langchain-openai langgraph
```
