# API Reference

Comprehensive documentation for Evaldeck's Python API, auto-generated from source code docstrings.

## Core Classes

| Class | Description |
|-------|-------------|
| [`Trace`](trace.md) | Complete execution record of an agent |
| [`Step`](step.md) | Single step in an execution trace |
| [`Evaluator`](evaluator.md) | Core evaluation engine |
| [`EvalCase`](evalcase.md) | Test case definition |

## Result Types

| Class | Description |
|-------|-------------|
| [`GradeResult`](grade-result.md) | Result from a single grader |
| [`EvaluationResult`](evaluation-result.md) | Complete evaluation of one test |

## Graders

| Class | Description |
|-------|-------------|
| [`BaseGrader`](graders/base.md) | Abstract base class for graders |
| [Code Graders](graders/code.md) | Deterministic graders |
| [LLM Graders](graders/llm.md) | Model-as-judge graders |

## Metrics

| Class | Description |
|-------|-------------|
| [Built-in Metrics](metrics.md) | Quantitative measurements |

## Configuration

| Class | Description |
|-------|-------------|
| [`EvaldeckConfig`](config.md) | Configuration loading |

## Quick Import Guide

```python
# Core classes
from evaldeck import (
    Trace,
    Step,
    Evaluator,
    EvalCase,
    EvalSuite,
    ExpectedBehavior,
)

# Result types
from evaldeck import (
    GradeResult,
    GradeStatus,
    MetricResult,
    EvaluationResult,
    SuiteResult,
    RunResult,
)

# Enums
from evaldeck import (
    StepType,
    StepStatus,
    TraceStatus,
    TokenUsage,
)

# Graders
from evaldeck.graders import (
    BaseGrader,
    ContainsGrader,
    ToolCalledGrader,
    LLMGrader,
)

# Metrics
from evaldeck.metrics import (
    BaseMetric,
    StepCountMetric,
    TokenUsageMetric,
)
```
