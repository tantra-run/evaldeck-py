# Code Standards

Guidelines for contributing code to Evaldeck.

## Style Guide

### Python Style

- Follow PEP 8
- Maximum line length: 100 characters
- Use type hints for all public functions
- Use descriptive variable names

### Formatting

We use Ruff for formatting:

```bash
ruff format .
```

### Imports

Organize imports with Ruff:

```python
# Standard library
from __future__ import annotations
import os
from typing import Any

# Third-party
from pydantic import BaseModel

# Local
from evaldeck.trace import Trace
from evaldeck.results import GradeResult
```

## Type Hints

All public APIs must have type hints:

```python
# Good
def evaluate(self, trace: Trace, test_case: EvalCase) -> EvaluationResult:
    ...

# Bad
def evaluate(self, trace, test_case):
    ...
```

Use `from __future__ import annotations` for forward references:

```python
from __future__ import annotations

class Evaluator:
    def evaluate(self, trace: Trace, test_case: EvalCase) -> EvaluationResult:
        ...
```

## Documentation

### Docstrings

Use Google-style docstrings:

```python
def evaluate(self, trace: Trace, test_case: EvalCase) -> EvaluationResult:
    """Evaluate a trace against a test case.

    Args:
        trace: The execution trace to evaluate.
        test_case: The test case with expected behavior.

    Returns:
        EvaluationResult containing grades and metrics.

    Raises:
        EvaluationError: If evaluation fails.

    Example:
        >>> evaluator = Evaluator()
        >>> result = evaluator.evaluate(trace, test_case)
        >>> print(result.passed)
        True
    """
```

### Comments

- Explain *why*, not *what*
- Keep comments up to date
- Remove commented-out code

```python
# Good: explains intent
# Skip grading if no expectations defined
if not test_case.expected:
    return default_result

# Bad: describes obvious code
# Loop through graders
for grader in graders:
```

## Testing

### Test Structure

```python
def test_evaluator_passes_when_tools_match():
    """Test that evaluation passes when required tools are called."""
    # Arrange
    trace = create_trace_with_tools(["search", "book"])
    test_case = create_test_case(tools_called=["search", "book"])

    # Act
    result = evaluator.evaluate(trace, test_case)

    # Assert
    assert result.passed
    assert len(result.grades) == 1
```

### Test Naming

Use descriptive names:

```python
# Good
def test_tool_called_grader_fails_when_tool_missing():
def test_contains_grader_is_case_insensitive():
def test_llm_grader_handles_api_timeout():

# Bad
def test_grader():
def test_1():
def test_evaluation_works():
```

### Fixtures

Use pytest fixtures for common setup:

```python
# conftest.py
@pytest.fixture
def sample_trace():
    trace = Trace(input="test input")
    trace.add_step(Step.tool_call("search", {}, {}))
    trace.complete(output="test output")
    return trace

@pytest.fixture
def basic_test_case():
    return EvalCase(
        name="test",
        input="test input",
        expected=ExpectedBehavior(tools_called=["search"])
    )
```

### Coverage

Maintain or improve test coverage:

```bash
pytest --cov=evaldeck --cov-report=term-missing
```

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `test`: Tests
- `refactor`: Code refactoring
- `chore`: Maintenance

### Examples

```
feat(graders): add LLMRubricGrader for multi-criteria scoring

fix(cli): handle missing config file gracefully

docs(readme): update installation instructions

test(evaluator): add tests for timeout handling

refactor(trace): simplify step serialization

chore(deps): update pydantic to 2.5
```

## Pull Requests

### PR Title

Follow commit message format:

```
feat(graders): add sentiment analysis grader
```

### PR Description

Include:

- What the change does
- Why it's needed
- How to test it
- Any breaking changes

### PR Checklist

Before submitting:

- [ ] Tests pass (`pytest`)
- [ ] Linting passes (`ruff check .`)
- [ ] Types check (`mypy src/`)
- [ ] Docs updated if needed
- [ ] Commit messages follow convention

## Error Handling

### Exceptions

Use specific exceptions:

```python
class EvaldeckError(Exception):
    """Base exception for Evaldeck."""
    pass

class ConfigurationError(EvaldeckError):
    """Invalid configuration."""
    pass

class GraderError(EvaldeckError):
    """Grader execution failed."""
    pass
```

### Error Messages

Be helpful:

```python
# Good
raise ConfigurationError(
    f"Agent module '{module}' not found. "
    f"Ensure it's installed and the module path is correct."
)

# Bad
raise ConfigurationError("Module not found")
```

## Performance

- Avoid premature optimization
- Profile before optimizing
- Document performance-critical code

```python
# Performance note: This iterates all steps, which is O(n).
# For traces with >1000 steps, consider caching.
@property
def tool_calls(self) -> list[Step]:
    return [s for s in self.steps if s.type == StepType.TOOL_CALL]
```
