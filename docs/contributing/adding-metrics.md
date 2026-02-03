# Adding Metrics

Create custom metrics to measure agent behavior.

## Metric Interface

All metrics inherit from `BaseMetric`:

```python
from abc import ABC, abstractmethod
from evaldeck.trace import Trace
from evaldeck.test_case import EvalCase
from evaldeck.results import MetricResult

class BaseMetric(ABC):
    """Base class for all metrics."""

    name: str = "base"

    @abstractmethod
    def calculate(self, trace: Trace, test_case: EvalCase) -> MetricResult:
        """Calculate the metric value."""
        pass
```

## Creating a Metric

### Step 1: Define the Class

```python
# src/evaldeck/metrics/custom.py
from evaldeck.metrics.base import BaseMetric
from evaldeck.results import MetricResult


class AverageStepDurationMetric(BaseMetric):
    """Calculate average duration per step."""

    name = "avg_step_duration"

    def calculate(self, trace: Trace, test_case: EvalCase) -> MetricResult:
        if not trace.steps:
            return MetricResult(
                metric_name=self.name,
                value=0.0,
                unit="ms"
            )

        total_duration = sum(
            step.duration_ms or 0
            for step in trace.steps
        )
        avg = total_duration / len(trace.steps)

        return MetricResult(
            metric_name=self.name,
            value=round(avg, 2),
            unit="ms",
            details={
                "total_duration_ms": total_duration,
                "step_count": len(trace.steps),
            }
        )
```

### Step 2: Export the Metric

```python
# src/evaldeck/metrics/__init__.py
from evaldeck.metrics.custom import AverageStepDurationMetric

__all__ = [
    # ... existing exports ...
    "AverageStepDurationMetric",
]
```

### Step 3: Add Tests

```python
# tests/test_metrics.py
import pytest
from evaldeck import Trace, Step
from evaldeck.metrics import AverageStepDurationMetric


class TestAverageStepDurationMetric:
    def test_calculates_average(self):
        trace = Trace(input="test")
        trace.add_step(Step.tool_call("a", {}, {}, duration_ms=100))
        trace.add_step(Step.tool_call("b", {}, {}, duration_ms=200))
        trace.add_step(Step.tool_call("c", {}, {}, duration_ms=300))

        metric = AverageStepDurationMetric()
        result = metric.calculate(trace, mock_test_case)

        assert result.value == 200.0
        assert result.unit == "ms"

    def test_handles_empty_trace(self):
        trace = Trace(input="test")

        metric = AverageStepDurationMetric()
        result = metric.calculate(trace, mock_test_case)

        assert result.value == 0.0

    def test_handles_missing_duration(self):
        trace = Trace(input="test")
        trace.add_step(Step.tool_call("a", {}, {}))  # No duration

        metric = AverageStepDurationMetric()
        result = metric.calculate(trace, mock_test_case)

        assert result.value == 0.0
```

## MetricResult

Return a `MetricResult` with:

```python
MetricResult(
    metric_name="my_metric",
    value=42.5,                    # The measurement
    unit="ms",                     # Optional unit
    details={"extra": "info"}      # Optional details
)
```

## More Examples

### Token Cost Metric

```python
class TokenCostMetric(BaseMetric):
    """Estimate cost based on token usage."""

    name = "token_cost"

    # Prices per 1M tokens (example rates)
    PRICES = {
        "gpt-4o": {"input": 5.0, "output": 15.0},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "claude-3-opus": {"input": 15.0, "output": 75.0},
        "claude-3-sonnet": {"input": 3.0, "output": 15.0},
    }

    def calculate(self, trace: Trace, test_case: EvalCase) -> MetricResult:
        total_cost = 0.0
        details = {}

        for step in trace.llm_calls:
            if step.tokens and step.model:
                model = step.model.lower()

                # Find matching price
                prices = None
                for model_key, model_prices in self.PRICES.items():
                    if model_key in model:
                        prices = model_prices
                        break

                if prices:
                    input_cost = (step.tokens.prompt_tokens / 1_000_000) * prices["input"]
                    output_cost = (step.tokens.completion_tokens / 1_000_000) * prices["output"]
                    step_cost = input_cost + output_cost
                    total_cost += step_cost

                    details[step.id] = {
                        "model": step.model,
                        "input_tokens": step.tokens.prompt_tokens,
                        "output_tokens": step.tokens.completion_tokens,
                        "cost": round(step_cost, 6),
                    }

        return MetricResult(
            metric_name=self.name,
            value=round(total_cost, 6),
            unit="USD",
            details=details
        )
```

### Retry Rate Metric

```python
class RetryRateMetric(BaseMetric):
    """Calculate the rate of repeated tool calls."""

    name = "retry_rate"

    def calculate(self, trace: Trace, test_case: EvalCase) -> MetricResult:
        tool_calls = [step.tool_name for step in trace.tool_calls]

        if not tool_calls:
            return MetricResult(
                metric_name=self.name,
                value=0.0,
                details={"message": "No tool calls"}
            )

        unique_tools = set(tool_calls)
        total_calls = len(tool_calls)
        unique_count = len(unique_tools)

        # Retry rate = 1 - (unique / total)
        # 0.0 = no retries, 0.5 = half are retries
        retry_rate = 1 - (unique_count / total_calls)

        return MetricResult(
            metric_name=self.name,
            value=round(retry_rate, 3),
            details={
                "total_calls": total_calls,
                "unique_tools": unique_count,
                "repeated_calls": total_calls - unique_count,
            }
        )
```

### Reasoning Depth Metric

```python
class ReasoningDepthMetric(BaseMetric):
    """Measure the depth of agent reasoning."""

    name = "reasoning_depth"

    def calculate(self, trace: Trace, test_case: EvalCase) -> MetricResult:
        reasoning_steps = [
            step for step in trace.steps
            if step.type.value == "reasoning"
        ]

        if not reasoning_steps:
            return MetricResult(
                metric_name=self.name,
                value=0,
                details={"message": "No reasoning steps"}
            )

        # Calculate metrics
        count = len(reasoning_steps)
        total_length = sum(
            len(step.reasoning_text or "")
            for step in reasoning_steps
        )
        avg_length = total_length / count

        return MetricResult(
            metric_name=self.name,
            value=count,
            details={
                "reasoning_step_count": count,
                "total_characters": total_length,
                "avg_characters": round(avg_length, 1),
            }
        )
```

## Using Custom Metrics

### Programmatically

```python
from evaldeck import Evaluator
from my_metrics import TokenCostMetric, RetryRateMetric

evaluator = Evaluator()
evaluator.add_metric(TokenCostMetric())
evaluator.add_metric(RetryRateMetric())

result = evaluator.evaluate(trace, test_case)

for metric in result.metrics:
    print(f"{metric.metric_name}: {metric.value} {metric.unit or ''}")
```

### In Evaluator Constructor

```python
evaluator = Evaluator(
    metrics=[
        StepCountMetric(),
        TokenUsageMetric(),
        TokenCostMetric(),
        RetryRateMetric(),
    ]
)
```

## Best Practices

1. **Return sensible defaults** for empty traces
2. **Include details** for debugging
3. **Use appropriate units** (ms, tokens, USD, etc.)
4. **Handle missing data** gracefully
5. **Round values** appropriately
