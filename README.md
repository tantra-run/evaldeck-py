# Evaldeck

**The evaluation framework for AI agents. Pytest for agents.**

[![PyPI version](https://badge.fury.io/py/evaldeck.svg)](https://badge.fury.io/py/evaldeck)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

Evaldeck helps you answer one question: **"Is my agent actually working?"**

Unlike LLM evaluation tools that focus on input→output scoring, Evaldeck evaluates the entire agent execution—how it reasons, which tools it selects, and whether it achieves the goal.

## Why Evaldeck?

- **Agent-native**: Evaluates multi-step traces, not just final outputs
- **Framework-agnostic**: Works with LangChain, CrewAI, AutoGen, or custom agents
- **Developer-friendly**: CLI-first, CI/CD ready, 5-minute setup
- **Comprehensive metrics**: Tool correctness, step efficiency, plan adherence, and more
- **Flexible grading**: Code-based, model-based (BYOK), or combine both

## Installation

```bash
pip install evaldeck
```

With framework integrations:

```bash
pip install evaldeck[langchain]  # LangChain/LangGraph support
pip install evaldeck[openai]     # OpenAI model graders
pip install evaldeck[all]        # Everything
```

## Quick Start

### 1. Initialize your project

```bash
evaldeck init
```

This creates:
```
evaldeck.yaml          # Configuration
tests/evals/         # Test directory
  example.yaml       # Example test case
```

### 2. Define test cases

```yaml
# tests/evals/booking.yaml
name: book_flight_basic
input: "Book me a flight from NYC to LA on March 15th"

expected:
  tools_called:
    - search_flights
    - book_flight
  output_contains:
    - "confirmation"
    - "March 15"
  max_steps: 5
```

### 3. Run evaluations

```bash
evaldeck run
```

Output:
```
Running 3 tests...

  ✓ book_flight_basic (1.2s)
  ✓ book_flight_roundtrip (2.1s)
  ✗ book_flight_with_preferences (1.8s)
    └─ FAIL at step 3: Wrong tool called
       Expected: search_flights_with_filters
       Got: search_flights

Results: 2/3 passed (66.7%)
```

## Configuration

```yaml
# evaldeck.yaml
version: 1

agent:
  module: my_agent
  function: run

test_dir: tests/evals

defaults:
  timeout: 30
  retries: 2

graders:
  llm:
    model: gpt-4o-mini
    # Uses OPENAI_API_KEY from environment

thresholds:
  min_pass_rate: 0.9
```

## Test Case Format

### Basic test case

```yaml
name: test_name
input: "User message to the agent"

expected:
  # What tools should be called?
  tools_called:
    - tool_name_1
    - tool_name_2

  # What tools should NOT be called?
  tools_not_called:
    - dangerous_tool

  # What should the output contain?
  output_contains:
    - "expected phrase"

  # What should the output NOT contain?
  output_not_contains:
    - "error"

  # Maximum steps allowed
  max_steps: 10

  # Must complete successfully?
  task_completed: true
```

### Using model-based grading

```yaml
name: helpful_response
input: "Explain quantum computing"

graders:
  - type: llm
    prompt: |
      Rate this response for helpfulness and accuracy.
      Response: {{ output }}

      Score from 1-5, where 5 is excellent.
    threshold: 4
```

## Framework Integration

### LangChain

Copy the reference tracer from `examples/langchain_tracer.py` to your project:

```python
from langchain_tracer import EvaldeckTracer
from langchain.agents import AgentExecutor

tracer = EvaldeckTracer()
agent = AgentExecutor(...)

result = agent.invoke(
    {"input": "Book a flight"},
    config={"callbacks": [tracer]}
)

# Get trace for evaluation
trace = tracer.get_trace()
```

### Manual trace construction

```python
from evaldeck import Trace, Step, Evaluator

trace = Trace(
    input="Book a flight from NYC to LA",
    steps=[
        Step(
            type="tool_call",
            tool_name="search_flights",
            tool_args={"from": "NYC", "to": "LA"},
            tool_result=[{"flight": "AA123", "price": 299}]
        ),
        Step(
            type="tool_call",
            tool_name="book_flight",
            tool_args={"flight_id": "AA123"},
            tool_result={"confirmation": "ABC123"}
        ),
    ],
    output="Your flight AA123 is booked. Confirmation: ABC123",
    status="success"
)

evaluator = Evaluator()
result = evaluator.evaluate(trace, test_case)
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/evaldeck.yaml
name: Agent Evaluation

on: [push, pull_request]

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - run: pip install evaldeck[all]

      - run: evaldeck run --output junit --output-file results.xml
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

      - uses: mikepenz/action-junit-report@v4
        if: always()
        with:
          report_paths: results.xml
```

## Metrics

| Metric | Description |
|--------|-------------|
| `task_completion` | Did the agent achieve the goal? |
| `tool_correctness` | Were the right tools selected? |
| `argument_correctness` | Were correct arguments passed to tools? |
| `step_efficiency` | Did it complete without unnecessary steps? |
| `tool_call_ordering` | Were tools called in the right sequence? |

## Graders

### Code-based (deterministic)

```python
from evaldeck.graders import ContainsGrader, ToolCalledGrader

graders = [
    ContainsGrader(values=["confirmation"]),
    ToolCalledGrader(required=["book_flight"]),
]
```

### Model-based (LLM-as-judge)

```python
from evaldeck.graders import LLMGrader

grader = LLMGrader(
    prompt="Did the agent complete the booking? Answer: pass or fail",
    model="gpt-4o-mini",  # Uses your API key
)
```

## Roadmap

- [x] Core evaluation engine
- [x] CLI interface
- [x] LangChain integration
- [ ] CrewAI integration
- [ ] AutoGen integration
- [ ] VS Code extension
- [ ] Historical result tracking
- [ ] Team dashboard (cloud)

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Setup development environment
git clone https://github.com/tantra-run/evaldeck-py.git
cd evaldeck
pip install -e ".[dev]"
pre-commit install

# Run tests
pytest

# Run linting
ruff check .
mypy src/
```

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.
