# Metrics

Metrics provide quantitative measurements about agent execution. Unlike graders (which return pass/fail), metrics return numeric values for analysis and tracking.

## Overview

| Metric | Description | Unit |
|--------|-------------|------|
| `step_count` | Total steps taken | count |
| `token_usage` | Total tokens consumed | tokens |
| `tool_call_count` | Number of tool calls | count |
| `llm_call_count` | Number of LLM calls | count |
| `duration` | Execution time | milliseconds |
| `tool_diversity` | Unique tools / total calls | ratio |
| `step_efficiency` | Steps used / max allowed | ratio |
| `error_rate` | Failed steps / total steps | ratio |

## Built-in Metrics

Evaldeck automatically calculates metrics for every evaluation.

### StepCountMetric

Total number of steps in the trace.

```python
from evaldeck.metrics import StepCountMetric

metric = StepCountMetric()
result = metric.calculate(trace, test_case)
print(result.value)  # e.g., 5
```

### TokenUsageMetric

Total tokens consumed across all LLM calls.

```python
from evaldeck.metrics import TokenUsageMetric

metric = TokenUsageMetric()
result = metric.calculate(trace, test_case)
print(result.value)  # e.g., 1250
print(result.details)  # {"prompt": 800, "completion": 450}
```

### ToolCallCountMetric

Number of tool calls made.

```python
from evaldeck.metrics import ToolCallCountMetric

metric = ToolCallCountMetric()
result = metric.calculate(trace, test_case)
print(result.value)  # e.g., 3
```

### LLMCallCountMetric

Number of LLM calls made.

```python
from evaldeck.metrics import LLMCallCountMetric

metric = LLMCallCountMetric()
result = metric.calculate(trace, test_case)
print(result.value)  # e.g., 4
```

### DurationMetric

Total execution time.

```python
from evaldeck.metrics import DurationMetric

metric = DurationMetric()
result = metric.calculate(trace, test_case)
print(result.value)  # e.g., 2500
print(result.unit)   # "ms"
```

### ToolDiversityMetric

Ratio of unique tools to total tool calls.

```python
from evaldeck.metrics import ToolDiversityMetric

metric = ToolDiversityMetric()
result = metric.calculate(trace, test_case)
print(result.value)  # e.g., 0.75 (3 unique tools / 4 total calls)
```

**Interpretation:**

- `1.0` = Every tool call was a different tool
- `0.5` = Half as many unique tools as calls (some repetition)
- `0.1` = Same tool called repeatedly

### StepEfficiencyMetric

Ratio of actual steps to maximum allowed.

```python
from evaldeck.metrics import StepEfficiencyMetric

metric = StepEfficiencyMetric()
result = metric.calculate(trace, test_case)
print(result.value)  # e.g., 0.6 (6 steps / 10 max)
```

**Interpretation:**

- `< 1.0` = Under budget (good)
- `= 1.0` = At maximum
- `> 1.0` = Over budget (if no max_steps, uses default of 10)

### ErrorRateMetric

Ratio of failed steps to total steps.

```python
from evaldeck.metrics import ErrorRateMetric

metric = ErrorRateMetric()
result = metric.calculate(trace, test_case)
print(result.value)  # e.g., 0.1 (1 failed step / 10 total)
```

## MetricResult Structure

Every metric returns a `MetricResult`:

```python
@dataclass
class MetricResult:
    metric_name: str     # Identifier
    value: float         # The measurement
    unit: str | None     # Optional unit (e.g., "ms", "tokens")
    details: dict | None # Additional breakdown
```

## Viewing Metrics

### CLI Verbose Output

```bash
evaldeck run --verbose
```

```
  ✓ book_flight_basic (1.2s)

    Metrics:
    ├─ step_count: 4
    ├─ token_usage: 1250 tokens
    │   └─ prompt: 800, completion: 450
    ├─ tool_call_count: 2
    ├─ llm_call_count: 2
    ├─ duration: 1200 ms
    ├─ tool_diversity: 1.0
    ├─ step_efficiency: 0.4
    └─ error_rate: 0.0
```

### JSON Output

```bash
evaldeck run --output json
```

```json
{
  "results": [
    {
      "test_case": "book_flight_basic",
      "metrics": [
        {"name": "step_count", "value": 4},
        {"name": "token_usage", "value": 1250, "unit": "tokens"},
        {"name": "tool_call_count", "value": 2},
        {"name": "duration", "value": 1200, "unit": "ms"}
      ]
    }
  ]
}
```

## Creating Custom Metrics

### Basic Custom Metric

```python
from evaldeck.metrics import BaseMetric
from evaldeck import Trace, EvalCase
from evaldeck.results import MetricResult

class AverageStepDuration(BaseMetric):
    """Calculate average duration per step."""

    def calculate(self, trace: Trace, test_case: EvalCase) -> MetricResult:
        if not trace.steps:
            return MetricResult(
                metric_name="avg_step_duration",
                value=0.0,
                unit="ms"
            )

        total_duration = sum(
            step.duration_ms or 0
            for step in trace.steps
        )
        avg = total_duration / len(trace.steps)

        return MetricResult(
            metric_name="avg_step_duration",
            value=round(avg, 2),
            unit="ms",
            details={
                "total_duration": total_duration,
                "step_count": len(trace.steps)
            }
        )
```

### Using Custom Metrics

```python
from evaldeck import Evaluator
from my_metrics import AverageStepDuration

evaluator = Evaluator()
evaluator.add_metric(AverageStepDuration())

result = evaluator.evaluate(trace, test_case)
for metric in result.metrics:
    print(f"{metric.metric_name}: {metric.value}")
```

## Metrics vs Graders

| Aspect | Metrics | Graders |
|--------|---------|---------|
| Output | Numeric value | Pass/Fail |
| Purpose | Measurement | Evaluation |
| Example | "Used 1250 tokens" | "Token budget exceeded" |
| Use case | Tracking, analysis | CI/CD gates |

### Combining Both

Use metrics for tracking, graders for pass/fail:

```python
# Metric: measure tokens
class TokenUsageMetric(BaseMetric):
    def calculate(self, trace, test_case):
        return MetricResult("token_usage", trace.total_tokens, "tokens")

# Grader: enforce limit
class TokenBudgetGrader(BaseGrader):
    def __init__(self, max_tokens):
        self.max_tokens = max_tokens

    def grade(self, trace, test_case):
        if trace.total_tokens <= self.max_tokens:
            return GradeResult.passed_result(...)
        return GradeResult.failed_result(...)
```

## Analyzing Metrics

### Aggregate Statistics

```python
from evaldeck import EvaluationRunner

runner = EvaluationRunner(config)
run_result = runner.run(suites, agent_func)

# Collect metrics across all tests
all_tokens = []
all_durations = []

for suite_result in run_result.suite_results:
    for eval_result in suite_result.results:
        for metric in eval_result.metrics:
            if metric.metric_name == "token_usage":
                all_tokens.append(metric.value)
            elif metric.metric_name == "duration":
                all_durations.append(metric.value)

print(f"Avg tokens: {sum(all_tokens) / len(all_tokens):.0f}")
print(f"Avg duration: {sum(all_durations) / len(all_durations):.0f}ms")
```

### Trend Analysis

Track metrics over time to detect regressions:

```bash
# Save results with timestamp
evaldeck run --output json --output-file results-$(date +%Y%m%d).json
```

Compare against baselines:

```python
import json

with open("results-baseline.json") as f:
    baseline = json.load(f)

with open("results-current.json") as f:
    current = json.load(f)

# Compare average token usage
baseline_tokens = [r["metrics"]["token_usage"] for r in baseline["results"]]
current_tokens = [r["metrics"]["token_usage"] for r in current["results"]]

change = (sum(current_tokens) - sum(baseline_tokens)) / sum(baseline_tokens) * 100
print(f"Token usage change: {change:+.1f}%")
```

## Best Practices

1. **Track metrics over time** - Detect performance regressions
2. **Set baselines** - Know what "normal" looks like
3. **Alert on anomalies** - Catch issues early
4. **Use metrics for optimization** - Find efficiency opportunities
5. **Correlate with graders** - Understand why tests fail
