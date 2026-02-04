"""Base grader classes."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from evaldeck.results import GradeResult, GradeStatus

if TYPE_CHECKING:
    from evaldeck.test_case import EvalCase
    from evaldeck.trace import Trace


class BaseGrader(ABC):
    """Base class for all graders.

    Graders evaluate a trace against expected behavior and return a grade result.
    Supports both sync and async evaluation.

    Async behavior:
        - Default grade_async() runs sync grade() in a thread pool
        - Override grade_async() for true async I/O (e.g., LLMGrader)
        - When using Evaluator.evaluate_async(), all graders run concurrently

    Creating a custom async grader::

        class MyAPIGrader(BaseGrader):
            name = "my_api"

            def grade(self, trace, test_case):
                # Sync fallback (blocking)
                return requests.post(...).json()

            async def grade_async(self, trace, test_case):
                # Async implementation (non-blocking)
                async with httpx.AsyncClient() as client:
                    response = await client.post(...)
                    return GradeResult.from_api(response.json())
    """

    name: str = "base"

    @abstractmethod
    def grade(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        """Evaluate the trace and return a grade result.

        Args:
            trace: The execution trace to evaluate.
            test_case: The test case with expected behavior.

        Returns:
            GradeResult indicating pass/fail and details.
        """
        pass

    async def grade_async(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        """Async version of grade.

        Default implementation runs sync grade() in a thread pool.
        Override this method for true async behavior (e.g., async API calls).

        Args:
            trace: The execution trace to evaluate.
            test_case: The test case with expected behavior.

        Returns:
            GradeResult indicating pass/fail and details.
        """
        return await asyncio.to_thread(self.grade, trace, test_case)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


class CompositeGrader(BaseGrader):
    """A grader that combines multiple graders.

    By default, all graders must pass for the composite to pass.
    """

    name = "composite"

    def __init__(
        self,
        graders: list[BaseGrader],
        require_all: bool = True,
    ) -> None:
        """Initialize composite grader.

        Args:
            graders: List of graders to run.
            require_all: If True, all must pass. If False, any can pass.
        """
        self.graders = graders
        self.require_all = require_all

    def grade(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        """Run all graders and combine results."""
        results: list[GradeResult] = []
        for grader in self.graders:
            result = grader.grade(trace, test_case)
            results.append(result)

        return self._combine_results(results)

    async def grade_async(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        """Run all graders concurrently and combine results."""
        tasks = [grader.grade_async(trace, test_case) for grader in self.graders]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        grade_results: list[GradeResult] = []
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                grade_results.append(
                    GradeResult.error_result(self.graders[i].name, f"Grader error: {result}")
                )
            else:
                grade_results.append(result)

        return self._combine_results(grade_results)

    def _combine_results(self, results: list[GradeResult]) -> GradeResult:
        """Combine multiple grader results into one."""
        passed_count = sum(1 for r in results if r.passed)
        total = len(results)

        if self.require_all:
            # All must pass
            all_passed = passed_count == total
            status = GradeStatus.PASS if all_passed else GradeStatus.FAIL
            message = f"{passed_count}/{total} graders passed"
        else:
            # Any can pass
            any_passed = passed_count > 0
            status = GradeStatus.PASS if any_passed else GradeStatus.FAIL
            message = f"{passed_count}/{total} graders passed (require any)"

        return GradeResult(
            grader_name=self.name,
            status=status,
            message=message,
            details={"results": [r.model_dump() for r in results]},
        )
