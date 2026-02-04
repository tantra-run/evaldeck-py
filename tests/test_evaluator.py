"""Tests for evaluator module."""

import asyncio
import time

import pytest

from evaldeck import (
    EvalCase,
    EvalSuite,
    Evaluator,
    ExpectedBehavior,
    GradeResult,
    GradeStatus,
    Step,
    Trace,
    Turn,
)


class TestEvaluator:
    """Tests for Evaluator class."""

    def test_evaluate_passing_trace(self, simple_trace: Trace, simple_test_case: EvalCase) -> None:
        """Test evaluating a trace that should pass."""
        evaluator = Evaluator()
        result = evaluator.evaluate(simple_trace, simple_test_case)

        assert result.passed
        assert result.status == GradeStatus.PASS
        assert len(result.grades) > 0
        assert all(g.passed for g in result.grades)

    def test_evaluate_failing_trace(self, failing_trace: Trace, simple_test_case: EvalCase) -> None:
        """Test evaluating a trace that should fail."""
        evaluator = Evaluator()
        result = evaluator.evaluate(failing_trace, simple_test_case)

        assert not result.passed
        assert result.status == GradeStatus.FAIL
        assert len(result.failed_grades) > 0

    def test_metrics_calculated(self, simple_trace: Trace, simple_test_case: EvalCase) -> None:
        """Test that metrics are calculated."""
        evaluator = Evaluator()
        result = evaluator.evaluate(simple_trace, simple_test_case)

        assert len(result.metrics) > 0

        # Find step count metric
        step_metric = next(
            (m for m in result.metrics if m.metric_name == "step_count"),
            None,
        )
        assert step_metric is not None
        assert step_metric.value == 2  # Two tool calls

    def test_auto_builds_graders_from_expected(self) -> None:
        """Test that graders are automatically built from expected behavior."""
        trace = Trace(input="test", output="result with keyword")
        trace.add_step(Step.tool_call("tool1", {}))

        test_case = EvalCase(
            name="test",
            turns=[
                Turn(
                    user="test",
                    expected=ExpectedBehavior(
                        output_contains=["keyword"],
                        tools_called=["tool1"],
                        max_steps=10,
                    ),
                )
            ],
        )

        evaluator = Evaluator()
        result = evaluator.evaluate(trace, test_case)

        # Should have graders for contains, tool_called, and max_steps
        grader_names = [g.grader_name for g in result.grades]
        assert "contains" in grader_names
        assert "tool_called" in grader_names
        assert "max_steps" in grader_names

    def test_custom_graders(self) -> None:
        """Test using custom graders."""
        from evaldeck.graders import ContainsGrader

        trace = Trace(input="test", output="custom output")
        test_case = EvalCase(name="test", turns=[Turn(user="test")])

        custom_grader = ContainsGrader(values=["custom"])
        evaluator = Evaluator(graders=[custom_grader])
        result = evaluator.evaluate(trace, test_case)

        assert result.passed
        assert len(result.grades) == 1
        assert result.grades[0].grader_name == "contains"

    def test_duration_tracked(self, simple_trace: Trace, simple_test_case: EvalCase) -> None:
        """Test that evaluation duration is tracked."""
        evaluator = Evaluator()
        result = evaluator.evaluate(simple_trace, simple_test_case)

        assert result.duration_ms is not None
        assert result.duration_ms >= 0
        assert result.started_at is not None
        assert result.completed_at is not None


class TestEvaluatorEdgeCases:
    """Edge case tests for Evaluator."""

    def test_empty_trace(self) -> None:
        """Test evaluating an empty trace."""
        trace = Trace(input="test", output="")
        test_case = EvalCase(
            name="test",
            turns=[Turn(user="test", expected=ExpectedBehavior(task_completed=True))],
        )

        evaluator = Evaluator()
        result = evaluator.evaluate(trace, test_case)

        # Should fail because output is empty
        assert not result.passed

    def test_no_expected_behavior(self) -> None:
        """Test evaluating with no expected behavior defined."""
        trace = Trace(input="test", output="some output")
        test_case = EvalCase(name="test", turns=[Turn(user="test")])

        evaluator = Evaluator()
        result = evaluator.evaluate(trace, test_case)

        # Should pass with default task completion check
        assert result.passed

    def test_trace_with_errors(self) -> None:
        """Test evaluating a trace with step errors."""
        from evaldeck.trace import TraceStatus

        trace = Trace(input="test", output=None, status=TraceStatus.ERROR)

        test_case = EvalCase(
            name="test",
            turns=[Turn(user="test", expected=ExpectedBehavior(task_completed=True))],
        )

        evaluator = Evaluator()
        result = evaluator.evaluate(trace, test_case)

        assert not result.passed


class TestAsyncGraders:
    """Tests for async grader execution."""

    @pytest.mark.asyncio
    async def test_evaluate_async_runs_graders_concurrently(self) -> None:
        """Test that evaluate_async runs graders concurrently."""
        from evaldeck.graders import BaseGrader

        grader_times: list[float] = []

        class SlowGrader(BaseGrader):
            name = "slow"

            def __init__(self, delay: float, grader_id: int):
                self.delay = delay
                self.grader_id = grader_id

            def grade(self, trace, test_case):
                import time

                time.sleep(self.delay)
                return GradeResult.passed_result(f"slow_{self.grader_id}", "passed")

            async def grade_async(self, trace, test_case):
                start = time.time()
                await asyncio.sleep(self.delay)
                grader_times.append(time.time() - start)
                return GradeResult.passed_result(f"slow_{self.grader_id}", "passed")

        # Create 3 slow graders, each taking 0.05s
        graders = [SlowGrader(0.05, i) for i in range(3)]

        trace = Trace(input="test", output="result")
        test_case = EvalCase(name="test", turns=[Turn(user="test")])

        evaluator = Evaluator(graders=graders)

        start = time.time()
        result = await evaluator.evaluate_async(trace, test_case)
        total_time = time.time() - start

        # All graders should have run
        assert len(result.grades) == 3
        assert all(g.passed for g in result.grades)

        # Should complete in ~0.05s (concurrent), not ~0.15s (sequential)
        assert total_time < 0.1  # Allow some margin

    @pytest.mark.asyncio
    async def test_base_grader_grade_async_wraps_sync(self) -> None:
        """Test that BaseGrader.grade_async wraps sync grade() by default."""
        from evaldeck.graders import ContainsGrader

        grader = ContainsGrader(values=["hello"])
        trace = Trace(input="test", output="hello world")
        test_case = EvalCase(name="test", turns=[Turn(user="test")])

        # Async call should work using the default wrapper
        result = await grader.grade_async(trace, test_case)
        assert result.passed

    @pytest.mark.asyncio
    async def test_composite_grader_async_runs_concurrently(self) -> None:
        """Test that CompositeGrader.grade_async runs sub-graders concurrently."""
        from evaldeck.graders import BaseGrader, CompositeGrader

        execution_order: list[int] = []

        class OrderedGrader(BaseGrader):
            name = "ordered"

            def __init__(self, grader_id: int, delay: float):
                self.grader_id = grader_id
                self.delay = delay

            def grade(self, trace, test_case):
                return GradeResult.passed_result(f"g{self.grader_id}", "passed")

            async def grade_async(self, trace, test_case):
                await asyncio.sleep(self.delay)
                execution_order.append(self.grader_id)
                return GradeResult.passed_result(f"g{self.grader_id}", "passed")

        # Grader 0 has longest delay, grader 2 has shortest
        graders = [
            OrderedGrader(0, 0.03),
            OrderedGrader(1, 0.02),
            OrderedGrader(2, 0.01),
        ]
        composite = CompositeGrader(graders)

        trace = Trace(input="test", output="result")
        test_case = EvalCase(name="test", turns=[Turn(user="test")])

        result = await composite.grade_async(trace, test_case)

        assert result.passed
        # If concurrent, shorter delays finish first
        assert execution_order == [2, 1, 0]


class TestConcurrentExecution:
    """Tests for concurrent test execution."""

    def test_evaluate_suite_with_sync_agent(self) -> None:
        """Test evaluate_suite with sync agent function."""
        from evaldeck.trace import Message

        def sync_agent(input: str, history: list[Message] | None = None) -> Trace:
            trace = Trace(input=input, output=f"Response to: {input}")
            return trace

        suite = EvalSuite(
            name="test_suite",
            test_cases=[
                EvalCase(name="test1", turns=[Turn(user="hello")]),
                EvalCase(name="test2", turns=[Turn(user="world")]),
            ],
        )

        evaluator = Evaluator()
        result = evaluator.evaluate_suite(suite, sync_agent)

        assert result.total == 2
        assert result.passed == 2

    @pytest.mark.asyncio
    async def test_evaluate_suite_async_with_async_agent(self) -> None:
        """Test evaluate_suite_async with async agent function."""
        from evaldeck.trace import Message

        async def async_agent(input: str, history: list[Message] | None = None) -> Trace:
            await asyncio.sleep(0.01)  # Simulate async work
            trace = Trace(input=input, output=f"Response to: {input}")
            return trace

        suite = EvalSuite(
            name="test_suite",
            test_cases=[
                EvalCase(name="test1", turns=[Turn(user="hello")]),
                EvalCase(name="test2", turns=[Turn(user="world")]),
            ],
        )

        evaluator = Evaluator()
        result = await evaluator.evaluate_suite_async(suite, async_agent)

        assert result.total == 2
        assert result.passed == 2

    @pytest.mark.asyncio
    async def test_concurrent_execution_faster_than_sequential(self) -> None:
        """Test that concurrent execution is faster than sequential."""
        from evaldeck.trace import Message

        delay = 0.05  # 50ms per test

        async def slow_agent(input: str, history: list[Message] | None = None) -> Trace:
            await asyncio.sleep(delay)
            return Trace(input=input, output="done")

        suite = EvalSuite(
            name="test_suite",
            test_cases=[
                EvalCase(name=f"test{i}", turns=[Turn(user=f"input{i}")]) for i in range(5)
            ],
        )

        evaluator = Evaluator()

        # Run with unlimited concurrency
        start = time.time()
        result = await evaluator.evaluate_suite_async(suite, slow_agent, max_concurrent=0)
        concurrent_time = time.time() - start

        assert result.total == 5
        # Should complete in roughly delay time (all run concurrently)
        # rather than 5 * delay time (sequential)
        assert concurrent_time < delay * 3  # Allow some margin

    @pytest.mark.asyncio
    async def test_max_concurrent_limits_parallelism(self) -> None:
        """Test that max_concurrent limits the number of parallel tests."""
        from evaldeck.trace import Message

        active_count = 0
        max_seen = 0

        async def counting_agent(input: str, history: list[Message] | None = None) -> Trace:
            nonlocal active_count, max_seen
            active_count += 1
            max_seen = max(max_seen, active_count)
            await asyncio.sleep(0.02)
            active_count -= 1
            return Trace(input=input, output="done")

        suite = EvalSuite(
            name="test_suite",
            test_cases=[
                EvalCase(name=f"test{i}", turns=[Turn(user=f"input{i}")]) for i in range(10)
            ],
        )

        evaluator = Evaluator()
        await evaluator.evaluate_suite_async(suite, counting_agent, max_concurrent=3)

        # Should never exceed 3 concurrent
        assert max_seen <= 3

    @pytest.mark.asyncio
    async def test_results_preserve_original_order(self) -> None:
        """Test that results maintain original test case order."""
        import random

        from evaldeck.trace import Message

        async def random_delay_agent(input: str, history: list[Message] | None = None) -> Trace:
            # Random delay so completion order differs from input order
            await asyncio.sleep(random.uniform(0.001, 0.02))
            return Trace(input=input, output=input)

        suite = EvalSuite(
            name="test_suite",
            test_cases=[
                EvalCase(name=f"test{i}", turns=[Turn(user=f"input{i}")]) for i in range(10)
            ],
        )

        evaluator = Evaluator()
        result = await evaluator.evaluate_suite_async(suite, random_delay_agent)

        # Results should be in original order
        for i, eval_result in enumerate(result.results):
            assert eval_result.test_case_name == f"test{i}"

    @pytest.mark.asyncio
    async def test_on_result_callback_called_for_each_test(self) -> None:
        """Test that on_result callback is called for each test."""
        from evaldeck.trace import Message

        results_received: list[str] = []

        def on_result(result) -> None:
            results_received.append(result.test_case_name)

        async def agent(input: str, history: list[Message] | None = None) -> Trace:
            return Trace(input=input, output="done")

        suite = EvalSuite(
            name="test_suite",
            test_cases=[
                EvalCase(name="test1", turns=[Turn(user="a")]),
                EvalCase(name="test2", turns=[Turn(user="b")]),
                EvalCase(name="test3", turns=[Turn(user="c")]),
            ],
        )

        evaluator = Evaluator()
        await evaluator.evaluate_suite_async(suite, agent, on_result=on_result)

        assert len(results_received) == 3
        assert set(results_received) == {"test1", "test2", "test3"}

    @pytest.mark.asyncio
    async def test_error_in_one_test_doesnt_affect_others(self) -> None:
        """Test that an error in one test doesn't stop others."""
        from evaldeck.trace import Message

        async def failing_agent(input: str, history: list[Message] | None = None) -> Trace:
            if "fail" in input:
                raise ValueError("Intentional failure")
            return Trace(input=input, output="success")

        suite = EvalSuite(
            name="test_suite",
            test_cases=[
                EvalCase(name="test1", turns=[Turn(user="pass")]),
                EvalCase(name="test2", turns=[Turn(user="fail")]),
                EvalCase(name="test3", turns=[Turn(user="pass")]),
            ],
        )

        evaluator = Evaluator()
        result = await evaluator.evaluate_suite_async(suite, failing_agent)

        assert result.total == 3
        assert result.passed == 2
        assert result.errors == 1

        # Check the error result
        error_result = next(r for r in result.results if r.test_case_name == "test2")
        assert error_result.status == GradeStatus.ERROR
        # Error message is in the grade message for multi-turn evaluation
        assert any("Intentional failure" in g.message for g in error_result.grades if g.message)
