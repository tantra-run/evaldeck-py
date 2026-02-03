"""Built-in metrics for agent evaluation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from evaldeck.metrics.base import BaseMetric
from evaldeck.results import MetricResult

if TYPE_CHECKING:
    from evaldeck.test_case import EvalCase
    from evaldeck.trace import Trace


class StepCountMetric(BaseMetric):
    """Count total number of steps in the trace."""

    name = "step_count"
    unit = "steps"

    def calculate(self, trace: Trace, test_case: EvalCase | None = None) -> MetricResult:
        return MetricResult(
            metric_name=self.name,
            value=float(trace.step_count),
            unit=self.unit,
        )


class TokenUsageMetric(BaseMetric):
    """Total token usage across all LLM calls."""

    name = "token_usage"
    unit = "tokens"

    def calculate(self, trace: Trace, test_case: EvalCase | None = None) -> MetricResult:
        return MetricResult(
            metric_name=self.name,
            value=float(trace.total_tokens),
            unit=self.unit,
            details={
                "llm_calls": len(trace.llm_calls),
            },
        )


class ToolCallCountMetric(BaseMetric):
    """Count number of tool calls."""

    name = "tool_call_count"
    unit = "calls"

    def calculate(self, trace: Trace, test_case: EvalCase | None = None) -> MetricResult:
        return MetricResult(
            metric_name=self.name,
            value=float(len(trace.tool_calls)),
            unit=self.unit,
            details={
                "tools": trace.tools_called,
            },
        )


class DurationMetric(BaseMetric):
    """Total execution duration."""

    name = "duration"
    unit = "ms"

    def calculate(self, trace: Trace, test_case: EvalCase | None = None) -> MetricResult:
        duration = trace.duration_ms or 0.0
        return MetricResult(
            metric_name=self.name,
            value=duration,
            unit=self.unit,
        )


class ToolDiversityMetric(BaseMetric):
    """Measure diversity of tools used (unique tools / total calls)."""

    name = "tool_diversity"
    unit = "ratio"

    def calculate(self, trace: Trace, test_case: EvalCase | None = None) -> MetricResult:
        tool_calls = trace.tool_calls
        if not tool_calls:
            return MetricResult(
                metric_name=self.name,
                value=0.0,
                unit=self.unit,
            )

        unique_tools = len(set(trace.tools_called))
        total_calls = len(tool_calls)
        diversity = unique_tools / total_calls

        return MetricResult(
            metric_name=self.name,
            value=diversity,
            unit=self.unit,
            details={
                "unique_tools": unique_tools,
                "total_calls": total_calls,
            },
        )


class StepEfficiencyMetric(BaseMetric):
    """Measure step efficiency compared to expected max steps.

    Returns 1.0 if within expected steps, <1.0 if exceeded.
    """

    name = "step_efficiency"
    unit = "ratio"

    def calculate(self, trace: Trace, test_case: EvalCase | None = None) -> MetricResult:
        actual_steps = trace.step_count

        # Get expected max from test case
        max_steps = None
        if test_case and test_case.expected.max_steps:
            max_steps = test_case.expected.max_steps

        if max_steps is None:
            # No baseline, just return step count as negative efficiency
            return MetricResult(
                metric_name=self.name,
                value=1.0,
                unit=self.unit,
                details={
                    "actual_steps": actual_steps,
                    "max_steps": None,
                },
            )

        # Calculate efficiency (1.0 = at or under budget, <1.0 = over budget)
        if actual_steps <= max_steps:
            efficiency = 1.0
        else:
            efficiency = max_steps / actual_steps

        return MetricResult(
            metric_name=self.name,
            value=efficiency,
            unit=self.unit,
            details={
                "actual_steps": actual_steps,
                "max_steps": max_steps,
            },
        )


class LLMCallCountMetric(BaseMetric):
    """Count number of LLM calls."""

    name = "llm_call_count"
    unit = "calls"

    def calculate(self, trace: Trace, test_case: EvalCase | None = None) -> MetricResult:
        return MetricResult(
            metric_name=self.name,
            value=float(len(trace.llm_calls)),
            unit=self.unit,
        )


class ErrorRateMetric(BaseMetric):
    """Calculate error rate across steps."""

    name = "error_rate"
    unit = "ratio"

    def calculate(self, trace: Trace, test_case: EvalCase | None = None) -> MetricResult:
        from evaldeck.trace import StepStatus

        if not trace.steps:
            return MetricResult(
                metric_name=self.name,
                value=0.0,
                unit=self.unit,
            )

        error_count = sum(1 for s in trace.steps if s.status == StepStatus.FAILURE)
        error_rate = error_count / len(trace.steps)

        return MetricResult(
            metric_name=self.name,
            value=error_rate,
            unit=self.unit,
            details={
                "error_count": error_count,
                "total_steps": len(trace.steps),
            },
        )
