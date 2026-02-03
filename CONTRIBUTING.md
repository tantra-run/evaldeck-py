# Contributing to Evaldeck

Thank you for your interest in contributing to Evaldeck! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How to Contribute

### Reporting Bugs

Before submitting a bug report:
1. Check existing issues to avoid duplicates
2. Use the latest version of Evaldeck
3. Collect relevant information (Python version, OS, stack trace)

When submitting a bug report, include:
- A clear, descriptive title
- Steps to reproduce the issue
- Expected vs actual behavior
- Code samples if applicable
- Environment details

### Suggesting Features

Feature requests are welcome! Please:
1. Check existing issues and discussions first
2. Describe the use case and problem you're trying to solve
3. Explain how the feature would work
4. Consider if it fits Evaldeck's scope (agent evaluation)

### Pull Requests

1. **Fork and clone** the repository
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Set up development environment**:
   ```bash
   pip install -e ".[dev]"
   pre-commit install
   ```
4. **Make your changes** following our coding standards
5. **Add tests** for new functionality
6. **Run the test suite**:
   ```bash
   pytest
   ruff check .
   mypy src/
   ```
7. **Commit your changes** with a clear message:
   ```bash
   git commit -m "feat: add support for X"
   ```
8. **Push and open a PR** against `main`

## Development Setup

### Prerequisites

- Python 3.10+
- Git

### Installation

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/evaldeck.git
cd evaldeck

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=evaldeck

# Run specific test file
pytest tests/test_evaluator.py

# Run specific test
pytest tests/test_evaluator.py::test_basic_evaluation
```

### Code Quality

We use:
- **Ruff** for linting and formatting
- **mypy** for type checking

```bash
# Lint
ruff check .

# Format
ruff format .

# Type check
mypy src/
```

## Coding Standards

### Style

- Follow PEP 8
- Use type hints for all public functions
- Maximum line length: 100 characters
- Use descriptive variable and function names

### Documentation

- Add docstrings to public functions and classes
- Update README.md if adding user-facing features
- Add inline comments for complex logic

### Testing

- Write tests for all new functionality
- Maintain or improve test coverage
- Use descriptive test names: `test_evaluator_returns_failure_when_tool_missing`

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add CrewAI integration
fix: handle empty trace gracefully
docs: update installation instructions
test: add tests for LLM grader
refactor: simplify metric calculation
chore: update dependencies
```

## Project Structure

```
evaldeck/
├── src/evaldeck/
│   ├── __init__.py        # Public API exports
│   ├── cli.py             # CLI commands
│   ├── config.py          # Configuration loading
│   ├── evaluator.py       # Main evaluation engine
│   ├── trace.py           # Trace data models
│   ├── test_case.py       # Test case data models
│   ├── graders/           # Grader implementations
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── code.py
│   │   └── llm.py
│   ├── metrics/           # Metric implementations
│   │   ├── __init__.py
│   │   └── ...
│   └── integrations/      # Framework adapters
│       ├── __init__.py
│       └── langchain.py
├── tests/
│   ├── conftest.py
│   ├── test_evaluator.py
│   └── ...
├── examples/
│   └── ...
└── docs/
    └── ...
```

## Adding a New Integration

To add support for a new agent framework:

1. Create `src/evaldeck/integrations/your_framework.py`
2. Implement a tracer/adapter that captures execution into `Trace` format
3. Add optional dependency to `pyproject.toml`
4. Add tests in `tests/integrations/test_your_framework.py`
5. Update README.md with usage example
6. Add example in `examples/`

## Adding a New Grader

To add a new grader type:

1. Create grader class inheriting from `BaseGrader`
2. Implement `grade(trace, test_case) -> GradeResult`
3. Add tests
4. Export from `evaldeck.graders`
5. Document in README.md

## Adding a New Metric

To add a new metric:

1. Create metric class inheriting from `BaseMetric`
2. Implement `calculate(trace, test_case) -> MetricResult`
3. Add tests
4. Export from `evaldeck.metrics`
5. Document in README.md

## Getting Help

- Open a [Discussion](https://github.com/tantra-run/evaldeck-py/discussions) for questions
- Join our Discord (coming soon)
- Tag maintainers on complex issues

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md
- Release notes
- Project documentation

Thank you for contributing to Evaldeck!
