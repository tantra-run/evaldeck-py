"""Evaldeck - The evaluation framework for AI agents.

Evaldeck helps you answer one question: "Is my agent actually working?"

Basic usage:
    from evaldeck import Trace, Step, Evaluator, EvalCase

    # Create a trace (or capture with LangChain adapter)
    trace = Trace(
        input="Book a flight to NYC",
        steps=[
            Step.tool_call("search_flights", {"to": "NYC"}),
            Step.tool_call("book_flight", {"flight_id": "123"}),
        ],
        output="Booked flight 123 to NYC",
    )

    # Define test case
    test_case = EvalCase(
        name="book_flight",
        input="Book a flight to NYC",
        expected=ExpectedBehavior(
            tools_called=["search_flights", "book_flight"],
            output_contains=["booked"],
        ),
    )

    # Evaluate
    evaluator = Evaluator()
    result = evaluator.evaluate(trace, test_case)
    print(f"Passed: {result.passed}")
"""

from evaldeck.config import EvaldeckConfig
from evaldeck.evaluator import EvaluationRunner, Evaluator
from evaldeck.results import (
    EvaluationResult,
    GradeResult,
    GradeStatus,
    MetricResult,
    RunResult,
    SuiteResult,
)
from evaldeck.test_case import (
    EvalCase,
    EvalSuite,
    ExpectedBehavior,
    GraderConfig,
)
from evaldeck.trace import (
    Step,
    StepStatus,
    StepType,
    TokenUsage,
    Trace,
    TraceStatus,
)

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Trace
    "Trace",
    "Step",
    "StepType",
    "StepStatus",
    "TraceStatus",
    "TokenUsage",
    # Test Case
    "EvalCase",
    "EvalSuite",
    "ExpectedBehavior",
    "GraderConfig",
    # Results
    "GradeResult",
    "GradeStatus",
    "MetricResult",
    "EvaluationResult",
    "SuiteResult",
    "RunResult",
    # Evaluator
    "Evaluator",
    "EvaluationRunner",
    # Config
    "EvaldeckConfig",
]
