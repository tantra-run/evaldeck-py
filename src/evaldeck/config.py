"""Configuration loading and management."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Configuration for the agent to test."""

    module: str | None = None
    function: str | None = None
    class_name: str | None = None
    framework: str | None = None  # "langchain", "crewai", etc.


class GraderDefaults(BaseModel):
    """Default configuration for graders."""

    llm_model: str = "gpt-4o-mini"
    llm_provider: str | None = None
    timeout: float = 30.0


class ThresholdConfig(BaseModel):
    """Threshold configuration for pass/fail."""

    min_pass_rate: float = 0.0
    max_failures: int | None = None


class SuiteConfig(BaseModel):
    """Configuration for a test suite."""

    name: str
    path: str
    tags: list[str] = Field(default_factory=list)


class ExecutionConfig(BaseModel):
    """Configuration for test execution."""

    workers: int = Field(
        default=0,
        ge=0,
        description="Number of concurrent workers. 0 = unlimited (default).",
    )
    timeout: float = Field(default=30.0, gt=0)
    retries: int = Field(default=0, ge=0)


class EvaldeckConfig(BaseModel):
    """Main evaldeck configuration."""

    version: int = 1

    # Agent configuration
    agent: AgentConfig = Field(default_factory=AgentConfig)

    # Test configuration
    test_dir: str = "tests/evals"
    suites: list[SuiteConfig] = Field(default_factory=list)

    # Execution configuration
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)

    # Legacy execution defaults (deprecated, use execution instead)
    defaults: dict[str, Any] = Field(
        default_factory=lambda: {
            "timeout": 30,
            "retries": 0,
        }
    )

    # Grader configuration
    graders: GraderDefaults = Field(default_factory=GraderDefaults)

    # Thresholds
    thresholds: ThresholdConfig = Field(default_factory=ThresholdConfig)

    # Output configuration
    output_dir: str = ".evaldeck"

    @classmethod
    def load(cls, path: str | Path | None = None) -> EvaldeckConfig:
        """Load configuration from file.

        Searches for evaldeck.yaml, evaldeck.yml in order.
        """
        if path:
            path = Path(path)
            if not path.exists():
                raise FileNotFoundError(f"Config file not found: {path}")
            return cls._load_file(path)

        # Search for config file
        for name in ["evaldeck.yaml", "evaldeck.yml"]:
            p = Path(name)
            if p.exists():
                return cls._load_file(p)

        # Return default config
        return cls()

    @classmethod
    def _load_file(cls, path: Path) -> EvaldeckConfig:
        """Load configuration from a specific file."""
        with open(path) as f:
            data = yaml.safe_load(f) or {}

        # Handle nested objects
        if "agent" in data and isinstance(data["agent"], dict):
            data["agent"] = AgentConfig(**data["agent"])

        if "graders" in data and isinstance(data["graders"], dict):
            # Handle 'llm' sub-key
            if "llm" in data["graders"]:
                llm_config = data["graders"]["llm"]
                data["graders"] = GraderDefaults(
                    llm_model=llm_config.get("model", "gpt-4o-mini"),
                    llm_provider=llm_config.get("provider"),
                )
            else:
                data["graders"] = GraderDefaults(**data["graders"])

        if "thresholds" in data and isinstance(data["thresholds"], dict):
            data["thresholds"] = ThresholdConfig(**data["thresholds"])

        if "execution" in data and isinstance(data["execution"], dict):
            data["execution"] = ExecutionConfig(**data["execution"])

        if "suites" in data:
            suites = []
            for s in data["suites"]:
                if isinstance(s, dict):
                    suites.append(SuiteConfig(**s))
                else:
                    suites.append(s)
            data["suites"] = suites

        return cls(**data)

    def save(self, path: str | Path) -> None:
        """Save configuration to file."""
        with open(path, "w") as f:
            yaml.dump(self.model_dump(exclude_none=True), f, default_flow_style=False)


def generate_default_config() -> str:
    """Generate default configuration YAML."""
    return """# Evaldeck Configuration
version: 1

# Agent configuration (optional - can also be specified per test)
# agent:
#   module: my_agent
#   function: run_agent

# Test directory
test_dir: tests/evals

# Test suites (optional - auto-discovers from test_dir if not specified)
# suites:
#   - name: core
#     path: tests/evals/core
#   - name: safety
#     path: tests/evals/safety

# Execution configuration
execution:
  workers: 0      # 0 = unlimited concurrent (default)
  timeout: 30
  retries: 0

# Grader configuration
graders:
  llm:
    model: gpt-4o-mini
    # API key from OPENAI_API_KEY environment variable

# Pass/fail thresholds
thresholds:
  min_pass_rate: 0.0
  # max_failures: 5

# Output directory for traces and results
output_dir: .evaldeck
"""


def generate_example_test() -> str:
    """Generate example test case YAML."""
    return """# Example test case
name: example_test
description: An example test case to get you started

# Conversation turns
turns:
  - user: "Hello, can you help me with a simple task?"
    expected:
      # Tools that must be called (if any)
      # tools_called:
      #   - search
      #   - calculate

      # Output must contain these strings
      output_contains:
        - "help"

      # Maximum steps allowed
      max_steps: 10

      # Task must complete successfully
      task_completed: true

# Optional: Custom graders
# graders:
#   - type: llm
#     prompt: "Did the agent respond helpfully? Answer PASS or FAIL."
#     model: gpt-4o-mini
"""
