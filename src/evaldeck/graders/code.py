"""Code-based graders for deterministic evaluation."""

from __future__ import annotations

import asyncio
import importlib
import re
from collections.abc import Callable
from typing import TYPE_CHECKING

from evaldeck.graders.base import BaseGrader
from evaldeck.results import GradeResult

if TYPE_CHECKING:
    from evaldeck.test_case import EvalCase
    from evaldeck.trace import Trace


class ContainsGrader(BaseGrader):
    """Check if output contains expected values."""

    name = "contains"

    def __init__(
        self,
        values: list[str] | None = None,
        field: str = "output",
        case_sensitive: bool = False,
    ) -> None:
        """Initialize contains grader.

        Args:
            values: Strings that must be present. If None, uses test_case.expected.
            field: Field to check ("output" or "reasoning").
            case_sensitive: Whether to do case-sensitive matching.
        """
        self.values = values
        self.field = field
        self.case_sensitive = case_sensitive

    def grade(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        """Check if all values are present in the output."""
        # Get values to check
        values = self.values
        if values is None:
            values = test_case.expected.output_contains or []

        if not values:
            return GradeResult.passed_result(self.name, "No values to check")

        # Get content to check
        content = trace.output or ""
        if not self.case_sensitive:
            content = content.lower()

        # Check each value
        missing = []
        for value in values:
            check_value = value if self.case_sensitive else value.lower()
            if check_value not in content:
                missing.append(value)

        if missing:
            return GradeResult.failed_result(
                self.name,
                f"Missing values in output: {missing}",
                expected=values,
                actual=trace.output,
            )

        return GradeResult.passed_result(
            self.name,
            f"All {len(values)} values found in output",
        )


class NotContainsGrader(BaseGrader):
    """Check that output does NOT contain certain values."""

    name = "not_contains"

    def __init__(
        self,
        values: list[str] | None = None,
        field: str = "output",
        case_sensitive: bool = False,
    ) -> None:
        self.values = values
        self.field = field
        self.case_sensitive = case_sensitive

    def grade(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        """Check that no forbidden values are present."""
        values = self.values
        if values is None:
            values = test_case.expected.output_not_contains or []

        if not values:
            return GradeResult.passed_result(self.name, "No values to check")

        content = trace.output or ""
        if not self.case_sensitive:
            content = content.lower()

        found = []
        for value in values:
            check_value = value if self.case_sensitive else value.lower()
            if check_value in content:
                found.append(value)

        if found:
            return GradeResult.failed_result(
                self.name,
                f"Forbidden values found in output: {found}",
                expected=f"None of: {values}",
                actual=trace.output,
            )

        return GradeResult.passed_result(self.name, "No forbidden values found")


class EqualsGrader(BaseGrader):
    """Check if output exactly equals expected value."""

    name = "equals"

    def __init__(
        self,
        expected: str | None = None,
        field: str = "output",
        normalize_whitespace: bool = True,
    ) -> None:
        self.expected = expected
        self.field = field
        self.normalize_whitespace = normalize_whitespace

    def grade(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        """Check exact equality."""
        expected = self.expected or test_case.expected.output_equals
        if expected is None:
            return GradeResult.passed_result(self.name, "No expected value to check")

        actual = trace.output or ""

        if self.normalize_whitespace:
            expected = " ".join(expected.split())
            actual = " ".join(actual.split())

        if actual == expected:
            return GradeResult.passed_result(self.name, "Output matches expected")

        return GradeResult.failed_result(
            self.name,
            "Output does not match expected",
            expected=expected,
            actual=actual,
        )


class RegexGrader(BaseGrader):
    """Check if output matches a regex pattern."""

    name = "regex"

    def __init__(
        self,
        pattern: str | None = None,
        field: str = "output",
        flags: int = 0,
    ) -> None:
        self.pattern = pattern
        self.field = field
        self.flags = flags

    def grade(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        """Check regex match."""
        pattern = self.pattern or test_case.expected.output_matches
        if pattern is None:
            return GradeResult.passed_result(self.name, "No pattern to check")

        content = trace.output or ""

        try:
            if re.search(pattern, content, self.flags):
                return GradeResult.passed_result(
                    self.name,
                    f"Output matches pattern: {pattern}",
                )
            return GradeResult.failed_result(
                self.name,
                f"Output does not match pattern: {pattern}",
                expected=pattern,
                actual=content,
            )
        except re.error as e:
            return GradeResult.error_result(self.name, f"Invalid regex: {e}")


class ToolCalledGrader(BaseGrader):
    """Check that required tools were called."""

    name = "tool_called"

    def __init__(self, required: list[str] | None = None) -> None:
        """Initialize tool called grader.

        Args:
            required: List of tool names that must be called.
                     If None, uses test_case.expected.tools_called.
        """
        self.required = required

    def grade(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        """Check that all required tools were called."""
        required = self.required
        if required is None:
            required = test_case.expected.tools_called or []

        if not required:
            return GradeResult.passed_result(self.name, "No required tools to check")

        called = set(trace.tools_called)
        required_set = set(required)
        missing = required_set - called

        if missing:
            return GradeResult.failed_result(
                self.name,
                f"Required tools not called: {sorted(missing)}",
                expected=sorted(required),
                actual=sorted(called),
            )

        return GradeResult.passed_result(
            self.name,
            f"All {len(required)} required tools were called",
        )


class ToolNotCalledGrader(BaseGrader):
    """Check that certain tools were NOT called."""

    name = "tool_not_called"

    def __init__(self, forbidden: list[str] | None = None) -> None:
        self.forbidden = forbidden

    def grade(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        """Check that forbidden tools were not called."""
        forbidden = self.forbidden
        if forbidden is None:
            forbidden = test_case.expected.tools_not_called or []

        if not forbidden:
            return GradeResult.passed_result(self.name, "No forbidden tools to check")

        called = set(trace.tools_called)
        forbidden_set = set(forbidden)
        violated = called & forbidden_set

        if violated:
            return GradeResult.failed_result(
                self.name,
                f"Forbidden tools were called: {sorted(violated)}",
                expected=f"None of: {sorted(forbidden)}",
                actual=sorted(called),
            )

        return GradeResult.passed_result(self.name, "No forbidden tools were called")


class ToolOrderGrader(BaseGrader):
    """Check that tools were called in the correct order."""

    name = "tool_order"

    def __init__(self, expected_order: list[str] | None = None) -> None:
        self.expected_order = expected_order

    def grade(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        """Check tool call ordering."""
        expected = self.expected_order
        if expected is None:
            expected = test_case.expected.tool_call_order or []

        if not expected:
            return GradeResult.passed_result(self.name, "No expected order to check")

        actual = trace.tools_called

        # Check if expected is a subsequence of actual
        expected_idx = 0
        for tool in actual:
            if expected_idx < len(expected) and tool == expected[expected_idx]:
                expected_idx += 1

        if expected_idx == len(expected):
            return GradeResult.passed_result(
                self.name,
                "Tools called in correct order",
            )

        return GradeResult.failed_result(
            self.name,
            "Tools not called in expected order",
            expected=expected,
            actual=actual,
        )


class MaxStepsGrader(BaseGrader):
    """Check that agent completed within maximum steps."""

    name = "max_steps"

    def __init__(self, max_steps: int | None = None) -> None:
        self.max_steps = max_steps

    def grade(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        """Check step count."""
        max_steps = self.max_steps
        if max_steps is None:
            max_steps = test_case.expected.max_steps

        if max_steps is None:
            return GradeResult.passed_result(self.name, "No max steps defined")

        actual = trace.step_count

        if actual <= max_steps:
            return GradeResult.passed_result(
                self.name,
                f"Completed in {actual} steps (max: {max_steps})",
            )

        return GradeResult.failed_result(
            self.name,
            f"Too many steps: {actual} > {max_steps}",
            expected=max_steps,
            actual=actual,
        )


class MaxToolCallsGrader(BaseGrader):
    """Check that agent completed within maximum tool calls.

    Unlike max_steps which counts all trace steps (including internal
    framework steps captured by OTel), this only counts actual tool calls.
    """

    name = "max_tool_calls"

    def __init__(self, max_tool_calls: int | None = None) -> None:
        self.max_tool_calls = max_tool_calls

    def grade(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        """Check tool call count."""
        max_tool_calls = self.max_tool_calls
        if max_tool_calls is None:
            max_tool_calls = test_case.expected.max_tool_calls

        if max_tool_calls is None:
            return GradeResult.passed_result(self.name, "No max tool calls defined")

        actual = len(trace.tool_calls)

        if actual <= max_tool_calls:
            return GradeResult.passed_result(
                self.name,
                f"Made {actual} tool calls (max: {max_tool_calls})",
            )

        return GradeResult.failed_result(
            self.name,
            f"Too many tool calls: {actual} > {max_tool_calls}",
            expected=max_tool_calls,
            actual=actual,
        )


class MaxLLMCallsGrader(BaseGrader):
    """Check that agent completed within maximum LLM calls.

    Counts only LLM call steps, not internal framework steps.
    """

    name = "max_llm_calls"

    def __init__(self, max_llm_calls: int | None = None) -> None:
        self.max_llm_calls = max_llm_calls

    def grade(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        """Check LLM call count."""
        max_llm_calls = self.max_llm_calls
        if max_llm_calls is None:
            max_llm_calls = test_case.expected.max_llm_calls

        if max_llm_calls is None:
            return GradeResult.passed_result(self.name, "No max LLM calls defined")

        actual = len(trace.llm_calls)

        if actual <= max_llm_calls:
            return GradeResult.passed_result(
                self.name,
                f"Made {actual} LLM calls (max: {max_llm_calls})",
            )

        return GradeResult.failed_result(
            self.name,
            f"Too many LLM calls: {actual} > {max_llm_calls}",
            expected=max_llm_calls,
            actual=actual,
        )


class TaskCompletedGrader(BaseGrader):
    """Check if the agent completed the task (based on trace status)."""

    name = "task_completed"

    def __init__(self, require_success: bool = True) -> None:
        self.require_success = require_success

    def grade(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        """Check task completion status."""
        from evaldeck.trace import TraceStatus

        # Check expected from test case
        expected = test_case.expected.task_completed
        if expected is None:
            expected = self.require_success

        is_success = trace.status == TraceStatus.SUCCESS
        has_output = bool(trace.output)

        completed = is_success and has_output

        if expected and completed:
            return GradeResult.passed_result(self.name, "Task completed successfully")
        elif expected and not completed:
            return GradeResult.failed_result(
                self.name,
                f"Task not completed. Status: {trace.status}, Output: {bool(trace.output)}",
                expected="completed",
                actual=f"status={trace.status}",
            )
        elif not expected and not completed:
            return GradeResult.passed_result(
                self.name,
                "Task correctly did not complete (as expected)",
            )
        else:
            return GradeResult.failed_result(
                self.name,
                "Task completed but was expected to fail",
                expected="not completed",
                actual="completed",
            )


class CustomGrader(BaseGrader):
    """Run a custom grading function.

    Supports both synchronous and asynchronous custom functions. When using
    evaluate_async(), async functions are awaited directly while sync functions
    run in a thread pool to avoid blocking the event loop.

    Example with sync function::

        def my_grader(trace, test_case):
            if "error" in trace.output:
                return GradeResult.failed_result("custom", "Found error")
            return GradeResult.passed_result("custom", "No errors")

        grader = CustomGrader(func=my_grader)

    Example with async function::

        async def my_async_grader(trace, test_case):
            # Can make async API calls here
            result = await external_validation_api(trace.output)
            if result.valid:
                return GradeResult.passed_result("custom", "Valid")
            return GradeResult.failed_result("custom", "Invalid")

        grader = CustomGrader(func=my_async_grader)
    """

    name = "custom"

    def __init__(
        self,
        func: Callable[[Trace, EvalCase], GradeResult] | None = None,
        module: str | None = None,
        function: str | None = None,
    ) -> None:
        """Initialize custom grader.

        Args:
            func: Custom grading function. Can be sync or async.
                Signature: (trace, test_case) -> GradeResult
            module: Module path to import function from (alternative to func).
            function: Function name to import from module.

        Provide either `func` directly, or `module` and `function` to import.
        """
        self.func = func
        self.module_name = module
        self.function_name = function
        self._loaded_func: Callable[..., GradeResult] | None = None

    def _get_func(self) -> Callable[[Trace, EvalCase], GradeResult]:
        """Get the grading function."""
        if self.func is not None:
            return self.func

        if self._loaded_func is not None:
            return self._loaded_func

        if self.module_name and self.function_name:
            module = importlib.import_module(self.module_name)
            self._loaded_func = getattr(module, self.function_name)
            return self._loaded_func

        raise ValueError("CustomGrader requires either func or module+function")

    def grade(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        """Run the custom grading function (sync).

        Note: If your custom function is async, use grade_async() instead,
        which will properly await the function.
        """
        try:
            func = self._get_func()
            return func(trace, test_case)
        except Exception as e:
            return GradeResult.error_result(self.name, f"Custom grader error: {e}")

    async def grade_async(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        """Run the custom grading function (async).

        Automatically detects if the custom function is async or sync:
        - Async functions are awaited directly
        - Sync functions run in a thread pool to avoid blocking the event loop

        This allows custom graders to make async API calls (e.g., external
        validation services) without blocking other concurrent evaluations.
        """
        try:
            func = self._get_func()
            if asyncio.iscoroutinefunction(func):
                return await func(trace, test_case)  # type: ignore[no-any-return]
            else:
                return await asyncio.to_thread(func, trace, test_case)
        except Exception as e:
            return GradeResult.error_result(self.name, f"Custom grader error: {e}")
