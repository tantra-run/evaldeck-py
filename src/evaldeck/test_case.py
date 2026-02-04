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
    max_tool_calls: int | None = None
    max_llm_calls: int | None = None
    task_completed: bool | None = None

    # Custom assertions (for code-based graders)
    custom: dict[str, Any] | None = None


class Turn(BaseModel):
    """A single turn in a conversation."""

    user: str
    expected: ExpectedBehavior | None = None
    graders: list[GraderConfig] = Field(default_factory=list)


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

    Test cases define conversation turns to send to the agent and the expected
    behavior/output to validate against for each turn.

    Example:
        Single turn:
            turns:
              - user: "Book a flight to NYC"
                expected:
                  tools_called: [search_flights, book_flight]

        Multi-turn:
            turns:
              - user: "I want to book a flight"
              - user: "NYC to LA, March 15"
                expected:
                  tools_called: [search_flights]
              - user: "Book the cheapest one"
                expected:
                  tools_called: [book_flight]
    """

    name: str
    description: str | None = None
    turns: list[Turn] = Field(default_factory=list)

    # Execution config
    timeout: float | None = None
    retries: int | None = None

    # Metadata
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Reference data (for grading)
    reference_output: str | None = None
    reference_tools: list[str] | None = None

    @property
    def is_multi_turn(self) -> bool:
        """Check if this is a multi-turn conversation."""
        return len(self.turns) > 1

    @property
    def expected(self) -> ExpectedBehavior:
        """Get expected behavior from first turn (for backward compat with graders)."""
        if self.turns and self.turns[0].expected:
            return self.turns[0].expected
        return ExpectedBehavior()

    @property
    def graders(self) -> list[GraderConfig]:
        """Get graders from first turn (for backward compat)."""
        if self.turns:
            return self.turns[0].graders
        return []

    @property
    def input(self) -> str:
        """Get input from first turn (for backward compat)."""
        if self.turns:
            return self.turns[0].user
        return ""

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
        # Backward compatibility: convert old 'input' format to 'turns'
        if "input" in data and "turns" not in data:
            turn_data: dict[str, Any] = {"user": data.pop("input")}
            if "expected" in data:
                turn_data["expected"] = data.pop("expected")
            if "graders" in data:
                turn_data["graders"] = data.pop("graders")
            data["turns"] = [turn_data]

        # Handle turns
        if "turns" in data:
            turns = []
            for t in data["turns"]:
                if isinstance(t, dict):
                    # Handle nested expected behavior
                    if "expected" in t and isinstance(t["expected"], dict):
                        t["expected"] = ExpectedBehavior(**t["expected"])
                    # Handle nested graders
                    if "graders" in t:
                        graders = []
                        for g in t["graders"]:
                            if isinstance(g, dict):
                                graders.append(GraderConfig(**g))
                            else:
                                graders.append(g)
                        t["graders"] = graders
                    turns.append(Turn(**t))
                else:
                    turns.append(t)
            data["turns"] = turns

        return cls(**data)

    def to_yaml(self) -> str:
        """Convert test case to YAML string."""
        result: str = yaml.dump(self.model_dump(exclude_none=True), default_flow_style=False)
        return result


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
