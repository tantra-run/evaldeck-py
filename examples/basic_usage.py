"""Basic usage example for Evaldeck.

This example demonstrates how to:
1. Create a trace manually
2. Define a test case
3. Run evaluation
4. Inspect results
"""

from evaldeck import (
    EvalCase,
    Evaluator,
    ExpectedBehavior,
    Step,
    Trace,
)


def main() -> None:
    """Run basic evaluation example."""

    # 1. Create a trace (simulating agent execution)
    # In real usage, you'd capture this from your agent using the LangChain adapter
    trace = Trace(
        input="Book me a flight from New York to Los Angeles for next Friday",
        output="I've booked your flight from NYC to LA. Confirmation number: ABC123. "
        "Your flight departs at 10:00 AM and arrives at 1:00 PM local time.",
    )

    # Add the steps that the agent took
    trace.add_step(
        Step.llm_call(
            model="gpt-4",
            input="User wants to book a flight from NYC to LA for next Friday",
            output="I'll search for available flights first.",
        )
    )

    trace.add_step(
        Step.tool_call(
            tool_name="search_flights",
            tool_args={"from": "NYC", "to": "LA", "date": "2024-03-15"},
            tool_result=[
                {"flight_id": "AA123", "departure": "10:00", "arrival": "13:00", "price": 299},
                {"flight_id": "UA456", "departure": "14:00", "arrival": "17:00", "price": 349},
            ],
        )
    )

    trace.add_step(
        Step.llm_call(
            model="gpt-4",
            input="Found 2 flights. AA123 at 10:00 AM for $299, UA456 at 2:00 PM for $349",
            output="I'll book the first option as it's cheaper and has a good time.",
        )
    )

    trace.add_step(
        Step.tool_call(
            tool_name="book_flight",
            tool_args={"flight_id": "AA123", "passenger": "user"},
            tool_result={"confirmation": "ABC123", "status": "confirmed"},
        )
    )

    # Mark trace as complete
    trace.complete(trace.output)

    # 2. Define test case
    test_case = EvalCase(
        name="book_flight_basic",
        description="Test that the agent can book a simple one-way flight",
        input="Book me a flight from New York to Los Angeles for next Friday",
        expected=ExpectedBehavior(
            # These tools must be called
            tools_called=["search_flights", "book_flight"],
            # These tools must NOT be called
            tools_not_called=["cancel_flight", "refund"],
            # Output must contain these strings
            output_contains=["confirmation", "ABC123"],
            # Must complete within this many steps
            max_steps=10,
            # Task must complete successfully
            task_completed=True,
        ),
    )

    # 3. Run evaluation
    evaluator = Evaluator()
    result = evaluator.evaluate(trace, test_case)

    # 4. Inspect results
    print("=" * 60)
    print(f"Test Case: {result.test_case_name}")
    print(f"Status: {'PASS' if result.passed else 'FAIL'}")
    print(f"Duration: {result.duration_ms:.2f}ms")
    print("=" * 60)

    print("\nGrades:")
    for grade in result.grades:
        icon = "✓" if grade.passed else "✗"
        print(f"  {icon} {grade.grader_name}: {grade.message}")

    print("\nMetrics:")
    for metric in result.metrics:
        print(f"  - {metric.metric_name}: {metric.value} {metric.unit or ''}")

    if not result.passed:
        print("\nFailed checks:")
        for grade in result.failed_grades:
            print(f"  - {grade.grader_name}")
            print(f"    Expected: {grade.expected}")
            print(f"    Actual: {grade.actual}")


if __name__ == "__main__":
    main()
