# Evaldeck

<p class="subtitle">The evaluation framework for AI agents. Pytest for agents.</p>

---

**Evaldeck** helps you answer one question: **"Is my agent actually working?"**

Unlike LLM evaluation tools that focus on single input→output scoring, Evaldeck evaluates the entire agent execution—how it reasons, which tools it selects, and whether it achieves the goal.

<div class="grid cards" markdown>

-   :material-clock-fast:{ .lg .middle } **5-Minute Setup**

    ---

    Get started with a single command. No complex configuration needed.

    [:octicons-arrow-right-24: Quick Start](getting-started/quickstart.md)

-   :material-puzzle:{ .lg .middle } **Framework Agnostic**

    ---

    Works with LangChain, CrewAI, AutoGen, or your custom agent framework.

    [:octicons-arrow-right-24: Integrations](user-guide/integrations/index.md)

-   :material-check-all:{ .lg .middle } **Comprehensive Evaluation**

    ---

    Evaluate tool selection, execution traces, step efficiency, and more.

    [:octicons-arrow-right-24: Metrics](user-guide/metrics.md)

-   :material-cog:{ .lg .middle } **Flexible Grading**

    ---

    Combine deterministic code-based checks with LLM-as-judge evaluation.

    [:octicons-arrow-right-24: Graders](user-guide/graders/index.md)

</div>

## Why Evaldeck?

Traditional LLM evaluation tools treat models as black boxes—they measure whether the final output is "good" but ignore *how* the agent got there. This approach fails for agents because:

- **Agents are multi-step**: A booking agent might search, filter, compare, and book. Each step matters.
- **Tool selection is critical**: Calling the wrong tool or passing bad arguments causes cascading failures.
- **Efficiency matters**: An agent that takes 20 steps to do a 3-step task is wasting time and tokens.

Evaldeck captures the complete execution trace and provides granular feedback on exactly where things went wrong.

## Quick Example

Define what your agent should do in YAML:

```yaml title="tests/evals/booking.yaml"
name: book_flight_basic
input: "Book me a flight from NYC to LA on March 15th"

expected:
  tools_called:
    - search_flights
    - book_flight
  output_contains:
    - "confirmation"
    - "March 15"
  max_steps: 5
```

Run the evaluation:

```bash
evaldeck run
```

Get actionable feedback:

```
Running 3 tests...

  ✓ book_flight_basic (1.2s)
  ✓ book_flight_roundtrip (2.1s)
  ✗ book_flight_with_preferences (1.8s)
    └─ FAIL at step 3: Wrong tool called
       Expected: search_flights_with_filters
       Got: search_flights

Results: 2/3 passed (66.7%)
```

## Installation

```bash
pip install evaldeck
```

With LLM graders:

```bash
pip install evaldeck[openai]      # OpenAI model graders
pip install evaldeck[anthropic]   # Anthropic model graders
pip install evaldeck[all]         # Everything
```

## Next Steps

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Getting Started**

    ---

    Install Evaldeck and run your first evaluation.

    [:octicons-arrow-right-24: Get Started](getting-started/index.md)

-   :material-book-open-variant:{ .lg .middle } **User Guide**

    ---

    Learn how to configure test cases, graders, and CI/CD.

    [:octicons-arrow-right-24: User Guide](user-guide/index.md)

-   :material-lightbulb:{ .lg .middle } **Concepts**

    ---

    Understand traces, evaluation workflows, and grading strategies.

    [:octicons-arrow-right-24: Concepts](concepts/index.md)

-   :material-code-tags:{ .lg .middle } **API Reference**

    ---

    Detailed documentation for all classes and functions.

    [:octicons-arrow-right-24: API Reference](api/index.md)

</div>
