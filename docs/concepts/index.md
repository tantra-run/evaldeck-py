# Concepts

This section explains the core concepts behind Evaldeck and agent evaluation.

## Overview

Understanding these concepts will help you write better tests and debug evaluation failures:

| Concept | Description |
|---------|-------------|
| [Architecture](architecture.md) | How Evaldeck's components work together |
| [Traces & Steps](traces.md) | The execution record of an agent |
| [Evaluation Workflow](evaluation-workflow.md) | How evaluation proceeds |
| [Grading Strategies](grading-strategies.md) | Approaches to agent evaluation |

## The Problem Evaldeck Solves

Traditional LLM evaluation treats models as black boxes:

```
Input → Model → Output → Score
```

This works for simple Q&A but fails for agents because:

1. **Agents are multi-step**: A booking agent might search, filter, compare, and book
2. **Tool selection matters**: Calling the wrong tool causes cascading failures
3. **Efficiency matters**: 20 steps for a 3-step task wastes time and money
4. **Intermediate states matter**: Even with correct output, the path matters

## Evaldeck's Approach

Evaldeck captures the complete execution trace:

```
Input → [Step 1] → [Step 2] → ... → [Step N] → Output
              ↓         ↓              ↓
           Trace captures every step
```

Then evaluates the entire journey:

```
Trace + Test Case → Graders → Results
                       ↓
                   Metrics
```

## Key Concepts at a Glance

### Trace

A complete record of agent execution:

```python
Trace(
    input="Book a flight to NYC",
    steps=[
        Step(type=TOOL_CALL, tool_name="search_flights", ...),
        Step(type=LLM_CALL, model="gpt-4o-mini", ...),
        Step(type=TOOL_CALL, tool_name="book_flight", ...),
    ],
    output="Your flight is booked. Confirmation: ABC123",
    status=SUCCESS
)
```

### Step

A single action in the trace:

- **TOOL_CALL**: Agent called a tool
- **LLM_CALL**: Agent called an LLM
- **REASONING**: Agent's internal reasoning
- **HUMAN_INPUT**: Human-in-the-loop input

### Test Case

What the agent should do:

```yaml
name: book_flight
input: "Book a flight to NYC"
expected:
  tools_called: [search_flights, book_flight]
  output_contains: ["confirmation"]
  max_steps: 5
```

### Grader

Evaluates trace against expectations:

- **Code-based**: Deterministic checks (tool called, output contains)
- **LLM-based**: Model-as-judge for subjective criteria

### Metric

Quantitative measurements:

- Token usage
- Step count
- Duration
- Error rate

## The Evaluation Formula

```
Evaluation Result = Graders(Trace, Test Case) + Metrics(Trace)
```

An evaluation passes when all graders pass.

## Why This Matters

### Without Evaldeck

```
Agent output: "Your flight is booked"
Human review: "Looks good!" ✓
```

Problems:

- How do we know it actually booked?
- Did it call the right APIs?
- Was it efficient?
- Will it work next time?

### With Evaldeck

```
Trace shows:
  1. ✓ Called search_flights
  2. ✓ Called book_flight
  3. ✓ Confirmation in output
  4. ✓ Completed in 3 steps (under limit of 5)

Result: PASS
```

Benefits:

- Verifiable execution path
- Reproducible tests
- Automated CI/CD
- Regression detection
