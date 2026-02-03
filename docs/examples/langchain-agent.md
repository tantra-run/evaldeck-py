# LangChain Agent

Evaluate LangChain and LangGraph agents using Evaldeck's OpenTelemetry integration.

## Setup

```bash
pip install evaldeck langchain-core langchain-openai
pip install opentelemetry-sdk openinference-instrumentation-langchain
```

## Basic Example

```python
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from langchain import hub
from openinference.instrumentation.langchain import LangChainInstrumentor

from evaldeck import Evaluator, EvalCase, ExpectedBehavior
from evaldeck.integrations import setup_otel_tracing

# Setup tracing (do this once at module level)
processor = setup_otel_tracing()
LangChainInstrumentor().instrument()


# Define tools
def search_flights(query: str) -> str:
    """Search for available flights."""
    return "Found flights: AA123 ($299), UA456 ($349)"


def book_flight(flight_id: str) -> str:
    """Book a specific flight."""
    return f"Booked {flight_id}. Confirmation: ABC123"


tools = [
    Tool(name="search_flights", func=search_flights,
         description="Search for flights. Input: destination city"),
    Tool(name="book_flight", func=book_flight,
         description="Book a flight. Input: flight ID"),
]

# Create agent
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
prompt = hub.pull("hwchase17/react")
agent = create_react_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Run agent (traces captured automatically)
processor.reset()  # Clear previous traces
result = executor.invoke({"input": "Book the cheapest flight to New York"})

# Get trace
trace = processor.get_latest_trace()

print(f"Agent output: {result['output']}")
print(f"Steps: {trace.step_count}")
print(f"Tools called: {trace.tools_called}")


# Evaluate
test = EvalCase(
    name="book_cheapest_flight",
    input="Book the cheapest flight to New York",
    expected=ExpectedBehavior(
        tools_called=["search_flights", "book_flight"],
        output_contains=["booked", "confirmation"],
        max_steps=6
    )
)

evaluator = Evaluator()
eval_result = evaluator.evaluate(trace, test)

print(f"\nEvaluation: {'PASS' if eval_result.passed else 'FAIL'}")
for grade in eval_result.grades:
    print(f"  {grade.grader_name}: {grade.status}")
```

## Reusable Agent Function

Create a function that returns traces for use with test suites:

```python
from evaldeck import Trace
from evaldeck.integrations import setup_otel_tracing
from openinference.instrumentation.langchain import LangChainInstrumentor

# Setup once at module level
processor = setup_otel_tracing()
LangChainInstrumentor().instrument()


def run_booking_agent(input: str) -> Trace:
    """Run the booking agent and return a trace."""
    processor.reset()  # Clear previous traces

    executor.invoke({"input": input})

    return processor.get_latest_trace()


# Use with test suite
from evaldeck import EvalSuite

suite = EvalSuite.from_directory("tests/evals/booking")
evaluator = Evaluator()

suite_result = evaluator.evaluate_suite(suite, run_booking_agent)
print(f"Results: {suite_result.passed}/{suite_result.total} passed")
```

## With evaldeck.yaml

Configure for CLI usage:

```yaml
# evaldeck.yaml
version: 1

agent:
  module: my_langchain_agent
  function: run_agent

test_dir: tests/evals

defaults:
  timeout: 60

graders:
  llm:
    model: gpt-4o-mini
```

```python
# my_langchain_agent.py
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from langchain import hub
from openinference.instrumentation.langchain import LangChainInstrumentor

from evaldeck import Trace
from evaldeck.integrations import setup_otel_tracing

# Setup tracing at module level
processor = setup_otel_tracing()
LangChainInstrumentor().instrument()

# Setup agent (module level)
llm = ChatOpenAI(model="gpt-4o-mini")
prompt = hub.pull("hwchase17/react")
tools = [...]  # Your tools
agent = create_react_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools)


def run_agent(input: str) -> Trace:
    """Entry point for Evaldeck CLI."""
    processor.reset()
    executor.invoke({"input": input})
    return processor.get_latest_trace()
```

Run with CLI:

```bash
evaldeck run
```

## Test Cases

```yaml
# tests/evals/booking/basic.yaml
name: book_flight_basic
input: "Book a flight to Los Angeles"

expected:
  tools_called:
    - search_flights
    - book_flight
  output_contains:
    - "booked"
    - "confirmation"
  max_steps: 6

tags:
  - booking
  - smoke

---
# tests/evals/booking/search_only.yaml
name: search_flights_only
input: "What flights are available to Chicago?"

expected:
  tools_called:
    - search_flights
  tools_not_called:
    - book_flight  # Should only search, not book
  output_contains:
    - "flight"
    - "Chicago"

tags:
  - search
  - smoke
```

## LangGraph Example

Works the same way with LangGraph:

```python
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from openinference.instrumentation.langchain import LangChainInstrumentor

from evaldeck import Trace
from evaldeck.integrations import setup_otel_tracing

# Setup tracing
processor = setup_otel_tracing()
LangChainInstrumentor().instrument()

# Create LangGraph agent
llm = ChatOpenAI(model="gpt-4o-mini")
tools = [...]
agent = create_react_agent(llm, tools)


def run_langgraph_agent(input: str) -> Trace:
    processor.reset()
    agent.invoke({"messages": [("user", input)]})
    return processor.get_latest_trace()
```

## Complete Script

```python
#!/usr/bin/env python3
"""Complete LangChain evaluation example."""

import os
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from langchain import hub
from openinference.instrumentation.langchain import LangChainInstrumentor

from evaldeck import (
    Trace, EvalCase, EvalSuite, ExpectedBehavior, Evaluator
)
from evaldeck.integrations import setup_otel_tracing

# Setup tracing
processor = setup_otel_tracing()
LangChainInstrumentor().instrument()


def search_flights(destination: str) -> str:
    """Search for flights to a destination."""
    flights = {
        "new york": "AA123 ($299), UA456 ($349)",
        "los angeles": "DL789 ($199), AA012 ($249)",
        "chicago": "UA345 ($179), AA678 ($199)",
    }
    dest_lower = destination.lower()
    for city, result in flights.items():
        if city in dest_lower:
            return f"Flights to {destination}: {result}"
    return f"No flights found to {destination}"


def book_flight(flight_id: str) -> str:
    """Book a flight by ID."""
    return f"Successfully booked {flight_id}. Confirmation: CONF{flight_id[-3:]}"


def main():
    # Create tools
    tools = [
        Tool(name="search_flights", func=search_flights,
             description="Search for flights. Input: destination city name"),
        Tool(name="book_flight", func=book_flight,
             description="Book a flight. Input: flight ID (e.g., AA123)"),
    ]

    # Create agent
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = hub.pull("hwchase17/react")
    agent = create_react_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=False)

    # Define tests
    tests = [
        EvalCase(
            name="book_to_la",
            input="Book the cheapest flight to Los Angeles",
            expected=ExpectedBehavior(
                tools_called=["search_flights", "book_flight"],
                output_contains=["booked", "confirmation"],
            )
        ),
        EvalCase(
            name="search_chicago",
            input="What flights go to Chicago?",
            expected=ExpectedBehavior(
                tools_called=["search_flights"],
                tools_not_called=["book_flight"],
                output_contains=["chicago", "flight"],
            )
        ),
    ]

    # Run evaluations
    evaluator = Evaluator()
    results = []

    for test in tests:
        processor.reset()
        executor.invoke({"input": test.input})
        trace = processor.get_latest_trace()

        result = evaluator.evaluate(trace, test)
        results.append(result)

        status = "PASS" if result.passed else "FAIL"
        print(f"{test.name}: {status}")
        if not result.passed:
            for grade in result.failed_grades:
                print(f"  - {grade.grader_name}: {grade.message}")

    # Summary
    passed = sum(1 for r in results if r.passed)
    print(f"\nResults: {passed}/{len(results)} passed")


if __name__ == "__main__":
    main()
```
