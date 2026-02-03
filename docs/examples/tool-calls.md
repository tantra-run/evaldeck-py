# Testing Tool Calls

Verify that your agent calls the right tools with the right arguments.

## Check Required Tools

Ensure specific tools are called:

```yaml
# tests/evals/booking_tools.yaml
name: booking_requires_search_and_book
input: "Book a flight to Paris"

expected:
  tools_called:
    - search_flights
    - book_flight
```

```python
from evaldeck import EvalCase, ExpectedBehavior

test = EvalCase(
    name="booking_requires_search_and_book",
    input="Book a flight to Paris",
    expected=ExpectedBehavior(
        tools_called=["search_flights", "book_flight"]
    )
)
```

## Check Forbidden Tools

Ensure dangerous tools aren't called:

```yaml
name: booking_safe_tools_only
input: "Book a flight to Paris"

expected:
  tools_not_called:
    - delete_account
    - admin_override
    - drop_database
```

## Check Tool Order

Ensure tools are called in sequence:

```yaml
name: booking_correct_sequence
input: "Book a flight to Paris"

expected:
  tool_call_order:
    - search_flights    # Must search first
    - select_flight     # Then select
    - book_flight       # Then book
    - send_confirmation # Finally confirm
```

The agent can call other tools in between, but these must appear in this order.

## Validate Tool Arguments

Use a custom grader to check tool arguments:

```python
from evaldeck import Trace, EvalCase
from evaldeck.results import GradeResult

def validate_search_args(trace: Trace, test_case: EvalCase) -> GradeResult:
    """Validate that search_flights was called with correct arguments."""

    for step in trace.tool_calls:
        if step.tool_name == "search_flights":
            args = step.tool_args or {}

            # Check required fields
            if "destination" not in args:
                return GradeResult.failed_result(
                    "validate_search_args",
                    "search_flights missing 'destination' argument",
                    expected="destination field",
                    actual=str(args)
                )

            # Validate format
            dest = args.get("destination", "")
            if len(dest) != 3 or not dest.isupper():
                return GradeResult.failed_result(
                    "validate_search_args",
                    f"Invalid airport code: {dest}",
                    expected="3-letter uppercase code (e.g., 'LAX')",
                    actual=dest
                )

            return GradeResult.passed_result(
                "validate_search_args",
                "search_flights arguments valid"
            )

    return GradeResult.failed_result(
        "validate_search_args",
        "search_flights was not called"
    )
```

Reference in YAML:

```yaml
name: booking_valid_arguments
input: "Book a flight to LAX"

graders:
  - type: code
    module: my_graders
    function: validate_search_args
```

## Check Tool Results

Verify the agent handles tool results correctly:

```python
def check_handles_no_results(trace: Trace, test_case: EvalCase) -> GradeResult:
    """Verify agent handles empty search results gracefully."""

    for step in trace.tool_calls:
        if step.tool_name == "search_flights":
            result = step.tool_result or {}
            flights = result.get("flights", [])

            if not flights:
                # Search returned no results - check agent handled it
                if "no flights" in (trace.output or "").lower():
                    return GradeResult.passed_result(
                        "check_handles_no_results",
                        "Agent correctly reported no flights found"
                    )
                else:
                    return GradeResult.failed_result(
                        "check_handles_no_results",
                        "Agent didn't inform user about no flights",
                        expected="Message about no flights",
                        actual=trace.output
                    )

    return GradeResult.passed_result(
        "check_handles_no_results",
        "Flights were found, no empty handling needed"
    )
```

## Complete Example

```python
from evaldeck import Trace, Step, EvalCase, ExpectedBehavior, Evaluator
from evaldeck.graders import CustomGrader
from evaldeck.results import GradeResult

# Simulate an agent that makes tool calls
def booking_agent(input: str) -> Trace:
    trace = Trace(input=input)

    trace.add_step(Step.tool_call(
        tool_name="search_flights",
        tool_args={"destination": "CDG", "date": "2024-06-01"},
        tool_result={"flights": [{"id": "AF123", "price": 599}]}
    ))

    trace.add_step(Step.tool_call(
        tool_name="book_flight",
        tool_args={"flight_id": "AF123", "passenger": "John Doe"},
        tool_result={"confirmation": "ABC123"}
    ))

    trace.complete(output="Booked flight AF123 to Paris. Confirmation: ABC123")
    return trace


# Define test with tool expectations
test = EvalCase(
    name="paris_booking",
    input="Book a flight to Paris",
    expected=ExpectedBehavior(
        tools_called=["search_flights", "book_flight"],
        tools_not_called=["cancel_booking", "refund"],
        tool_call_order=["search_flights", "book_flight"],
    )
)

# Add custom argument validation
def validate_booking_args(trace, test_case):
    for step in trace.tool_calls:
        if step.tool_name == "book_flight":
            args = step.tool_args or {}
            if "flight_id" not in args:
                return GradeResult.failed_result(
                    "validate_booking_args",
                    "book_flight missing flight_id"
                )
            if "passenger" not in args:
                return GradeResult.failed_result(
                    "validate_booking_args",
                    "book_flight missing passenger"
                )
    return GradeResult.passed_result("validate_booking_args", "Arguments valid")


# Evaluate
custom_grader = CustomGrader(func=validate_booking_args)
evaluator = Evaluator(graders=[custom_grader])

trace = booking_agent(test.input)
result = evaluator.evaluate(trace, test)

print(f"Passed: {result.passed}")
for grade in result.grades:
    print(f"  {grade.grader_name}: {grade.status}")
```

Output:

```
Passed: True
  tool_called: PASS
  tool_not_called: PASS
  tool_order: PASS
  validate_booking_args: PASS
```
