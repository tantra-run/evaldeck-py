# Examples

Practical examples showing how to use Evaldeck in common scenarios.

## Quick Examples

| Example | Description |
|---------|-------------|
| [Basic Usage](basic-usage.md) | Core workflow: create trace, define test, evaluate |
| [Testing Tool Calls](tool-calls.md) | Verify correct tool selection and arguments |
| [LLM-as-Judge](llm-judge.md) | Use LLMs for subjective evaluation |
| [LangChain Agent](langchain-agent.md) | Evaluate LangChain/LangGraph agents |

## Complete Example Project

For a full working example, see the **[evaldeck-langchain-example](https://github.com/tantra-run/evaldeck-langchain-example)** repository.

## Code Snippets

### Minimal Example

```python
from evaldeck import Trace, Step, Evaluator, EvalCase, ExpectedBehavior, Turn

# Create a trace (simulating agent execution)
trace = Trace(input="Search for flights to NYC")
trace.add_step(Step.tool_call("search_flights", {"destination": "NYC"}, {"flights": [...]}))
trace.complete(output="Found 3 flights to NYC")

# Define expectations
test_case = EvalCase(
    name="search_test",
    turns=[
        Turn(
            user="Search for flights to NYC",
            expected=ExpectedBehavior(
                tools_called=["search_flights"],
                output_contains=["flights", "NYC"]
            )
        )
    ]
)

# Evaluate
result = Evaluator().evaluate(trace, test_case)
print(f"Passed: {result.passed}")
```

### With YAML Test Cases

```python
from evaldeck import EvalSuite, Evaluator, Trace

# Load tests from YAML files
suite = EvalSuite.from_directory("tests/evals")

# Your agent function (must accept input and history)
def my_agent(input: str, history=None) -> Trace:
    # ... your agent logic ...
    return trace

# Run all tests
evaluator = Evaluator()
result = evaluator.evaluate_suite(suite, my_agent)
print(f"Results: {result.passed}/{result.total} passed")
```

### With LLM Grading

```python
from evaldeck import Trace, EvalCase, Evaluator
from evaldeck.graders import LLMGrader

# Add LLM grader for subjective evaluation
llm_grader = LLMGrader(
    prompt="Is this response helpful and professional? Answer PASS or FAIL.",
    model="gpt-4o-mini"
)
evaluator = Evaluator(graders=[llm_grader])

result = evaluator.evaluate(trace, test_case)
```

## File Structure

Example project structure:

```
my-agent/
├── evaldeck.yaml
├── my_agent.py
├── tests/
│   └── evals/
│       ├── booking/
│       │   ├── basic.yaml
│       │   └── complex.yaml
│       └── search/
│           └── web_search.yaml
```
