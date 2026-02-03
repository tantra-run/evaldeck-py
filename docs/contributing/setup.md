# Development Setup

Set up your environment for Evaldeck development.

## Prerequisites

- Python 3.10+
- Git
- (Optional) OpenAI or Anthropic API key for LLM grader tests

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/evaldeck-ai/evaldeck.git
cd evaldeck
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
# Core + dev dependencies
pip install -e ".[dev]"

# With all optional dependencies
pip install -e ".[dev,all]"
```

### 4. Install Pre-commit Hooks

```bash
pre-commit install
```

This runs linting and formatting on every commit.

## Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=evaldeck --cov-report=html

# Specific file
pytest tests/test_evaluator.py

# Specific test
pytest tests/test_evaluator.py::test_basic_evaluation -v

# Skip slow tests
pytest -m "not slow"
```

## Code Quality

### Linting

```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check --fix .
```

### Formatting

```bash
# Check formatting
ruff format --check .

# Apply formatting
ruff format .
```

### Type Checking

```bash
mypy src/
```

### Run All Checks

```bash
# Same as CI
ruff check .
ruff format --check .
mypy src/
pytest
```

## Building Documentation

```bash
# Install docs dependencies
pip install mkdocs-material mkdocstrings[python]

# Serve locally
mkdocs serve

# Build static site
mkdocs build
```

Visit `http://localhost:8000` to view docs.

## Project Structure

```
evaldeck/
├── src/evaldeck/           # Source code
│   ├── __init__.py       # Public API
│   ├── cli.py            # CLI commands
│   ├── config.py         # Configuration
│   ├── evaluator.py      # Core engine
│   ├── trace.py          # Trace models
│   ├── test_case.py      # Test case models
│   ├── results.py        # Result models
│   ├── graders/          # Grader implementations
│   │   ├── base.py
│   │   ├── code.py
│   │   └── llm.py
│   ├── metrics/          # Metric implementations
│   └── integrations/     # Framework adapters
├── tests/                # Test suite
│   ├── conftest.py       # Fixtures
│   ├── test_evaluator.py
│   └── ...
├── docs/                 # Documentation
├── examples/             # Usage examples
├── pyproject.toml        # Project config
└── mkdocs.yml           # Docs config
```

## Environment Variables

For LLM grader tests:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

## IDE Setup

### VS Code

Recommended extensions:

- Python
- Pylance
- Ruff

Settings (`.vscode/settings.json`):

```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.fixAll.ruff": "explicit",
            "source.organizeImports.ruff": "explicit"
        }
    },
    "python.analysis.typeCheckingMode": "basic"
}
```

### PyCharm

1. Mark `src` as Sources Root
2. Enable Ruff plugin
3. Configure Python interpreter to use venv

## Troubleshooting

### Import Errors

Ensure you installed in editable mode:

```bash
pip install -e ".[dev]"
```

### Pre-commit Failures

Run checks manually to see details:

```bash
ruff check .
ruff format .
```

### Test Failures

Check Python version:

```bash
python --version  # Should be 3.10+
```

Run with verbose output:

```bash
pytest -v --tb=long
```
