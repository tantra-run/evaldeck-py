# Contributing

Thank you for your interest in contributing to Evaldeck!

## Ways to Contribute

- **Bug Reports** - Found a bug? [Open an issue](https://github.com/tantra-run/evaldeck-py/issues)
- **Feature Requests** - Have an idea? [Start a discussion](https://github.com/tantra-run/evaldeck-py/discussions)
- **Code Contributions** - Fix bugs, add features, improve docs
- **Documentation** - Improve guides, add examples, fix typos

## Quick Start

```bash
# Clone the repo
git clone https://github.com/tantra-run/evaldeck-py.git
cd evaldeck

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install in dev mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest
```

## Guide Sections

| Guide | Description |
|-------|-------------|
| [Development Setup](setup.md) | Set up your development environment |
| [Code Standards](code-standards.md) | Style, testing, and commit conventions |
| [Adding Graders](adding-graders.md) | Create new grader types |
| [Adding Metrics](adding-metrics.md) | Create new metrics |
| [Adding Integrations](adding-integrations.md) | Support new frameworks |

## Contribution Workflow

1. **Fork** the repository
2. **Create a branch** from `main`
3. **Make changes** following our code standards
4. **Add tests** for new functionality
5. **Run checks** (`pytest`, `ruff`, `mypy`)
6. **Open a PR** with a clear description

## Getting Help

- **Questions**: [GitHub Discussions](https://github.com/tantra-run/evaldeck-py/discussions)
- **Bugs**: [GitHub Issues](https://github.com/tantra-run/evaldeck-py/issues)
- **Chat**: Discord (coming soon)
