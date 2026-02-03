"""Test case data models for defining agent evaluations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class ExpectedBehavior(BaseModel):
    """Expected behavior for an agent test case."""

    # Tool expectations
    tools_called: list[str] | None = None
    tools_not_called: list[str] | None = None
    tool_call_order: list[str] | None = None

    # Output expectations
    output_contains: list[str] | None = None
    output_not_contains: list[str] | None = None
    output_equals: str | None = None
    output_matches: str | None = None  # Regex pattern

    # Execution expectations
    max_steps: int | None = None
    min_steps: int | None = None
    task_completed: bool | None = None

    # Custom assertions (for code-based graders)
    custom: dict[str, Any] | None = None


class GraderConfig(BaseModel):
    """Configuration for a grader."""

    type: str  # "contains", "tool_called", "llm", "custom", etc.
    params: dict[str, Any] = Field(default_factory=dict)

    # For LLM graders
    prompt: str | None = None
    model: str | None = None
    threshold: float | None = None

    # For custom graders
    module: str | None = None
    function: str | None = None


class EvalCase(BaseModel):
    """A test case for evaluating an agent.

    Test cases define an input to send to the agent and the expected
    behavior/output to validate against.
    """

    name: str
    description: str | None = None
    input: str
    expected: ExpectedBehavior = Field(default_factory=ExpectedBehavior)
    graders: list[GraderConfig] = Field(default_factory=list)

    # Execution config
    timeout: float | None = None
    retries: int | None = None

    # Metadata
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Reference data (for grading)
    reference_output: str | None = None
    reference_tools: list[str] | None = None

    @classmethod
    def from_yaml(cls, path: str | Path) -> EvalCase:
        """Load a test case from a YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls._from_dict(data)

    @classmethod
    def from_yaml_string(cls, content: str) -> EvalCase:
        """Load a test case from a YAML string."""
        data = yaml.safe_load(content)
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> EvalCase:
        """Create test case from dictionary, handling nested structures."""
        # Handle expected behavior
        if "expected" in data and isinstance(data["expected"], dict):
            data["expected"] = ExpectedBehavior(**data["expected"])

        # Handle graders
        if "graders" in data:
            graders = []
            for g in data["graders"]:
                if isinstance(g, dict):
                    graders.append(GraderConfig(**g))
                else:
                    graders.append(g)
            data["graders"] = graders

        return cls(**data)

    def to_yaml(self) -> str:
        """Convert test case to YAML string."""
        return yaml.dump(self.model_dump(exclude_none=True), default_flow_style=False)


class EvalSuite(BaseModel):
    """A collection of test cases."""

    name: str
    description: str | None = None
    test_cases: list[EvalCase] = Field(default_factory=list)

    # Suite-level defaults
    defaults: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)

    @classmethod
    def from_directory(cls, path: str | Path, name: str | None = None) -> EvalSuite:
        """Load all test cases from a directory."""
        path = Path(path)
        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")

        test_cases = []
        for file in sorted(path.glob("*.yaml")):
            if file.name.startswith("_"):
                continue
            try:
                test_cases.append(EvalCase.from_yaml(file))
            except Exception as e:
                raise ValueError(f"Failed to load {file}: {e}") from e

        for file in sorted(path.glob("*.yml")):
            if file.name.startswith("_"):
                continue
            try:
                test_cases.append(EvalCase.from_yaml(file))
            except Exception as e:
                raise ValueError(f"Failed to load {file}: {e}") from e

        return cls(
            name=name or path.name,
            test_cases=test_cases,
        )

    def filter_by_tags(self, tags: list[str]) -> EvalSuite:
        """Return a new suite with only test cases matching the given tags."""
        filtered = [tc for tc in self.test_cases if any(t in tc.tags for t in tags)]
        return EvalSuite(
            name=self.name,
            description=self.description,
            test_cases=filtered,
            defaults=self.defaults,
            tags=self.tags,
        )
