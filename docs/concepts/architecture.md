# Architecture Overview

This document explains how Evaldeck's components work together.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Evaldeck                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   CLI       │    │  Python API │    │   Config    │     │
│  │  evaldeck run │    │  Evaluator  │    │  YAML files │     │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘     │
│         │                  │                  │             │
│         └──────────────────┼──────────────────┘             │
│                            ▼                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │               Evaluation Engine                      │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐        │   │
│  │  │  Graders  │  │  Metrics  │  │  Results  │        │   │
│  │  └───────────┘  └───────────┘  └───────────┘        │   │
│  └─────────────────────────────────────────────────────┘   │
│                            ▲                                │
│         ┌──────────────────┼──────────────────┐             │
│         │                  │                  │             │
│  ┌──────┴──────┐    ┌──────┴──────┐    ┌──────┴──────┐     │
│  │   Trace     │    │  Test Case  │    │ Integrations│     │
│  │   Models    │    │   Models    │    │  LangChain  │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Component Overview

### Data Models

**Trace Models** (`trace.py`)

- `Trace` - Complete execution record
- `Step` - Single action (tool call, LLM call, etc.)
- `TokenUsage` - Token consumption tracking
- Enums: `StepType`, `StepStatus`, `TraceStatus`

**Test Case Models** (`test_case.py`)

- `EvalCase` - Single test definition
- `EvalSuite` - Collection of test cases
- `ExpectedBehavior` - What agent should do
- `GraderConfig` - Custom grader configuration

**Result Models** (`results.py`)

- `GradeResult` - Single grader output
- `MetricResult` - Single metric output
- `EvaluationResult` - Complete evaluation of one test
- `SuiteResult` - Results for a test suite
- `RunResult` - Results for entire run

### Evaluation Engine

**Evaluator** (`evaluator.py`)

- Core evaluation logic
- Builds graders from expectations
- Runs graders and collects results
- Calculates metrics

**EvaluationRunner** (`evaluator.py`)

- High-level orchestration
- Suite discovery
- Agent loading
- Result aggregation

### Graders

**Base** (`graders/base.py`)

- `BaseGrader` - Abstract base class

**Code-Based** (`graders/code.py`)

- `ContainsGrader`, `NotContainsGrader`
- `EqualsGrader`, `RegexGrader`
- `ToolCalledGrader`, `ToolNotCalledGrader`, `ToolOrderGrader`
- `MaxStepsGrader`, `TaskCompletedGrader`
- `CustomGrader`, `CompositeGrader`

**LLM-Based** (`graders/llm.py`)

- `LLMGrader` - Pass/fail with prompt
- `LLMRubricGrader` - Multi-criteria scoring

### Metrics

**Base** (`metrics/base.py`)

- `BaseMetric` - Abstract base class

**Built-in** (`metrics/builtin.py`)

- `StepCountMetric`, `TokenUsageMetric`
- `ToolCallCountMetric`, `LLMCallCountMetric`
- `DurationMetric`, `ToolDiversityMetric`
- `StepEfficiencyMetric`, `ErrorRateMetric`

### Interface Layer

**CLI** (`cli.py`)

- Click-based command interface
- `init`, `run` commands
- Output formatting (text, JSON, JUnit)

**Configuration** (`config.py`)

- YAML configuration loading
- Defaults and validation

## Data Flow

### Evaluation Flow

```
1. Load Configuration
   evaldeck.yaml → EvaldeckConfig

2. Discover Tests
   tests/evals/*.yaml → EvalSuite[]

3. Load Agent
   config.agent → agent_function

4. For each test case:
   a. Run agent
      test_case.input → agent_function → Trace

   b. Build graders
      test_case.expected → Grader[]

   c. Run graders
      Trace + TestCase → Grader[] → GradeResult[]

   d. Calculate metrics
      Trace → Metric[] → MetricResult[]

   e. Aggregate results
      GradeResult[] + MetricResult[] → EvaluationResult

5. Aggregate suite results
   EvaluationResult[] → SuiteResult → RunResult

6. Output results
   RunResult → text/JSON/JUnit
```

### Grading Flow

```
┌─────────────────────────────────────────────────────┐
│                    Grading                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ExpectedBehavior              Custom Graders       │
│  ┌─────────────────┐           ┌─────────────────┐  │
│  │ tools_called    │──┐        │ LLMGrader       │  │
│  │ output_contains │  │        │ CustomGrader    │  │
│  │ max_steps       │  │        └────────┬────────┘  │
│  └─────────────────┘  │                 │           │
│                       ▼                 │           │
│              ┌────────────────┐         │           │
│              │ Auto-build     │         │           │
│              │ Graders        │         │           │
│              └───────┬────────┘         │           │
│                      │                  │           │
│                      ▼                  ▼           │
│              ┌─────────────────────────────┐        │
│              │      Combined Graders       │        │
│              └──────────────┬──────────────┘        │
│                             │                       │
│                             ▼                       │
│              ┌─────────────────────────────┐        │
│              │     grade(trace, case)      │        │
│              └──────────────┬──────────────┘        │
│                             │                       │
│                             ▼                       │
│              ┌─────────────────────────────┐        │
│              │       GradeResult[]         │        │
│              └─────────────────────────────┘        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Extension Points

### Adding a New Grader

1. Inherit from `BaseGrader`
2. Implement `grade(trace, test_case) -> GradeResult`
3. Export from `evaldeck.graders`

```python
class MyGrader(BaseGrader):
    def grade(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        # Custom logic
        return GradeResult(...)
```

### Adding a New Metric

1. Inherit from `BaseMetric`
2. Implement `calculate(trace, test_case) -> MetricResult`
3. Export from `evaldeck.metrics`

```python
class MyMetric(BaseMetric):
    def calculate(self, trace: Trace, test_case: EvalCase) -> MetricResult:
        # Custom calculation
        return MetricResult(...)
```

### Adding a New Integration

The recommended approach is to use OpenTelemetry with OpenInference instrumentors. See `evaldeck.integrations.opentelemetry` for the implementation.

For frameworks with OpenInference support, no additional code is needed:

```python
from evaldeck.integrations import setup_otel_tracing
from openinference.instrumentation.langchain import LangChainInstrumentor

processor = setup_otel_tracing()
LangChainInstrumentor().instrument()

# Traces captured automatically
```

For custom frameworks without OpenTelemetry support, create an adapter that builds `Trace` objects:

```python
class MyFrameworkTracer:
    def __init__(self):
        self.trace = Trace(...)

    def on_event(self, event):
        self.trace.add_step(...)

    def get_trace(self) -> Trace:
        return self.trace
```

## Design Principles

### 1. Framework Agnostic

The `Trace` model is independent of any agent framework. Integrations convert framework-specific events to this common format.

### 2. Composable Graders

Graders are independent units that can be combined. Each grader checks one thing.

### 3. Separation of Concerns

- Models: Data structures
- Graders: Pass/fail logic
- Metrics: Measurements
- Evaluator: Orchestration
- CLI: User interface

### 4. YAML-First Configuration

Test cases and config use YAML for readability and version control friendliness.

### 5. Python API Parity

Everything available in YAML is also available programmatically.
