# Installation

This guide covers installing Evaldeck and its optional dependencies.

## Requirements

- Python 3.10 or later
- pip (comes with Python)

## Basic Installation

Install Evaldeck from PyPI:

```bash
pip install evaldeck
```

This installs the core package with:

- CLI tools (`evaldeck init`, `evaldeck run`)
- Trace and test case models
- Code-based graders (deterministic checks)
- Built-in metrics

## Optional Dependencies

### LLM Graders

To use LLM-as-judge grading, install the provider you need:

=== "OpenAI"

    ```bash
    pip install evaldeck[openai]
    ```

    Set your API key:
    ```bash
    export OPENAI_API_KEY="sk-..."
    ```

=== "Anthropic"

    ```bash
    pip install evaldeck[anthropic]
    ```

    Set your API key:
    ```bash
    export ANTHROPIC_API_KEY="sk-ant-..."
    ```

=== "Both"

    ```bash
    pip install evaldeck[all]
    ```

### Framework Integrations

Evaldeck uses OpenTelemetry/OpenInference for framework integrations. The core OpenTelemetry adapter is included. Install instrumentors for your frameworks:

```bash
# For LangChain
pip install openinference-instrumentation-langchain

# For CrewAI
pip install openinference-instrumentation-crewai

# For OpenAI SDK
pip install openinference-instrumentation-openai

# For LiteLLM
pip install openinference-instrumentation-litellm
```

## Verify Installation

Check that Evaldeck is installed correctly:

```bash
evaldeck --version
```

You should see:

```
evaldeck, version 0.1.0
```

Try the help command:

```bash
evaldeck --help
```

Output:

```
Usage: evaldeck [OPTIONS] COMMAND [ARGS]...

  Evaldeck - The evaluation framework for AI agents.

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  init  Initialize a new Evaldeck project.
  run   Run evaluations.
```

## Development Installation

For contributing to Evaldeck or running from source:

```bash
# Clone the repository
git clone https://github.com/tantra-run/evaldeck-py.git
cd evaldeck

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Troubleshooting

### Python Version Issues

If you see errors about Python version:

```bash
# Check your Python version
python --version

# Use a specific Python version
python3.11 -m pip install evaldeck
```

### Permission Errors

If you get permission errors:

```bash
# Install in user space
pip install --user evaldeck

# Or use a virtual environment (recommended)
python -m venv myenv
source myenv/bin/activate
pip install evaldeck
```

### Import Errors

If imports fail after installation:

```bash
# Ensure you're in the right environment
which python
pip show evaldeck

# Reinstall if needed
pip uninstall evaldeck
pip install evaldeck
```

## Next Steps

With Evaldeck installed, continue to [Quick Start](quickstart.md) to create your first project.
