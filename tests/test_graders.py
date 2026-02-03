"""Tests for graders module."""

from evaldeck import EvalCase, ExpectedBehavior, Step, Trace
from evaldeck.graders import (
    CompositeGrader,
    ContainsGrader,
    MaxStepsGrader,
    ToolCalledGrader,
    ToolNotCalledGrader,
)
from evaldeck.results import GradeStatus


class TestContainsGrader:
    """Tests for ContainsGrader."""

    def test_pass_when_all_values_present(self) -> None:
        """Test passing when all expected values are in output."""
        trace = Trace(input="test", output="Hello world, this is a test")
        test_case = EvalCase(
            name="test",
            input="test",
            expected=ExpectedBehavior(output_contains=["hello", "test"]),
        )

        grader = ContainsGrader()
        result = grader.grade(trace, test_case)

        assert result.status == GradeStatus.PASS

    def test_fail_when_value_missing(self) -> None:
        """Test failing when expected value is missing."""
        trace = Trace(input="test", output="Hello world")
        test_case = EvalCase(
            name="test",
            input="test",
            expected=ExpectedBehavior(output_contains=["hello", "goodbye"]),
        )

        grader = ContainsGrader()
        result = grader.grade(trace, test_case)

        assert result.status == GradeStatus.FAIL
        assert "goodbye" in result.message.lower()

    def test_case_insensitive_by_default(self) -> None:
        """Test case-insensitive matching by default."""
        trace = Trace(input="test", output="HELLO WORLD")
        test_case = EvalCase(
            name="test",
            input="test",
            expected=ExpectedBehavior(output_contains=["hello"]),
        )

        grader = ContainsGrader()
        result = grader.grade(trace, test_case)

        assert result.status == GradeStatus.PASS

    def test_explicit_values_override(self) -> None:
        """Test explicit values parameter overrides test case."""
        trace = Trace(input="test", output="specific content here")
        test_case = EvalCase(
            name="test",
            input="test",
            expected=ExpectedBehavior(output_contains=["other"]),
        )

        grader = ContainsGrader(values=["specific"])
        result = grader.grade(trace, test_case)

        assert result.status == GradeStatus.PASS


class TestToolCalledGrader:
    """Tests for ToolCalledGrader."""

    def test_pass_when_all_tools_called(self) -> None:
        """Test passing when all required tools are called."""
        trace = Trace(input="test")
        trace.add_step(Step.tool_call("search", {}))
        trace.add_step(Step.tool_call("book", {}))

        test_case = EvalCase(
            name="test",
            input="test",
            expected=ExpectedBehavior(tools_called=["search", "book"]),
        )

        grader = ToolCalledGrader()
        result = grader.grade(trace, test_case)

        assert result.status == GradeStatus.PASS

    def test_fail_when_tool_missing(self) -> None:
        """Test failing when required tool not called."""
        trace = Trace(input="test")
        trace.add_step(Step.tool_call("search", {}))

        test_case = EvalCase(
            name="test",
            input="test",
            expected=ExpectedBehavior(tools_called=["search", "book"]),
        )

        grader = ToolCalledGrader()
        result = grader.grade(trace, test_case)

        assert result.status == GradeStatus.FAIL
        assert "book" in str(result.expected)

    def test_pass_with_extra_tools(self) -> None:
        """Test passing even when extra tools are called."""
        trace = Trace(input="test")
        trace.add_step(Step.tool_call("search", {}))
        trace.add_step(Step.tool_call("validate", {}))  # Extra tool
        trace.add_step(Step.tool_call("book", {}))

        test_case = EvalCase(
            name="test",
            input="test",
            expected=ExpectedBehavior(tools_called=["search", "book"]),
        )

        grader = ToolCalledGrader()
        result = grader.grade(trace, test_case)

        assert result.status == GradeStatus.PASS


class TestToolNotCalledGrader:
    """Tests for ToolNotCalledGrader."""

    def test_pass_when_forbidden_tools_not_called(self) -> None:
        """Test passing when forbidden tools are not called."""
        trace = Trace(input="test")
        trace.add_step(Step.tool_call("search", {}))

        test_case = EvalCase(
            name="test",
            input="test",
            expected=ExpectedBehavior(tools_not_called=["delete", "cancel"]),
        )

        grader = ToolNotCalledGrader()
        result = grader.grade(trace, test_case)

        assert result.status == GradeStatus.PASS

    def test_fail_when_forbidden_tool_called(self) -> None:
        """Test failing when forbidden tool is called."""
        trace = Trace(input="test")
        trace.add_step(Step.tool_call("search", {}))
        trace.add_step(Step.tool_call("delete", {}))

        test_case = EvalCase(
            name="test",
            input="test",
            expected=ExpectedBehavior(tools_not_called=["delete"]),
        )

        grader = ToolNotCalledGrader()
        result = grader.grade(trace, test_case)

        assert result.status == GradeStatus.FAIL


class TestMaxStepsGrader:
    """Tests for MaxStepsGrader."""

    def test_pass_when_under_limit(self) -> None:
        """Test passing when under step limit."""
        trace = Trace(input="test")
        trace.add_step(Step.tool_call("step1", {}))
        trace.add_step(Step.tool_call("step2", {}))

        test_case = EvalCase(
            name="test",
            input="test",
            expected=ExpectedBehavior(max_steps=5),
        )

        grader = MaxStepsGrader()
        result = grader.grade(trace, test_case)

        assert result.status == GradeStatus.PASS

    def test_fail_when_over_limit(self) -> None:
        """Test failing when over step limit."""
        trace = Trace(input="test")
        for i in range(10):
            trace.add_step(Step.tool_call(f"step{i}", {}))

        test_case = EvalCase(
            name="test",
            input="test",
            expected=ExpectedBehavior(max_steps=5),
        )

        grader = MaxStepsGrader()
        result = grader.grade(trace, test_case)

        assert result.status == GradeStatus.FAIL


class TestCompositeGrader:
    """Tests for CompositeGrader."""

    def test_all_must_pass(self) -> None:
        """Test require_all=True requires all graders to pass."""
        trace = Trace(input="test", output="hello")
        trace.add_step(Step.tool_call("search", {}))

        test_case = EvalCase(
            name="test",
            input="test",
            expected=ExpectedBehavior(
                output_contains=["hello"],
                tools_called=["search", "missing"],
            ),
        )

        graders = [ContainsGrader(), ToolCalledGrader()]
        composite = CompositeGrader(graders, require_all=True)
        result = composite.grade(trace, test_case)

        assert result.status == GradeStatus.FAIL
        assert "1/2" in result.message

    def test_any_can_pass(self) -> None:
        """Test require_all=False allows any grader to pass."""
        trace = Trace(input="test", output="hello")

        test_case = EvalCase(
            name="test",
            input="test",
            expected=ExpectedBehavior(
                output_contains=["hello"],
                tools_called=["missing"],
            ),
        )

        graders = [ContainsGrader(), ToolCalledGrader()]
        composite = CompositeGrader(graders, require_all=False)
        result = composite.grade(trace, test_case)

        assert result.status == GradeStatus.PASS
