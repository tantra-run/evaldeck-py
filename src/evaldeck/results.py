"""Evaluation result data models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class GradeStatus(str, Enum):
    """Status of a grading result."""

    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIP = "skip"


class GradeResult(BaseModel):
    """Result from a single grader."""

    grader_name: str
    status: GradeStatus
    score: float | None = None  # 0.0 to 1.0
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)

    # For debugging
    expected: Any | None = None
    actual: Any | None = None

    @property
    def passed(self) -> bool:
        """Check if this grade passed."""
        return self.status == GradeStatus.PASS

    @classmethod
    def passed_result(
        cls, grader_name: str, message: str | None = None, **kwargs: Any
    ) -> GradeResult:
        """Create a passing result."""
        return cls(grader_name=grader_name, status=GradeStatus.PASS, message=message, **kwargs)

    @classmethod
    def failed_result(
        cls,
        grader_name: str,
        message: str,
        expected: Any = None,
        actual: Any = None,
        **kwargs: Any,
    ) -> GradeResult:
        """Create a failing result."""
        return cls(
            grader_name=grader_name,
            status=GradeStatus.FAIL,
            message=message,
            expected=expected,
            actual=actual,
            **kwargs,
        )

    @classmethod
    def error_result(cls, grader_name: str, message: str, **kwargs: Any) -> GradeResult:
        """Create an error result."""
        return cls(grader_name=grader_name, status=GradeStatus.ERROR, message=message, **kwargs)


class MetricResult(BaseModel):
    """Result from a metric calculation."""

    metric_name: str
    value: float
    unit: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    """Complete result of evaluating a single test case."""

    test_case_name: str
    status: GradeStatus
    grades: list[GradeResult] = Field(default_factory=list)
    metrics: list[MetricResult] = Field(default_factory=list)

    # Execution info
    duration_ms: float | None = None
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None

    # For debugging
    trace_id: str | None = None
    error: str | None = None

    @property
    def passed(self) -> bool:
        """Check if the evaluation passed."""
        return self.status == GradeStatus.PASS

    @property
    def failed_grades(self) -> list[GradeResult]:
        """Get all failed grades."""
        return [g for g in self.grades if g.status == GradeStatus.FAIL]

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate across all grades."""
        if not self.grades:
            return 0.0
        passed = sum(1 for g in self.grades if g.passed)
        return passed / len(self.grades)

    def add_grade(self, grade: GradeResult) -> None:
        """Add a grade result."""
        self.grades.append(grade)
        # Update overall status
        if grade.status == GradeStatus.ERROR:
            self.status = GradeStatus.ERROR
        elif grade.status == GradeStatus.FAIL and self.status != GradeStatus.ERROR:
            self.status = GradeStatus.FAIL

    def add_metric(self, metric: MetricResult) -> None:
        """Add a metric result."""
        self.metrics.append(metric)


class SuiteResult(BaseModel):
    """Result of evaluating a test suite."""

    suite_name: str
    results: list[EvaluationResult] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None

    @property
    def total(self) -> int:
        """Total number of test cases."""
        return len(self.results)

    @property
    def passed(self) -> int:
        """Number of passed test cases."""
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        """Number of failed test cases."""
        return sum(1 for r in self.results if r.status == GradeStatus.FAIL)

    @property
    def errors(self) -> int:
        """Number of errored test cases."""
        return sum(1 for r in self.results if r.status == GradeStatus.ERROR)

    @property
    def pass_rate(self) -> float:
        """Overall pass rate."""
        if not self.results:
            return 0.0
        return self.passed / self.total

    @property
    def duration_ms(self) -> float:
        """Total duration in milliseconds."""
        return sum(r.duration_ms or 0 for r in self.results)

    def add_result(self, result: EvaluationResult) -> None:
        """Add an evaluation result."""
        self.results.append(result)


class RunResult(BaseModel):
    """Result of a complete evaluation run (multiple suites)."""

    suites: list[SuiteResult] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
    config: dict[str, Any] = Field(default_factory=dict)

    @property
    def total(self) -> int:
        """Total test cases across all suites."""
        return sum(s.total for s in self.suites)

    @property
    def passed(self) -> int:
        """Total passed across all suites."""
        return sum(s.passed for s in self.suites)

    @property
    def failed(self) -> int:
        """Total failed across all suites."""
        return sum(s.failed for s in self.suites)

    @property
    def pass_rate(self) -> float:
        """Overall pass rate."""
        if self.total == 0:
            return 0.0
        return self.passed / self.total

    @property
    def all_passed(self) -> bool:
        """Check if all tests passed."""
        return self.passed == self.total

    def add_suite(self, suite: SuiteResult) -> None:
        """Add a suite result."""
        self.suites.append(suite)
