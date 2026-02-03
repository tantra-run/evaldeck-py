# Test Cases

Test cases define what your agent should do and how to evaluate it. This guide covers all test case options.

## Test Case Structure

A test case is a YAML file with the following structure:

```yaml
# Required fields
name: unique_test_name
input: "The input to send to your agent"

# Optional: what the agent should do
expected:
  tools_called: [...]
  output_contains: [...]
  # ... more expectations

# Optional: custom graders
graders:
  - type: llm
    prompt: "..."

# Optional: metadata
description: "What this test verifies"
timeout: 30
retries: 0
tags: [category, priority]
metadata:
  custom_key: value
```

## Required Fields

### name

Unique identifier for the test case:

```yaml
name: book_flight_basic
```

Best practices:

- Use snake_case
- Be descriptive: `book_flight_roundtrip` not `test1`
- Include the feature being tested

### input

The input string sent to your agent:

```yaml
input: "Book me a flight from NYC to LA on March 15th"
```

For multi-line inputs:

```yaml
input: |
  I need to book a flight.
  From: New York
  To: Los Angeles
  Date: March 15th
```

## Expected Behavior

The `expected` block defines what your agent should do.

### Tool Expectations

#### tools_called

Tools that must be called:

```yaml
expected:
  tools_called:
    - search_flights
    - book_flight
```

All listed tools must be called at least once. Order doesn't matter.

#### tools_not_called

Tools that must NOT be called:

```yaml
expected:
  tools_not_called:
    - delete_booking
    - admin_override
```

Useful for ensuring the agent doesn't take dangerous or irrelevant actions.

#### tool_call_order

Require tools to be called in a specific sequence:

```yaml
expected:
  tool_call_order:
    - search_flights
    - select_flight
    - book_flight
```

The agent may call other tools, but these must appear in this order.

### Output Expectations

#### output_contains

Strings that must appear in the output:

```yaml
expected:
  output_contains:
    - "confirmation"
    - "March 15"
    - "NYC to LA"
```

All strings must be present (case-insensitive by default).

#### output_not_contains

Strings that must NOT appear:

```yaml
expected:
  output_not_contains:
    - "error"
    - "failed"
    - "unable to"
```

#### output_equals

Exact output match:

```yaml
expected:
  output_equals: "Booking confirmed. Reference: ABC123"
```

Rarely used—most outputs have dynamic content.

#### output_matches

Regex pattern match:

```yaml
expected:
  output_matches: "Confirmation: [A-Z]{3}\\d{3}"
```

Useful for validating structured output formats.

### Execution Expectations

#### max_steps

Maximum allowed steps:

```yaml
expected:
  max_steps: 5
```

Ensures the agent doesn't take unnecessarily long paths.

#### min_steps

Minimum required steps:

```yaml
expected:
  min_steps: 2
```

Ensures the agent doesn't skip necessary steps.

#### task_completed

Whether the agent must complete successfully:

```yaml
expected:
  task_completed: true
```

Checks that `trace.status == "success"`.

## Custom Graders

Add custom evaluation logic with graders:

### LLM Grader

Use an LLM to evaluate the output:

```yaml
graders:
  - type: llm
    prompt: |
      Evaluate if this response is helpful and accurate.

      User asked: {{ input }}
      Agent responded: {{ output }}

      Consider:
      1. Is the information accurate?
      2. Is the response complete?
      3. Is the tone appropriate?

      Answer: PASS or FAIL
      Reason: <your explanation>
    model: gpt-4o-mini
```

Available template variables:

| Variable | Description |
|----------|-------------|
| `{{ input }}` | The test case input |
| `{{ output }}` | The agent's output |
| `{{ trace }}` | Full trace as JSON |
| `{{ task }}` | Test case description |

#### With Threshold

For scored evaluation:

```yaml
graders:
  - type: llm
    prompt: |
      Score this response from 1-5 for helpfulness.
      Response: {{ output }}

      SCORE: <number>
    model: gpt-4o-mini
    threshold: 4  # Must score 4 or higher
```

### Code Grader

Use a custom Python function:

```yaml
graders:
  - type: code
    module: my_graders
    function: custom_check
```

```python
# my_graders.py
from evaldeck import Trace, EvalCase, GradeResult

def custom_check(trace: Trace, test_case: EvalCase) -> GradeResult:
    # Custom logic
    if "important" in trace.output.lower():
        return GradeResult.passed_result("custom_check", "Found important content")
    return GradeResult.failed_result("custom_check", "Missing important content")
```

## Test Metadata

### description

Human-readable description:

```yaml
description: |
  Tests that the booking agent can handle a basic one-way flight
  booking with specified departure date.
```

### timeout

Override default timeout:

```yaml
timeout: 120  # 2 minutes for complex operations
```

### retries

Number of retries on failure:

```yaml
retries: 3  # Try up to 4 times total
```

### tags

Categorize tests for filtering:

```yaml
tags:
  - booking
  - critical
  - smoke
```

Run by tag:

```bash
evaldeck run --tag critical
evaldeck run --tag "booking,smoke"  # Multiple tags (OR)
```

### metadata

Custom key-value pairs:

```yaml
metadata:
  author: alice
  priority: high
  jira_ticket: AGENT-123
  created_date: 2024-01-15
```

## Multiple Test Cases Per File

Use YAML document separators for multiple tests:

```yaml
# tests/evals/booking.yaml

name: book_flight_basic
input: "Book a flight to LA"
expected:
  tools_called: [book_flight]
tags: [booking, simple]

---

name: book_flight_roundtrip
input: "Book a roundtrip flight to LA"
expected:
  tools_called: [book_flight]
  output_contains: ["roundtrip", "return"]
tags: [booking, complex]

---

name: book_flight_with_preferences
input: "Book a flight to LA, window seat, vegetarian meal"
expected:
  tools_called: [book_flight, set_preferences]
  output_contains: ["window", "vegetarian"]
tags: [booking, complex]
```

## Reference Data

### reference_output

Expected output for comparison:

```yaml
reference_output: |
  Your flight has been booked.
  Confirmation: ABC123
  Departure: March 15, 2024
```

Useful for LLM graders that compare against expected output.

### reference_tools

Expected tool call sequence with arguments:

```yaml
reference_tools:
  - name: search_flights
    args:
      from: NYC
      to: LA
      date: "2024-03-15"
  - name: book_flight
    args:
      flight_id: AA123
```

## Best Practices

### 1. One Behavior Per Test

```yaml
# Good: focused test
name: book_flight_validates_date
expected:
  output_not_contains: ["invalid date"]

# Avoid: testing too many things
name: book_flight_everything
expected:
  tools_called: [search, filter, sort, book, confirm, notify]
```

### 2. Use Descriptive Names

```yaml
# Good
name: booking_rejects_past_dates
name: search_handles_empty_results
name: auth_requires_valid_token

# Avoid
name: test1
name: booking_test
name: should_work
```

### 3. Tag Strategically

```yaml
# Recommended tag categories
tags:
  - critical       # Must pass for deploy
  - smoke          # Quick sanity checks
  - regression     # Full regression suite
  - booking        # Feature area
  - slow           # Long-running tests
```

### 4. Document Edge Cases

```yaml
name: booking_handles_sold_out_flight
description: |
  Verifies the agent gracefully handles the case where
  the selected flight becomes unavailable during booking.
input: "Book flight AA123"  # This flight is configured to be sold out
expected:
  output_contains: ["unavailable", "alternative"]
  tools_not_called: [charge_payment]  # Should not charge if sold out
```
