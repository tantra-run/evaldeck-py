# Code-Based Graders

Code-based graders perform deterministic checks on agent execution. They're fast, free, and predictable.

## When to Use

Use code-based graders for:

- Verifying specific tools were called
- Checking output contains/doesn't contain strings
- Validating output format with regex
- Enforcing step limits
- Any objective, rule-based criteria

## Available Graders

### ContainsGrader

Checks that the output contains expected strings.

**YAML:**

```yaml
expected:
  output_contains:
    - "confirmation"
    - "booking reference"
```

**Python:**

```python
from evaldeck.graders import ContainsGrader

grader = ContainsGrader(
    values=["confirmation", "booking reference"],
    case_sensitive=False  # Default: False
)
```

**Behavior:**

- All values must be present
- Case-insensitive by default
- Partial matches count (e.g., "confirm" matches "confirmation")

---

### NotContainsGrader

Checks that the output does NOT contain forbidden strings.

**YAML:**

```yaml
expected:
  output_not_contains:
    - "error"
    - "failed"
    - "exception"
```

**Python:**

```python
from evaldeck.graders import NotContainsGrader

grader = NotContainsGrader(
    values=["error", "failed", "exception"],
    case_sensitive=False
)
```

---

### EqualsGrader

Checks for exact output match.

**YAML:**

```yaml
expected:
  output_equals: "Operation completed successfully."
```

**Python:**

```python
from evaldeck.graders import EqualsGrader

grader = EqualsGrader(
    expected="Operation completed successfully.",
    strip_whitespace=True  # Default: True
)
```

**Note:** Rarely used since most agent outputs have dynamic content.

---

### RegexGrader

Checks output against a regex pattern.

**YAML:**

```yaml
expected:
  output_matches: "Confirmation: [A-Z]{3}\\d{6}"
```

**Python:**

```python
from evaldeck.graders import RegexGrader

grader = RegexGrader(
    pattern=r"Confirmation: [A-Z]{3}\d{6}",
    flags=0  # re module flags
)
```

**Examples:**

```yaml
# Email format
output_matches: "[\\w.-]+@[\\w.-]+\\.\\w+"

# JSON object
output_matches: "\\{.*\\}"

# Date format
output_matches: "\\d{4}-\\d{2}-\\d{2}"
```

---

### ToolCalledGrader

Verifies that required tools were called.

**YAML:**

```yaml
expected:
  tools_called:
    - search_flights
    - book_flight
```

**Python:**

```python
from evaldeck.graders import ToolCalledGrader

grader = ToolCalledGrader(
    required=["search_flights", "book_flight"]
)
```

**Behavior:**

- All listed tools must be called at least once
- Order doesn't matter
- Extra tool calls are allowed

**Failure output:**

```
ToolCalledGrader: FAIL
  Expected: ['search_flights', 'book_flight']
  Actual: ['search_flights']
  Missing: ['book_flight']
```

---

### ToolNotCalledGrader

Verifies that forbidden tools were NOT called.

**YAML:**

```yaml
expected:
  tools_not_called:
    - delete_account
    - admin_override
    - drop_database
```

**Python:**

```python
from evaldeck.graders import ToolNotCalledGrader

grader = ToolNotCalledGrader(
    forbidden=["delete_account", "admin_override"]
)
```

**Use cases:**

- Ensuring dangerous tools aren't called
- Verifying agent stays within scope
- Security constraints

---

### ToolOrderGrader

Verifies tools were called in a specific order.

**YAML:**

```yaml
expected:
  tool_call_order:
    - authenticate
    - fetch_data
    - process_data
    - save_result
```

**Python:**

```python
from evaldeck.graders import ToolOrderGrader

grader = ToolOrderGrader(
    expected_order=["authenticate", "fetch_data", "process_data", "save_result"]
)
```

**Behavior:**

- Tools must appear in the specified sequence
- Other tools may be called in between
- Each tool in the sequence must appear after the previous one

**Example:**

```
Expected order: [A, B, C]
Actual calls:   [A, X, B, Y, C]  → PASS (A→B→C preserved)
Actual calls:   [A, C, B]        → FAIL (C before B)
```

---

### MaxStepsGrader

Enforces a maximum step count (counts all trace steps including internal framework steps).

**YAML:**

```yaml
expected:
  max_steps: 10
```

**Python:**

```python
from evaldeck.graders import MaxStepsGrader

grader = MaxStepsGrader(max_steps=10)
```

**Note:** When using OpenTelemetry instrumentation, step counts include all captured spans (LLM calls, parsing, internal framework steps). For more intuitive limits based on actual tool calls, use `MaxToolCallsGrader` instead.

---

### MaxToolCallsGrader

Enforces a maximum number of tool calls.

**YAML:**

```yaml
expected:
  max_tool_calls: 5
```

**Python:**

```python
from evaldeck.graders import MaxToolCallsGrader

grader = MaxToolCallsGrader(max_tool_calls=5)
```

**Use case:** Ensure agent efficiency by limiting actual tool invocations. Unlike `max_steps`, this only counts tool calls, not internal framework steps captured by OpenTelemetry.

---

### MaxLLMCallsGrader

Enforces a maximum number of LLM calls.

**YAML:**

```yaml
expected:
  max_llm_calls: 3
```

**Python:**

```python
from evaldeck.graders import MaxLLMCallsGrader

grader = MaxLLMCallsGrader(max_llm_calls=3)
```

**Use case:** Control costs and latency by limiting how many times the agent calls the LLM. Useful for ensuring the agent doesn't get stuck in reasoning loops.

---

### TaskCompletedGrader

Checks that the agent completed successfully.

**YAML:**

```yaml
expected:
  task_completed: true
```

**Python:**

```python
from evaldeck.graders import TaskCompletedGrader

grader = TaskCompletedGrader()
```

**Behavior:** Checks `trace.status == TraceStatus.SUCCESS`

## Combining Graders

All `expected` conditions are combined with AND logic:

```yaml
expected:
  tools_called: [search, book]     # AND
  output_contains: [confirmed]     # AND
  max_steps: 5                     # All must pass
```

## Programmatic Usage

Use graders directly in Python:

```python
from evaldeck import Trace, EvalCase
from evaldeck.graders import ToolCalledGrader, ContainsGrader

# Create graders
tool_grader = ToolCalledGrader(required=["search", "book"])
output_grader = ContainsGrader(values=["confirmed"])

# Grade a trace
trace = Trace(...)
test_case = EvalCase(...)

result1 = tool_grader.grade(trace, test_case)
result2 = output_grader.grade(trace, test_case)

print(f"Tools: {result1.status}")  # PASS or FAIL
print(f"Output: {result2.status}")
```

## Best Practices

### 1. Start with Tool Checks

Tool selection is often the first point of failure:

```yaml
expected:
  tools_called: [required_tool]
```

### 2. Add Negative Checks

Prevent dangerous or irrelevant actions:

```yaml
expected:
  tools_not_called: [dangerous_tool]
  output_not_contains: [error, failed]
```

### 3. Set Reasonable Limits

Prevent runaway executions:

```yaml
expected:
  max_steps: 10
```

### 4. Use Regex for Structured Output

Validate format without exact matching:

```yaml
expected:
  output_matches: "Reference: [A-Z0-9]{8}"
```
