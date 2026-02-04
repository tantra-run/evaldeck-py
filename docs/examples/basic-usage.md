# Basic Usage

This example demonstrates the core Evaldeck workflow.

## Step 1: Create a Trace

A trace captures the agent's execution:

```python
from evaldeck import Trace, Step, TokenUsage

# Start a trace
trace = Trace(
    input="Book a flight from NYC to LA on March 15",
    framework="custom",
    agent_name="BookingAgent"
)

# Add LLM reasoning step
trace.add_step(Step.llm_call(
    model="gpt-4o-mini",
    input="Parse user request for booking details",
    output='{"from": "NYC", "to": "LA", "date": "March 15"}',
    token_usage=TokenUsage(prompt_tokens=50, completion_tokens=30, total_tokens=80)
))

# Add tool call step
trace.add_step(Step.tool_call(
    tool_name="search_flights",
    tool_args={"from": "NYC", "to": "LA", "date": "2024-03-15"},
    tool_result={
        "flights": [
            {"id": "AA123", "price": 299, "departure": "08:00"},
            {"id": "UA456", "price": 349, "departure": "10:30"}
        ]
    }
))

# Add another tool call
trace.add_step(Step.tool_call(
    tool_name="book_flight",
    tool_args={"flight_id": "AA123"},
    tool_result={"confirmation": "ABC123", "status": "confirmed"}
))

# Complete the trace
trace.complete(output="Your flight AA123 from NYC to LA on March 15 is booked. Confirmation: ABC123")
```

## Step 2: Define a Test Case

### In Python

```python
from evaldeck import EvalCase, ExpectedBehavior, Turn

test_case = EvalCase(
    name="book_flight_basic",
    description="Book a simple one-way flight",
    turns=[
        Turn(
            user="Book a flight from NYC to LA on March 15",
            expected=ExpectedBehavior(
                tools_called=["search_flights", "book_flight"],
                tools_not_called=["cancel_booking"],
                output_contains=["confirmation", "ABC123"],
                max_steps=5,
                task_completed=True
            ),
        )
    ],
    tags=["booking", "critical"]
)
```

### In YAML

```yaml
# tests/evals/book_flight_basic.yaml
name: book_flight_basic
description: Book a simple one-way flight
turns:
  - user: "Book a flight from NYC to LA on March 15"
    expected:
      tools_called:
        - search_flights
        - book_flight
      tools_not_called:
        - cancel_booking
      output_contains:
        - "confirmation"
        - "ABC123"
      max_steps: 5
      task_completed: true

tags:
  - booking
  - critical
```

## Step 3: Evaluate

```python
from evaldeck import Evaluator

evaluator = Evaluator()
result = evaluator.evaluate(trace, test_case)

# Check results
print(f"Test: {result.test_case_name}")
print(f"Passed: {result.passed}")
print(f"Duration: {result.duration_ms:.0f}ms")

# Show grades
for grade in result.grades:
    status = "PASS" if grade.passed else "FAIL"
    print(f"  {grade.grader_name}: {status}")
    if not grade.passed:
        print(f"    Expected: {grade.expected}")
        print(f"    Actual: {grade.actual}")

# Show metrics
for metric in result.metrics:
    print(f"  {metric.metric_name}: {metric.value} {metric.unit or ''}")
```

Output:

```
Test: book_flight_basic
Passed: True
Duration: 5ms
  tool_called: PASS
  tool_not_called: PASS
  contains: PASS
  max_steps: PASS
  task_completed: PASS
  step_count: 3
  token_usage: 80 tokens
  tool_call_count: 2
```

## Step 4: Run Multiple Tests

```python
from evaldeck import EvalSuite

# Load from directory
suite = EvalSuite.from_directory("tests/evals")

# Or create programmatically
suite = EvalSuite(
    name="booking_tests",
    test_cases=[test_case1, test_case2, test_case3]
)

# Run all tests
def run_agent(input: str) -> Trace:
    # Your agent implementation
    ...

suite_result = evaluator.evaluate_suite(suite, run_agent)

# Summary
print(f"\nResults: {suite_result.passed}/{suite_result.total} passed")
print(f"Pass rate: {suite_result.pass_rate:.1%}")
```

## Complete Script

```python
#!/usr/bin/env python3
"""Complete basic usage example."""

from evaldeck import (
    Trace, Step, TokenUsage,
    EvalCase, ExpectedBehavior, Turn,
    Evaluator
)


def simulate_booking_agent(input: str) -> Trace:
    """Simulated booking agent for demonstration."""
    trace = Trace(input=input)

    # Parse request
    trace.add_step(Step.llm_call(
        model="gpt-4o-mini",
        input=f"Parse: {input}",
        output='{"action": "book_flight", "from": "NYC", "to": "LA"}',
        token_usage=TokenUsage(prompt_tokens=30, completion_tokens=20, total_tokens=50)
    ))

    # Search flights
    trace.add_step(Step.tool_call(
        tool_name="search_flights",
        tool_args={"from": "NYC", "to": "LA"},
        tool_result={"flights": [{"id": "AA123", "price": 299}]}
    ))

    # Book flight
    trace.add_step(Step.tool_call(
        tool_name="book_flight",
        tool_args={"flight_id": "AA123"},
        tool_result={"confirmation": "ABC123"}
    ))

    # Generate response
    trace.add_step(Step.llm_call(
        model="gpt-4o-mini",
        input="Generate booking confirmation",
        output="Flight booked! Confirmation: ABC123",
        token_usage=TokenUsage(prompt_tokens=20, completion_tokens=15, total_tokens=35)
    ))

    trace.complete(output="Your flight is booked! Confirmation: ABC123")
    return trace


def main():
    # Define test
    test = EvalCase(
        name="booking_test",
        turns=[
            Turn(
                user="Book a flight from NYC to LA",
                expected=ExpectedBehavior(
                    tools_called=["search_flights", "book_flight"],
                    output_contains=["confirmation", "ABC123"],
                    max_steps=5
                )
            )
        ]
    )

    # Run agent
    trace = simulate_booking_agent(test.input)

    # Evaluate
    evaluator = Evaluator()
    result = evaluator.evaluate(trace, test)

    # Report
    print(f"Test: {result.test_case_name}")
    print(f"Status: {'PASS' if result.passed else 'FAIL'}")
    print(f"Steps: {trace.step_count}")
    print(f"Tokens: {trace.total_tokens}")

    for grade in result.grades:
        symbol = "✓" if grade.passed else "✗"
        print(f"  {symbol} {grade.grader_name}: {grade.message or grade.status}")


if __name__ == "__main__":
    main()
```
