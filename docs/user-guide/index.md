# User Guide

This guide covers everything you need to effectively use Evaldeck for agent evaluation.

## Overview

The User Guide is organized into the following sections:

| Section | Description |
|---------|-------------|
| [Configuration](configuration.md) | Project setup and `evaldeck.yaml` options |
| [Test Cases](test-cases.md) | Writing and organizing test cases |
| [CLI Reference](cli.md) | Command-line interface options |
| [Graders](graders/index.md) | Evaluation strategies |
| [Metrics](metrics.md) | Quantitative measurements |
| [Integrations](integrations/index.md) | Framework adapters |
| [CI/CD](ci-cd.md) | Continuous integration setup |

## Quick Reference

### Project Structure

A typical Evaldeck project:

```
my-project/
├── evaldeck.yaml              # Configuration
├── my_agent.py              # Your agent code
├── tests/
│   └── evals/
│       ├── booking/
│       │   ├── basic.yaml
│       │   └── complex.yaml
│       └── search/
│           └── web_search.yaml
└── .evaldeck/                 # Output (gitignore)
    └── results/
```

### Essential Commands

```bash
# Initialize new project
evaldeck init

# Run all tests
evaldeck run

# Run with specific config
evaldeck run --config custom.yaml

# Run tests by tag
evaldeck run --tag critical

# Verbose output
evaldeck run --verbose

# Generate reports
evaldeck run --output junit --output-file results.xml
```

### Test Case Quick Reference

```yaml
name: test_name                    # Required: unique identifier
description: What this tests       # Optional: documentation

input: "User message"              # Required: agent input

expected:                          # Expected behavior
  tools_called: [tool1, tool2]     # Required tools
  tools_not_called: [bad_tool]     # Forbidden tools
  tool_call_order: [a, b, c]       # Sequence requirement
  output_contains: ["phrase"]      # Output must contain
  output_not_contains: ["error"]   # Output must not contain
  output_equals: "exact match"     # Exact output match
  output_matches: "regex.*"        # Regex match
  max_steps: 10                    # Step limit
  min_steps: 2                     # Minimum steps
  task_completed: true             # Must succeed

graders:                           # Custom graders
  - type: llm
    prompt: "Grade this..."
    model: gpt-4o-mini
    threshold: 0.8

timeout: 30                        # Timeout in seconds
retries: 2                         # Retry on failure
tags: [critical, booking]          # Categorization

metadata:                          # Custom metadata
  author: team-a
  priority: high
```

### Configuration Quick Reference

```yaml
# evaldeck.yaml
version: 1

agent:
  module: my_agent           # Python module
  function: run              # Function name

test_dir: tests/evals        # Test case directory

defaults:
  timeout: 30                # Default timeout
  retries: 0                 # Default retries

graders:
  llm:
    model: gpt-4o-mini       # Default LLM model
    provider: openai         # openai or anthropic

thresholds:
  min_pass_rate: 0.9         # Minimum pass rate

output_dir: .evaldeck          # Results directory
```

## Workflow Tips

### 1. Organize Tests by Feature

```
tests/evals/
├── booking/
│   ├── flights.yaml
│   └── hotels.yaml
├── search/
│   └── web.yaml
└── auth/
    └── login.yaml
```

### 2. Use Tags Strategically

```yaml
tags:
  - critical    # Run in CI
  - smoke       # Quick sanity checks
  - regression  # Full regression suite
```

### 3. Layer Your Grading

Start with deterministic checks, add LLM grading for nuance:

```yaml
expected:
  tools_called: [search]        # Deterministic
  output_contains: ["result"]   # Deterministic

graders:
  - type: llm                   # Nuanced evaluation
    prompt: "Is this helpful?"
```

### 4. Set Appropriate Thresholds

For CI/CD:

```yaml
thresholds:
  min_pass_rate: 1.0    # Critical tests must all pass
```

For development:

```yaml
thresholds:
  min_pass_rate: 0.8    # Allow some failures
```
