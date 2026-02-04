"""Trace data models for capturing agent execution."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StepType(str, Enum):
    """Type of step in an agent trace."""

    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    REASONING = "reasoning"
    HUMAN_INPUT = "human_input"


class StepStatus(str, Enum):
    """Status of a step execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"


class TraceStatus(str, Enum):
    """Status of the overall trace execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"


class Message(BaseModel):
    """A message in a conversation."""

    role: str  # "user" or "assistant"
    content: str


class TokenUsage(BaseModel):
    """Token usage for an LLM call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    @property
    def cost_estimate(self) -> float | None:
        """Estimate cost based on token usage. Returns None if model unknown."""
        return None


class Step(BaseModel):
    """A single step in an agent's execution trace.

    Steps can represent LLM calls, tool calls, reasoning steps, or human input.
    """

    id: str = Field(default_factory=lambda: "")
    type: StepType
    timestamp: datetime = Field(default_factory=datetime.now)
    status: StepStatus = StepStatus.SUCCESS

    # For LLM calls
    model: str | None = None
    input: str | None = None
    output: str | None = None
    tokens: TokenUsage | None = None

    # For tool calls
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    tool_result: Any | None = None

    # For reasoning steps
    reasoning_text: str | None = None

    # Metadata
    parent_id: str | None = None
    error: str | None = None
    duration_ms: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        """Generate ID if not provided."""
        if not self.id:
            import uuid

            self.id = str(uuid.uuid4())[:8]

    @classmethod
    def llm_call(
        cls,
        model: str,
        input: str,
        output: str,
        tokens: TokenUsage | None = None,
        **kwargs: Any,
    ) -> Step:
        """Create an LLM call step."""
        return cls(
            type=StepType.LLM_CALL,
            model=model,
            input=input,
            output=output,
            tokens=tokens,
            **kwargs,
        )

    @classmethod
    def tool_call(
        cls,
        tool_name: str,
        tool_args: dict[str, Any] | None = None,
        tool_result: Any = None,
        **kwargs: Any,
    ) -> Step:
        """Create a tool call step."""
        return cls(
            type=StepType.TOOL_CALL,
            tool_name=tool_name,
            tool_args=tool_args or {},
            tool_result=tool_result,
            **kwargs,
        )

    @classmethod
    def reasoning(cls, text: str, **kwargs: Any) -> Step:
        """Create a reasoning step."""
        return cls(
            type=StepType.REASONING,
            reasoning_text=text,
            **kwargs,
        )


class Trace(BaseModel):
    """Complete execution trace of an agent.

    A trace captures everything that happened during an agent's execution,
    from the initial input to the final output, including all intermediate
    steps (LLM calls, tool calls, reasoning).
    """

    id: str = Field(default_factory=lambda: "")
    input: str
    output: str | None = None
    status: TraceStatus = TraceStatus.SUCCESS
    steps: list[Step] = Field(default_factory=list)

    # Timing
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
    duration_ms: float | None = None

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
    framework: str | None = None
    agent_name: str | None = None

    def model_post_init(self, __context: Any) -> None:
        """Generate ID if not provided."""
        if not self.id:
            import uuid

            self.id = str(uuid.uuid4())[:8]

    @property
    def tool_calls(self) -> list[Step]:
        """Get all tool call steps."""
        return [s for s in self.steps if s.type == StepType.TOOL_CALL]

    @property
    def llm_calls(self) -> list[Step]:
        """Get all LLM call steps."""
        return [s for s in self.steps if s.type == StepType.LLM_CALL]

    @property
    def tools_called(self) -> list[str]:
        """Get list of tool names that were called."""
        return [s.tool_name for s in self.tool_calls if s.tool_name]

    @property
    def total_tokens(self) -> int:
        """Get total tokens used across all LLM calls."""
        total = 0
        for step in self.llm_calls:
            if step.tokens:
                total += step.tokens.total_tokens
        return total

    @property
    def step_count(self) -> int:
        """Get total number of steps."""
        return len(self.steps)

    def add_step(self, step: Step) -> None:
        """Add a step to the trace."""
        self.steps.append(step)

    def complete(self, output: str, status: TraceStatus = TraceStatus.SUCCESS) -> None:
        """Mark the trace as complete."""
        self.output = output
        self.status = status
        self.completed_at = datetime.now()
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_ms = delta.total_seconds() * 1000

    def to_dict(self) -> dict[str, Any]:
        """Convert trace to dictionary."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Trace:
        """Create trace from dictionary."""
        return cls.model_validate(data)
