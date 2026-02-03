# CLI Reference

Evaldeck provides a command-line interface for initializing projects and running evaluations.

## Commands Overview

```bash
evaldeck --help
```

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

## evaldeck init

Initialize a new Evaldeck project in the current directory.

```bash
evaldeck init [OPTIONS]
```

### Options

| Option | Description |
|--------|-------------|
| `--force` | Overwrite existing files |
| `--help` | Show help message |

### What It Creates

```
your-project/
├── evaldeck.yaml           # Configuration file
├── tests/
│   └── evals/
│       └── example.yaml  # Example test case
└── .evaldeck/              # Output directory
```

### Example

```bash
# Initialize in current directory
evaldeck init

# Force overwrite existing files
evaldeck init --force
```

## evaldeck run

Run evaluations against your agent.

```bash
evaldeck run [OPTIONS]
```

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--config PATH` | `-c` | Path to configuration file |
| `--suite NAME` | `-s` | Run specific test suite |
| `--tag TAG` | `-t` | Filter tests by tag (comma-separated for multiple) |
| `--output FORMAT` | `-o` | Output format: `text`, `json`, `junit` |
| `--output-file PATH` | `-f` | Write output to file |
| `--verbose` | `-v` | Show detailed output including traces |
| `--dry-run` | | Validate config without running |
| `--help` | | Show help message |

### Examples

#### Basic Run

Run all tests with default configuration:

```bash
evaldeck run
```

#### Custom Configuration

Use a specific config file:

```bash
evaldeck run --config config/evaldeck.ci.yaml
evaldeck run -c evaldeck.production.yaml
```

#### Filter by Suite

Run a specific test suite:

```bash
evaldeck run --suite critical
evaldeck run -s smoke
```

#### Filter by Tag

Run tests with specific tags:

```bash
# Single tag
evaldeck run --tag critical

# Multiple tags (OR logic)
evaldeck run --tag "critical,smoke"
evaldeck run -t booking -t search
```

#### Output Formats

**Text (default)** - Human-readable terminal output:

```bash
evaldeck run
```

```
Running 5 tests...

  ✓ book_flight_basic (1.2s)
  ✓ book_flight_roundtrip (2.1s)
  ✗ book_flight_preferences (1.8s)
    └─ FAIL: ToolCalledGrader - Expected tool 'set_preferences' not called

Results: 2/3 passed (66.7%)
```

**JSON** - Machine-readable format:

```bash
evaldeck run --output json
evaldeck run -o json --output-file results.json
```

```json
{
  "total": 3,
  "passed": 2,
  "failed": 1,
  "pass_rate": 0.667,
  "duration_ms": 5100,
  "results": [...]
}
```

**JUnit XML** - For CI/CD integration:

```bash
evaldeck run --output junit --output-file results.xml
```

```xml
<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="evaldeck" tests="3" failures="1" time="5.1">
    <testcase name="book_flight_basic" time="1.2"/>
    <testcase name="book_flight_roundtrip" time="2.1"/>
    <testcase name="book_flight_preferences" time="1.8">
      <failure message="ToolCalledGrader failed">
        Expected tool 'set_preferences' not called
      </failure>
    </testcase>
  </testsuite>
</testsuites>
```

#### Verbose Mode

Show detailed execution traces:

```bash
evaldeck run --verbose
evaldeck run -v
```

```
  ✗ book_flight_preferences (1.8s)

    Trace:
    ├─ [1] LLM_CALL (gpt-4o-mini) - 0.3s
    │   └─ Parsed user request
    ├─ [2] TOOL_CALL (search_flights) - 0.5s
    │   └─ Found 5 flights
    ├─ [3] TOOL_CALL (book_flight) - 0.4s
    │   └─ Booked flight AA123
    └─ [4] LLM_CALL (gpt-4o-mini) - 0.2s
        └─ Generated response

    Grades:
    ├─ ToolCalledGrader: FAIL
    │   Expected: ['search_flights', 'set_preferences', 'book_flight']
    │   Actual: ['search_flights', 'book_flight']
    │   Missing: ['set_preferences']
    └─ ContainsGrader: PASS
```

#### Dry Run

Validate configuration without executing:

```bash
evaldeck run --dry-run
```

```
Configuration valid.
Found 15 test cases across 3 suites.
Agent: my_agent.run_agent

Would run:
  - critical: 5 tests
  - regression: 8 tests
  - smoke: 2 tests
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All tests passed |
| 1 | One or more tests failed |
| 2 | Configuration or runtime error |

Use exit codes in scripts:

```bash
evaldeck run --tag critical
if [ $? -eq 0 ]; then
  echo "All critical tests passed!"
else
  echo "Some tests failed"
  exit 1
fi
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `EVALDECK_CONFIG` | Default config file path |
| `EVALDECK_VERBOSE` | Set to `1` for verbose output |
| `OPENAI_API_KEY` | API key for OpenAI LLM graders |
| `ANTHROPIC_API_KEY` | API key for Anthropic LLM graders |

```bash
# Use environment variables
export EVALDECK_CONFIG=configs/evaldeck.ci.yaml
export EVALDECK_VERBOSE=1
evaldeck run
```

## Combining Options

Options can be combined:

```bash
# Run critical tests with JSON output to file
evaldeck run \
  --config evaldeck.ci.yaml \
  --tag critical \
  --output json \
  --output-file results.json \
  --verbose
```

## Shell Completion

Enable shell completion for bash/zsh:

```bash
# Bash
eval "$(_EVALDECK_COMPLETE=bash_source evaldeck)"

# Zsh
eval "$(_EVALDECK_COMPLETE=zsh_source evaldeck)"

# Add to your shell profile for persistence
echo 'eval "$(_EVALDECK_COMPLETE=bash_source evaldeck)"' >> ~/.bashrc
```
