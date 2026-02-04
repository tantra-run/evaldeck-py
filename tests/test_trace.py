"""Tests for trace module."""

from evaldeck import Step, StepType, Trace, TraceStatus


class TestStep:
    """Tests for Step class."""

    def test_llm_call_creation(self) -> None:
        """Test creating an LLM call step."""
        step = Step.llm_call(
            model="gpt-4",
            input="Hello",
            output="Hi there!",
        )

        assert step.type == StepType.LLM_CALL
        assert step.model == "gpt-4"
        assert step.input == "Hello"
        assert step.output == "Hi there!"
        assert step.id  # Should have auto-generated ID

    def test_tool_call_creation(self) -> None:
        """Test creating a tool call step."""
        step = Step.tool_call(
            tool_name="search",
            tool_args={"query": "flights"},
            tool_result=["flight1", "flight2"],
        )

        assert step.type == StepType.TOOL_CALL
        assert step.tool_name == "search"
        assert step.tool_args == {"query": "flights"}
        assert step.tool_result == ["flight1", "flight2"]

    def test_reasoning_creation(self) -> None:
        """Test creating a reasoning step."""
        step = Step.reasoning("I should search for flights first")

        assert step.type == StepType.REASONING
        assert step.reasoning_text == "I should search for flights first"


class TestTrace:
    """Tests for Trace class."""

    def test_trace_creation(self) -> None:
        """Test creating a trace."""
        trace = Trace(input="Hello")

        assert trace.input == "Hello"
        assert trace.output is None
        assert trace.status == TraceStatus.SUCCESS
        assert trace.steps == []
        assert trace.id  # Should have auto-generated ID

    def test_add_step(self) -> None:
        """Test adding steps to a trace."""
        trace = Trace(input="Test")

        step1 = Step.tool_call("tool1", {})
        step2 = Step.tool_call("tool2", {})

        trace.add_step(step1)
        trace.add_step(step2)

        assert len(trace.steps) == 2
        assert trace.step_count == 2

    def test_tools_called(self) -> None:
        """Test getting list of tools called."""
        trace = Trace(input="Test")
        trace.add_step(Step.tool_call("search", {}))
        trace.add_step(Step.tool_call("book", {}))
        trace.add_step(Step.tool_call("search", {}))  # Duplicate

        assert trace.tools_called == ["search", "book", "search"]

    def test_tool_calls_property(self) -> None:
        """Test filtering tool call steps."""
        trace = Trace(input="Test")
        trace.add_step(Step.tool_call("search", {}))
        trace.add_step(Step.llm_call("gpt-4", "input", "output"))
        trace.add_step(Step.tool_call("book", {}))

        tool_calls = trace.tool_calls
        assert len(tool_calls) == 2
        assert all(s.type == StepType.TOOL_CALL for s in tool_calls)

    def test_complete(self) -> None:
        """Test completing a trace."""
        trace = Trace(input="Test")
        trace.complete("Done!", TraceStatus.SUCCESS)

        assert trace.output == "Done!"
        assert trace.status == TraceStatus.SUCCESS
        assert trace.completed_at is not None

    def test_serialization(self) -> None:
        """Test trace serialization round-trip."""
        trace = Trace(input="Test", output="Result")
        trace.add_step(Step.tool_call("search", {"q": "test"}))

        # To dict
        data = trace.to_dict()
        assert data["input"] == "Test"
        assert data["output"] == "Result"
        assert len(data["steps"]) == 1

        # From dict
        restored = Trace.from_dict(data)
        assert restored.input == trace.input
        assert restored.output == trace.output
        assert len(restored.steps) == len(trace.steps)
