# Configuration

Evaldeck uses a YAML configuration file to define project settings. This guide covers all configuration options.

## Configuration File

Evaldeck looks for configuration in this order:

1. `evaldeck.yaml`
2. `evaldeck.yml`
3. `.evaldeck.yaml`

You can also specify a custom path:

```bash
evaldeck run --config path/to/config.yaml
```

## Full Configuration Reference

```yaml
# evaldeck.yaml

# Configuration version (required)
version: 1

# Agent configuration (required for `evaldeck run`)
agent:
  module: my_agent        # Python module containing your agent
  function: run_agent     # Function to call (receives input string)
  # class_name: MyAgent   # Optional: if using a class

# Test directory
test_dir: tests/evals     # Where to find test case YAML files

# Test suites (optional, alternative to test_dir)
suites:
  - name: critical
    path: tests/evals/critical
    tags: [critical]
  - name: regression
    path: tests/evals/regression

# Default settings for all tests
defaults:
  timeout: 30             # Timeout in seconds
  retries: 0              # Number of retries on failure

# Grader settings
graders:
  llm:
    model: gpt-4o-mini    # Default model for LLM graders
    provider: openai      # openai or anthropic
    timeout: 60           # LLM call timeout

# Pass/fail thresholds
thresholds:
  min_pass_rate: 0.0      # Minimum pass rate (0.0-1.0)
  max_failures: null      # Maximum allowed failures (null = unlimited)

# Output settings
output_dir: .evaldeck       # Directory for results and artifacts
```

## Agent Configuration

### With Framework Integration (Recommended)

For supported frameworks, use the `framework` option for automatic instrumentation:

```yaml
agent:
  module: my_agent
  function: create_agent
  framework: langchain
```

Your function returns the agent instance (not a Trace):

```python
# my_agent.py
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

def create_agent():
    llm = ChatOpenAI(model="gpt-4o-mini")
    return create_react_agent(llm, tools=[...])
```

Evaldeck handles OTel instrumentation and trace capture automatically.

**Supported frameworks:**

| Framework | Value | Install |
|-----------|-------|---------|
| LangChain / LangGraph | `langchain` | `pip install evaldeck[langchain]` |

### Without Framework Integration

If not using a supported framework, your function must return a `Trace`:

```yaml
agent:
  module: my_package.agents.booking
  function: run_booking_agent
```

```python
# my_package/agents/booking.py
from evaldeck import Trace, Step

def run_booking_agent(input: str) -> Trace:
    trace = Trace(input=input)
    # ... agent logic ...
    trace.complete(output="...")
    return trace
```

### Using a Class

If your agent is a class:

```yaml
agent:
  module: my_package.agents
  class_name: BookingAgent
  function: run  # Method to call
```

```python
# my_package/agents.py
from evaldeck import Trace

class BookingAgent:
    def __init__(self):
        # Setup...
        pass

    def run(self, input: str) -> Trace:
        trace = Trace(input=input)
        # ... agent logic ...
        return trace
```

## Test Directories and Suites

### Simple Setup

For most projects, a single test directory is sufficient:

```yaml
test_dir: tests/evals
```

Evaldeck will recursively discover all `.yaml` files:

```
tests/evals/
├── booking.yaml
├── search.yaml
└── complex/
    ├── multi_step.yaml
    └── edge_cases.yaml
```

### Named Suites

For larger projects, organize into named suites:

```yaml
suites:
  - name: smoke
    path: tests/smoke
    tags: [quick]

  - name: regression
    path: tests/regression
    tags: [full]

  - name: critical
    path: tests/critical
    tags: [critical, ci]
```

Run specific suites:

```bash
evaldeck run --suite smoke
evaldeck run --suite critical
```

## Default Settings

Defaults apply to all test cases unless overridden:

```yaml
defaults:
  timeout: 30    # 30 second timeout
  retries: 2     # Retry twice on failure
```

Override per test case:

```yaml
# tests/evals/slow_test.yaml
name: complex_operation
timeout: 120    # Override: 2 minute timeout
retries: 0      # Override: no retries
```

## Grader Configuration

### LLM Grader Defaults

Set defaults for all LLM graders:

```yaml
graders:
  llm:
    model: gpt-4o-mini      # Model to use
    provider: openai        # openai or anthropic
    timeout: 60             # Timeout for LLM calls
```

### Provider Configuration

LLM graders use environment variables for authentication:

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
```

Override the model per test case:

```yaml
graders:
  - type: llm
    model: gpt-4o           # Use GPT-4 for this test
    prompt: "Evaluate..."
```

## Thresholds

Thresholds determine when an evaluation run passes or fails:

```yaml
thresholds:
  min_pass_rate: 0.9    # 90% of tests must pass
  max_failures: 5       # Or at most 5 failures
```

### CI/CD Thresholds

For production CI:

```yaml
thresholds:
  min_pass_rate: 1.0    # All tests must pass
```

For development:

```yaml
thresholds:
  min_pass_rate: 0.8    # Allow 20% failure rate
```

## Environment Variables

Evaldeck supports environment variable substitution:

```yaml
agent:
  module: ${AGENT_MODULE:-my_agent}  # Default: my_agent

graders:
  llm:
    model: ${LLM_MODEL:-gpt-4o-mini}
```

Common environment variables:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for LLM graders |
| `ANTHROPIC_API_KEY` | Anthropic API key for LLM graders |
| `EVALDECK_CONFIG` | Custom config file path |
| `EVALDECK_VERBOSE` | Enable verbose output |

## Multiple Configurations

Use different configs for different scenarios:

```
configs/
├── evaldeck.yaml          # Default development config
├── evaldeck.ci.yaml       # CI/CD config (stricter thresholds)
└── evaldeck.local.yaml    # Local testing config
```

```bash
# Development
evaldeck run

# CI/CD
evaldeck run --config config/evaldeck.ci.yaml
```

## Validation

Evaldeck validates your configuration on load. Common errors:

```
Error: Invalid configuration
  - agent.module: Required field missing
  - thresholds.min_pass_rate: Must be between 0.0 and 1.0
```

To validate without running:

```bash
evaldeck run --dry-run
```
