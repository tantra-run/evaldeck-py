# Traces & Steps

A **Trace** is the complete record of an agent's execution. Understanding traces is essential for effective agent evaluation.

## What is a Trace?

A trace captures everything that happened during agent execution:

```
Input: "Book a flight to NYC"
                 │
                 ▼
┌─────────────────────────────────────┐
│              Trace                  │
├─────────────────────────────────────┤
│ Step 1: LLM_CALL                    │
│   "I'll search for flights..."      │
├─────────────────────────────────────┤
│ Step 2: TOOL_CALL (search_flights)  │
│   → Found 3 flights                 │
├─────────────────────────────────────┤
│ Step 3: REASONING                   │
│   "AA123 is cheapest, selecting..." │
├─────────────────────────────────────┤
│ Step 4: TOOL_CALL (book_flight)     │
│   → Confirmation: ABC123            │
├─────────────────────────────────────┤
│ Step 5: LLM_CALL                    │
│   "Your flight is booked..."        │
└─────────────────────────────────────┘
                 │
                 ▼
Output: "Your flight to NYC is booked. Confirmation: ABC123"
```

## Trace Structure

```python
from evaldeck import Trace, TraceStatus

trace = Trace(
    # Required
    input="User's request",

    # Set after execution
    output="Agent's response",
    status=TraceStatus.SUCCESS,

    # Execution details
    steps=[...],
    started_at=datetime(...),
    completed_at=datetime(...),
    duration_ms=1500,

    # Metadata
    framework="langchain",
    agent_name="BookingAgent",
    metadata={"user_id": "123"}
)
```

### Trace Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Unique identifier (auto-generated) |
| `input` | str | User input to the agent |
| `output` | str | Agent's final output |
| `status` | TraceStatus | SUCCESS, FAILURE, TIMEOUT, ERROR |
| `steps` | list[Step] | Ordered list of execution steps |
| `started_at` | datetime | When execution started |
| `completed_at` | datetime | When execution completed |
| `duration_ms` | int | Total execution time |
| `framework` | str | Framework name (e.g., "langchain") |
| `agent_name` | str | Agent identifier |
| `metadata` | dict | Custom key-value data |

### Trace Status

| Status | When to Use |
|--------|-------------|
| `SUCCESS` | Agent completed task successfully |
| `FAILURE` | Agent failed to complete task |
| `TIMEOUT` | Execution exceeded time limit |
| `ERROR` | Unexpected error occurred |

## Step Types

Each step in a trace has a type:

### TOOL_CALL

Agent invoked a tool/function:

```python
from evaldeck import Step

step = Step.tool_call(
    tool_name="search_flights",
    tool_args={"from": "NYC", "to": "LA", "date": "2024-03-15"},
    tool_result={"flights": [{"id": "AA123", "price": 299}]},
    duration_ms=150,
    status="success"
)
```

Fields:

- `tool_name`: Name of the tool called
- `tool_args`: Arguments passed to the tool
- `tool_result`: What the tool returned
- `status`: "success" or "error"
- `error`: Error message if failed

### LLM_CALL

Agent called a language model:

```python
from evaldeck import Step, TokenUsage

step = Step.llm_call(
    model="gpt-4o-mini",
    input="Parse this request: Book a flight to NYC",
    output='{"destination": "NYC", "type": "flight"}',
    token_usage=TokenUsage(prompt_tokens=50, completion_tokens=20, total_tokens=70),
    duration_ms=500
)
```

Fields:

- `model`: Model identifier
- `input`: Prompt sent to model
- `output`: Model's response
- `token_usage`: Token consumption

### REASONING

Agent's internal reasoning:

```python
step = Step.reasoning(
    text="User wants to book a flight. I should search for available flights first.",
    duration_ms=10
)
```

Fields:

- `reasoning_text`: The reasoning content

### HUMAN_INPUT

Human-in-the-loop input:

```python
step = Step(
    type=StepType.HUMAN_INPUT,
    input="Is this the correct flight?",
    output="Yes, proceed with booking"
)
```

## Step Structure

All steps share common fields:

```python
Step(
    # Identity
    id="step_001",
    type=StepType.TOOL_CALL,

    # Timing
    timestamp=datetime.now(),
    duration_ms=150,

    # Status
    status=StepStatus.SUCCESS,  # or FAILURE, ERROR
    error=None,

    # Type-specific fields
    tool_name="search",
    tool_args={...},
    tool_result={...},

    # Or for LLM calls
    model="gpt-4o-mini",
    input="...",
    output="...",
    token_usage=TokenUsage(...),

    # Metadata
    metadata={"custom": "data"}
)
```

## Building Traces

### Manual Construction

```python
from evaldeck import Trace, Step, TokenUsage

trace = Trace(input="Book a flight to NYC")

# Add steps as execution proceeds
trace.add_step(Step.llm_call(
    model="gpt-4o-mini",
    input="Parse: Book a flight to NYC",
    output="destination=NYC, type=flight",
    token_usage=TokenUsage(prompt_tokens=30, completion_tokens=10, total_tokens=40)
))

trace.add_step(Step.tool_call(
    tool_name="search_flights",
    tool_args={"destination": "NYC"},
    tool_result={"flights": [...]}
))

# Complete the trace
trace.complete(
    output="Your flight is booked!",
    status="success"
)
```

### With OpenTelemetry Integration

Use the built-in OpenTelemetry adapter to capture traces automatically:

```python
from evaldeck.integrations import setup_otel_tracing
from openinference.instrumentation.langchain import LangChainInstrumentor

# Setup once at module level
processor = setup_otel_tracing()
LangChainInstrumentor().instrument()

# Run agent (traces captured automatically)
processor.reset()
result = agent.invoke({"input": "..."})
trace = processor.get_latest_trace()
```

## Accessing Trace Data

### Step Iteration

```python
for step in trace.steps:
    print(f"{step.type}: {step.status}")
```

### Filtered Access

```python
# Get all tool calls
tool_calls = trace.tool_calls
for tc in tool_calls:
    print(f"{tc.tool_name}({tc.tool_args}) -> {tc.tool_result}")

# Get all LLM calls
llm_calls = trace.llm_calls
for lc in llm_calls:
    print(f"{lc.model}: {lc.token_usage.total} tokens")
```

### Computed Properties

```python
# Set of tool names called
tools = trace.tools_called  # {"search", "book"}

# Total token usage
tokens = trace.total_tokens  # 250

# Step count
count = trace.step_count  # 5

# Duration
duration = trace.duration_ms  # 1500
```

## Serialization

### To Dictionary

```python
data = trace.to_dict()
# {'id': '...', 'input': '...', 'steps': [...], ...}
```

### From Dictionary

```python
trace = Trace.from_dict(data)
```

### To/From JSON

```python
import json

# Serialize
json_str = json.dumps(trace.to_dict())

# Deserialize
trace = Trace.from_dict(json.loads(json_str))
```

## Why Traces Matter

### 1. Granular Debugging

When a test fails, the trace shows exactly where:

```
Step 1: LLM_CALL ✓
Step 2: TOOL_CALL (search) ✓
Step 3: TOOL_CALL (book) ✗  ← Failed here
        Error: "Invalid flight ID"
```

### 2. Behavioral Verification

Check not just output, but how the agent got there:

```yaml
expected:
  tools_called: [search, book]  # Verify the path
  tool_call_order: [search, book]  # Verify the sequence
```

### 3. Efficiency Analysis

Measure and optimize agent behavior:

```python
print(f"Steps: {trace.step_count}")
print(f"Tokens: {trace.total_tokens}")
print(f"Duration: {trace.duration_ms}ms")
```

### 4. Regression Detection

Compare traces across versions to catch regressions:

```python
# Before: 3 steps, 150 tokens
# After: 7 steps, 450 tokens  ← Regression!
```

## Best Practices

1. **Capture everything** - Include reasoning steps, not just tool calls
2. **Track timing** - `duration_ms` helps identify bottlenecks
3. **Include metadata** - Add context that helps debugging
4. **Use status correctly** - Distinguish between failure modes
5. **Complete traces properly** - Always call `complete()` with final status
