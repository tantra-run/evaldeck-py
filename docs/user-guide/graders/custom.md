# Custom Graders

Create your own grading logic when built-in graders don't meet your needs.

## When to Use

Use custom graders for:

- Domain-specific validation logic
- Complex business rules
- External service checks (databases, APIs)
- Custom scoring algorithms
- Combining multiple checks

## Creating a Custom Grader

### Step 1: Create the Grader Function

```python
# my_graders.py
from evaldeck import Trace, EvalCase
from evaldeck.results import GradeResult, GradeStatus

def check_booking_format(trace: Trace, test_case: EvalCase) -> GradeResult:
    """Check that booking confirmation follows expected format."""

    output = trace.output or ""

    # Check for confirmation number pattern
    import re
    pattern = r"Confirmation: [A-Z]{2}\d{6}"

    if re.search(pattern, output):
        return GradeResult(
            grader_name="check_booking_format",
            status=GradeStatus.PASS,
            message="Booking confirmation format is valid",
            score=1.0,
        )
    else:
        return GradeResult(
            grader_name="check_booking_format",
            status=GradeStatus.FAIL,
            message="Booking confirmation format is invalid",
            expected="Confirmation: XX000000",
            actual=output[:100],  # First 100 chars
            score=0.0,
        )
```

### Step 2: Reference in Test Case

```yaml
# tests/evals/booking.yaml
name: booking_format_test
input: "Book a flight to NYC"

graders:
  - type: code
    module: my_graders
    function: check_booking_format
```

## GradeResult Structure

Your function must return a `GradeResult`:

```python
from evaldeck.results import GradeResult, GradeStatus

GradeResult(
    grader_name="my_grader",      # Identifier for this grader
    status=GradeStatus.PASS,      # PASS, FAIL, ERROR, or SKIP
    message="Explanation",         # Human-readable result
    score=0.85,                    # Optional: 0.0-1.0
    details={"key": "value"},     # Optional: additional data
    expected="what was expected", # Optional: for failure messages
    actual="what was found",      # Optional: for failure messages
)
```

### GradeStatus Values

| Status | When to Use |
|--------|-------------|
| `PASS` | Criteria met |
| `FAIL` | Criteria not met |
| `ERROR` | Grader encountered an error |
| `SKIP` | Grader not applicable |

### Helper Methods

Use convenience methods for common cases:

```python
# For passing
return GradeResult.passed_result(
    grader_name="my_grader",
    message="All checks passed"
)

# For failing
return GradeResult.failed_result(
    grader_name="my_grader",
    message="Check failed",
    expected="foo",
    actual="bar"
)

# For errors
return GradeResult.error_result(
    grader_name="my_grader",
    message="Database connection failed"
)
```

## Accessing Trace Data

The `Trace` object contains the full execution record:

```python
def my_grader(trace: Trace, test_case: EvalCase) -> GradeResult:
    # Basic info
    input_text = trace.input
    output_text = trace.output
    status = trace.status  # SUCCESS, FAILURE, TIMEOUT, ERROR

    # Steps
    for step in trace.steps:
        if step.type == StepType.TOOL_CALL:
            print(f"Tool: {step.tool_name}")
            print(f"Args: {step.tool_args}")
            print(f"Result: {step.tool_result}")
        elif step.type == StepType.LLM_CALL:
            print(f"Model: {step.model}")
            print(f"Tokens: {step.token_usage}")

    # Convenience properties
    tool_calls = trace.tool_calls      # List of tool call steps
    llm_calls = trace.llm_calls        # List of LLM call steps
    tools_used = trace.tools_called    # Set of tool names
    total_tokens = trace.total_tokens  # Sum of all token usage

    # Metadata
    duration = trace.duration_ms
    framework = trace.framework        # e.g., "langchain"

    # ...
```

## Accessing Test Case Data

The `EvalCase` object contains test definition:

```python
def my_grader(trace: Trace, test_case: EvalCase) -> GradeResult:
    # Test case info
    name = test_case.name
    description = test_case.description
    input_text = test_case.input

    # Expected behavior
    expected = test_case.expected
    if expected:
        required_tools = expected.tools_called
        forbidden_tools = expected.tools_not_called
        max_steps = expected.max_steps

    # Reference data
    reference_output = test_case.reference_output
    reference_tools = test_case.reference_tools

    # Custom metadata
    custom_data = test_case.metadata.get("my_key")

    # ...
```

## Advanced Examples

### Tool Argument Validation

```python
def validate_search_args(trace: Trace, test_case: EvalCase) -> GradeResult:
    """Ensure search tool was called with valid arguments."""

    for step in trace.tool_calls:
        if step.tool_name == "search_flights":
            args = step.tool_args or {}

            # Validate required fields
            if "from" not in args or "to" not in args:
                return GradeResult.failed_result(
                    "validate_search_args",
                    "Search missing required from/to arguments",
                    expected="from and to fields",
                    actual=str(args)
                )

            # Validate format
            if not args.get("from", "").isupper():
                return GradeResult.failed_result(
                    "validate_search_args",
                    "Airport code should be uppercase",
                    expected="NYC",
                    actual=args.get("from")
                )

    return GradeResult.passed_result(
        "validate_search_args",
        "Search arguments are valid"
    )
```

### External Validation

```python
import httpx

def validate_with_api(trace: Trace, test_case: EvalCase) -> GradeResult:
    """Validate output against external API."""

    try:
        response = httpx.post(
            "https://api.example.com/validate",
            json={"output": trace.output},
            timeout=10
        )
        result = response.json()

        if result["valid"]:
            return GradeResult.passed_result(
                "validate_with_api",
                f"API validation passed: {result['message']}"
            )
        else:
            return GradeResult.failed_result(
                "validate_with_api",
                f"API validation failed: {result['message']}"
            )

    except Exception as e:
        return GradeResult.error_result(
            "validate_with_api",
            f"API call failed: {str(e)}"
        )
```

### Scoring Grader

```python
def quality_score(trace: Trace, test_case: EvalCase) -> GradeResult:
    """Calculate a quality score based on multiple factors."""

    score = 0.0
    details = {}

    # Factor 1: Efficiency (fewer steps = better)
    max_steps = test_case.expected.max_steps or 10
    step_ratio = len(trace.steps) / max_steps
    efficiency = max(0, 1 - step_ratio)
    score += efficiency * 0.3
    details["efficiency"] = efficiency

    # Factor 2: Tool selection
    expected_tools = set(test_case.expected.tools_called or [])
    actual_tools = trace.tools_called
    tool_overlap = len(expected_tools & actual_tools) / len(expected_tools) if expected_tools else 1
    score += tool_overlap * 0.4
    details["tool_selection"] = tool_overlap

    # Factor 3: Output quality (length heuristic)
    output_len = len(trace.output or "")
    length_score = min(1.0, output_len / 100)  # Up to 100 chars
    score += length_score * 0.3
    details["output_quality"] = length_score

    # Determine pass/fail
    threshold = 0.7
    status = GradeStatus.PASS if score >= threshold else GradeStatus.FAIL

    return GradeResult(
        grader_name="quality_score",
        status=status,
        message=f"Quality score: {score:.2f} (threshold: {threshold})",
        score=score,
        details=details,
    )
```

## Creating a Grader Class

For reusable graders, create a class:

```python
from evaldeck.graders import BaseGrader
from evaldeck import Trace, EvalCase
from evaldeck.results import GradeResult

class TokenBudgetGrader(BaseGrader):
    """Ensure agent stays within token budget."""

    def __init__(self, max_tokens: int):
        self.max_tokens = max_tokens

    def grade(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        total = trace.total_tokens

        if total <= self.max_tokens:
            return GradeResult.passed_result(
                "TokenBudgetGrader",
                f"Used {total} tokens (budget: {self.max_tokens})"
            )
        else:
            return GradeResult.failed_result(
                "TokenBudgetGrader",
                f"Exceeded token budget",
                expected=f"<= {self.max_tokens}",
                actual=str(total)
            )
```

Use in Python:

```python
from my_graders import TokenBudgetGrader

token_grader = TokenBudgetGrader(max_tokens=1000)
evaluator = Evaluator(graders=[token_grader])
```

## Best Practices

1. **Clear naming** - Grader name should describe what it checks
2. **Informative messages** - Help users understand failures
3. **Include expected/actual** - For debugging failed tests
4. **Handle errors gracefully** - Return ERROR status, don't crash
5. **Keep graders focused** - One check per grader
6. **Document requirements** - What the grader needs to work
