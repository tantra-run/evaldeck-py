"""Pytest configuration and fixtures."""

import pytest

from evaldeck import EvalCase, ExpectedBehavior, Step, Trace, Turn


@pytest.fixture
def simple_trace() -> Trace:
    """A simple trace for testing."""
    trace = Trace(
        input="Book a flight from NYC to LA",
        output="Your flight has been booked. Confirmation: ABC123",
    )
    trace.add_step(
        Step.tool_call(
            tool_name="search_flights",
            tool_args={"from": "NYC", "to": "LA"},
            tool_result=[{"flight_id": "AA123", "price": 299}],
        )
    )
    trace.add_step(
        Step.tool_call(
            tool_name="book_flight",
            tool_args={"flight_id": "AA123"},
            tool_result={"confirmation": "ABC123"},
        )
    )
    return trace


@pytest.fixture
def simple_test_case() -> EvalCase:
    """A simple test case for testing."""
    return EvalCase(
        name="book_flight_basic",
        turns=[
            Turn(
                user="Book a flight from NYC to LA",
                expected=ExpectedBehavior(
                    tools_called=["search_flights", "book_flight"],
                    output_contains=["booked", "confirmation"],
                    max_steps=5,
                ),
            )
        ],
    )


@pytest.fixture
def failing_trace() -> Trace:
    """A trace that should fail evaluation."""
    return Trace(
        input="Book a flight from NYC to LA",
        output="Sorry, I couldn't complete the booking.",
    )
