# Quick Start

Get up and running with Evaldeck in under 5 minutes.

## Initialize Your Project

Run the init command in your project directory:

```bash
evaldeck init
```

This creates:

```
your-project/
├── evaldeck.yaml           # Configuration file
├── tests/
│   └── evals/
│       └── example.yaml  # Example test case
└── .evaldeck/              # Output directory (gitignore this)
```

## Configure Your Agent

### LangChain / LangGraph (Recommended)

For LangChain agents, use the built-in integration:

```yaml title="evaldeck.yaml"
version: 1

agent:
  module: my_agent
  function: create_agent
  framework: langchain      # Auto-instruments LangChain

test_dir: tests/evals
```

Your function returns the agent (evaldeck handles tracing):

```python title="my_agent.py"
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

def create_agent():
    llm = ChatOpenAI(model="gpt-4o-mini")
    tools = [...]  # Your tools
    return create_react_agent(llm, tools)
```

Install with: `pip install evaldeck[langchain]`

### Other Frameworks

For other frameworks, your function returns a `Trace`:

```yaml title="evaldeck.yaml"
version: 1

agent:
  module: my_agent
  function: run_agent

test_dir: tests/evals
```

```python title="my_agent.py"
from evaldeck import Trace, Step

def run_agent(input: str) -> Trace:
    trace = Trace(input=input)

    # Agent logic here...
    trace.add_step(Step.tool_call(
        tool_name="search",
        tool_args={"query": input},
        tool_result={"items": [...]}
    ))

    trace.complete(output="Here's what I found...")
    return trace
```

## Write Your First Test

Create a test case in `tests/evals/`:

```yaml title="tests/evals/search_test.yaml"
name: basic_search
description: Agent should search and return results
input: "Find restaurants near me"

expected:
  tools_called:
    - search
  output_contains:
    - "restaurant"
  task_completed: true
```

## Run Evaluations

Execute your tests:

```bash
evaldeck run
```

Output:

```
Loading configuration from evaldeck.yaml...
Discovering test suites in tests/evals/...
Found 1 test case(s)

Running evaluations...

  ✓ basic_search (0.8s)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Results: 1/1 passed (100.0%)
```

## CLI Options

### Filter by Tags

Run only tests with specific tags:

```bash
evaldeck run --tag critical
evaldeck run --tag "booking,search"
```

### Output Formats

Generate different output formats:

```bash
# Default: human-readable text
evaldeck run

# JSON output
evaldeck run --output json --output-file results.json

# JUnit XML (for CI/CD)
evaldeck run --output junit --output-file results.xml
```

### Verbose Mode

See detailed output including traces:

```bash
evaldeck run --verbose
```

## Example: Flight Booking Agent

Here's a complete example evaluating a flight booking agent:

```yaml title="tests/evals/flight_booking.yaml"
name: book_flight_basic
description: Book a simple one-way flight
input: "Book a flight from NYC to LA on March 15th"

expected:
  # Required tools must be called
  tools_called:
    - search_flights
    - book_flight

  # These tools should NOT be called
  tools_not_called:
    - cancel_booking

  # Output must contain these strings
  output_contains:
    - "confirmation"
    - "March 15"

  # Efficiency constraint
  max_steps: 5

  # Must complete successfully
  task_completed: true

tags:
  - booking
  - critical
```

Run it:

```bash
evaldeck run --tag booking
```

## What's Next?

- **[Your First Evaluation](first-evaluation.md)** - Deep dive into evaluation workflow
- **[Configuration](../user-guide/configuration.md)** - Full configuration reference
- **[Test Cases](../user-guide/test-cases.md)** - All test case options
- **[Graders](../user-guide/graders/index.md)** - Deterministic and LLM-based grading
