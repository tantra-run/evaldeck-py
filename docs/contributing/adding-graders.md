# Adding Graders

Create custom graders to evaluate agent behavior.

## Grader Interface

All graders inherit from `BaseGrader`:

```python
from abc import ABC, abstractmethod
from evaldeck.trace import Trace
from evaldeck.test_case import EvalCase
from evaldeck.results import GradeResult

class BaseGrader(ABC):
    """Base class for all graders."""

    name: str = "base"

    @abstractmethod
    def grade(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        """Evaluate the trace and return a grade result."""
        pass
```

## Creating a Grader

### Step 1: Define the Class

```python
# src/evaldeck/graders/sentiment.py
from evaldeck.graders.base import BaseGrader
from evaldeck.results import GradeResult, GradeStatus


class SentimentGrader(BaseGrader):
    """Check if output has positive sentiment."""

    name = "sentiment"

    def __init__(self, require_positive: bool = True):
        """Initialize sentiment grader.

        Args:
            require_positive: If True, output must be positive.
                            If False, output must not be negative.
        """
        self.require_positive = require_positive
```

### Step 2: Implement grade()

```python
    def grade(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        """Check sentiment of the output."""
        output = trace.output or ""

        # Simple sentiment check (replace with real implementation)
        positive_words = ["great", "success", "happy", "thank", "perfect"]
        negative_words = ["error", "fail", "sorry", "unfortunately", "problem"]

        output_lower = output.lower()
        has_positive = any(word in output_lower for word in positive_words)
        has_negative = any(word in output_lower for word in negative_words)

        if self.require_positive:
            if has_positive and not has_negative:
                return GradeResult.passed_result(
                    self.name,
                    "Output has positive sentiment"
                )
            return GradeResult.failed_result(
                self.name,
                "Output does not have positive sentiment",
                expected="positive sentiment",
                actual=f"positive={has_positive}, negative={has_negative}"
            )
        else:
            if not has_negative:
                return GradeResult.passed_result(
                    self.name,
                    "Output is not negative"
                )
            return GradeResult.failed_result(
                self.name,
                "Output has negative sentiment",
                expected="no negative sentiment",
                actual=output[:100]
            )
```

### Step 3: Export the Grader

```python
# src/evaldeck/graders/__init__.py
from evaldeck.graders.sentiment import SentimentGrader

__all__ = [
    # ... existing exports ...
    "SentimentGrader",
]
```

### Step 4: Add Tests

```python
# tests/test_graders.py
import pytest
from evaldeck import Trace
from evaldeck.graders import SentimentGrader


class TestSentimentGrader:
    def test_passes_on_positive_output(self):
        trace = Trace(input="test")
        trace.complete(output="Great! Your request was successful.")

        grader = SentimentGrader(require_positive=True)
        result = grader.grade(trace, mock_test_case)

        assert result.passed
        assert "positive" in result.message.lower()

    def test_fails_on_negative_output(self):
        trace = Trace(input="test")
        trace.complete(output="Sorry, there was an error processing your request.")

        grader = SentimentGrader(require_positive=True)
        result = grader.grade(trace, mock_test_case)

        assert not result.passed

    def test_handles_empty_output(self):
        trace = Trace(input="test")
        trace.complete(output="")

        grader = SentimentGrader(require_positive=True)
        result = grader.grade(trace, mock_test_case)

        assert not result.passed
```

## GradeResult

Return appropriate results:

```python
# Success
GradeResult.passed_result(
    grader_name="my_grader",
    message="Check passed",
    score=1.0,  # Optional
    details={"key": "value"}  # Optional
)

# Failure
GradeResult.failed_result(
    grader_name="my_grader",
    message="Check failed because...",
    expected="what was expected",
    actual="what was found"
)

# Error (grader couldn't run)
GradeResult.error_result(
    grader_name="my_grader",
    message="Failed to connect to API"
)
```

## Configuration Support

To support YAML configuration:

### 1. Update GraderConfig handling

```python
# src/evaldeck/evaluator.py
def _create_grader_from_config(self, config: GraderConfig) -> BaseGrader | None:
    grader_type = config.type.lower()

    if grader_type == "sentiment":
        return SentimentGrader(**config.params)

    # ... existing handlers ...
```

### 2. Document YAML usage

```yaml
# In test case
graders:
  - type: sentiment
    params:
      require_positive: true
```

## Best Practices

### 1. Single Responsibility

Each grader should check one thing:

```python
# Good: focused grader
class ToolCalledGrader(BaseGrader):
    """Check that required tools were called."""

# Bad: multi-purpose grader
class EverythingGrader(BaseGrader):
    """Check tools, output, sentiment, and format."""
```

### 2. Clear Error Messages

Help users understand failures:

```python
# Good
return GradeResult.failed_result(
    self.name,
    f"Required tool '{tool}' was not called. "
    f"Called tools: {sorted(called_tools)}",
    expected=required_tools,
    actual=called_tools
)

# Bad
return GradeResult.failed_result(self.name, "Failed")
```

### 3. Handle Edge Cases

```python
def grade(self, trace: Trace, test_case: EvalCase) -> GradeResult:
    # Handle missing output
    if not trace.output:
        return GradeResult.failed_result(
            self.name,
            "No output to evaluate"
        )

    # Handle missing expectations
    expected = test_case.expected.custom_field
    if expected is None:
        return GradeResult.passed_result(
            self.name,
            "No expectation defined, skipping"
        )
```

### 4. Use Type Hints

```python
def grade(self, trace: Trace, test_case: EvalCase) -> GradeResult:
    ...
```

## Example: API Response Grader

A more complex example checking API response format:

```python
class APIResponseGrader(BaseGrader):
    """Validate that tool results match expected API response format."""

    name = "api_response"

    def __init__(
        self,
        tool_name: str,
        required_fields: list[str],
        field_types: dict[str, type] | None = None
    ):
        self.tool_name = tool_name
        self.required_fields = required_fields
        self.field_types = field_types or {}

    def grade(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        # Find the tool call
        tool_call = None
        for step in trace.tool_calls:
            if step.tool_name == self.tool_name:
                tool_call = step
                break

        if tool_call is None:
            return GradeResult.failed_result(
                self.name,
                f"Tool '{self.tool_name}' was not called"
            )

        result = tool_call.tool_result
        if not isinstance(result, dict):
            return GradeResult.failed_result(
                self.name,
                f"Tool result is not a dict: {type(result)}",
                expected="dict",
                actual=type(result).__name__
            )

        # Check required fields
        missing = [f for f in self.required_fields if f not in result]
        if missing:
            return GradeResult.failed_result(
                self.name,
                f"Missing required fields: {missing}",
                expected=self.required_fields,
                actual=list(result.keys())
            )

        # Check field types
        type_errors = []
        for field, expected_type in self.field_types.items():
            if field in result and not isinstance(result[field], expected_type):
                type_errors.append(
                    f"{field}: expected {expected_type.__name__}, "
                    f"got {type(result[field]).__name__}"
                )

        if type_errors:
            return GradeResult.failed_result(
                self.name,
                f"Type errors: {type_errors}"
            )

        return GradeResult.passed_result(
            self.name,
            f"API response from '{self.tool_name}' is valid"
        )
```
