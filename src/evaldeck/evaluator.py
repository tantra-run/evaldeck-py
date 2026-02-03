"""Main evaluation engine."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from typing import TYPE_CHECKING, Any

from evaldeck.graders import (
    BaseGrader,
    ContainsGrader,
    LLMGrader,
    MaxLLMCallsGrader,
    MaxStepsGrader,
    MaxToolCallsGrader,
    TaskCompletedGrader,
    ToolCalledGrader,
    ToolNotCalledGrader,
    ToolOrderGrader,
)
from evaldeck.graders.code import NotContainsGrader
from evaldeck.metrics import (
    BaseMetric,
    DurationMetric,
    StepCountMetric,
    TokenUsageMetric,
    ToolCallCountMetric,
)
from evaldeck.results import (
    EvaluationResult,
    GradeResult,
    GradeStatus,
    RunResult,
    SuiteResult,
)

if TYPE_CHECKING:
    from evaldeck.config import EvaldeckConfig
    from evaldeck.test_case import EvalCase, EvalSuite
    from evaldeck.trace import Trace


class Evaluator:
    """Main evaluation engine.

    Evaluates agent traces against test cases using graders and metrics.

    Choosing sync vs async methods:

    Use **evaluate()** (sync) when:
        - Running a single quick evaluation with code-based graders
        - Your graders are all CPU-bound (ContainsGrader, RegexGrader, etc.)
        - You're in a sync context without an event loop

    Use **evaluate_async()** when:
        - Using LLMGrader or other I/O-bound graders
        - Running multiple graders that make API calls
        - You want concurrent grader execution for better throughput
        - Your custom graders/metrics make async API calls

    Use **evaluate_suite_async()** when:
        - Running multiple test cases (concurrent execution)
        - Your agent function is async
        - You want to control concurrency with max_concurrent

    Performance comparison::

        # Sync: graders run sequentially
        # 3 LLMGraders × 2 seconds each = ~6 seconds total
        result = evaluator.evaluate(trace, test_case)

        # Async: graders run concurrently
        # 3 LLMGraders × 2 seconds each = ~2 seconds total
        result = await evaluator.evaluate_async(trace, test_case)
    """

    def __init__(
        self,
        graders: list[BaseGrader] | None = None,
        metrics: list[BaseMetric] | None = None,
        config: EvaldeckConfig | None = None,
    ) -> None:
        """Initialize the evaluator.

        Args:
            graders: List of graders to use. If None, uses defaults based on test case.
            metrics: List of metrics to calculate. If None, uses defaults.
            config: Evaldeck configuration.
        """
        self.graders = graders
        self.metrics = metrics or self._default_metrics()
        self.config = config

    def _default_metrics(self) -> list[BaseMetric]:
        """Get default metrics."""
        return [
            StepCountMetric(),
            TokenUsageMetric(),
            ToolCallCountMetric(),
            DurationMetric(),
        ]

    def _build_graders(self, test_case: EvalCase) -> list[BaseGrader]:
        """Build graders from test case expected behavior."""
        graders: list[BaseGrader] = []
        expected = test_case.expected

        # Add graders based on expected behavior
        if expected.output_contains:
            graders.append(ContainsGrader())

        if expected.output_not_contains:
            graders.append(NotContainsGrader())

        if expected.tools_called:
            graders.append(ToolCalledGrader())

        if expected.tools_not_called:
            graders.append(ToolNotCalledGrader())

        if expected.tool_call_order:
            graders.append(ToolOrderGrader())

        if expected.max_steps is not None:
            graders.append(MaxStepsGrader())

        if expected.max_tool_calls is not None:
            graders.append(MaxToolCallsGrader())

        if expected.max_llm_calls is not None:
            graders.append(MaxLLMCallsGrader())

        if expected.task_completed is not None:
            graders.append(TaskCompletedGrader())

        # Add graders from test case config
        for grader_config in test_case.graders:
            grader = self._create_grader_from_config(grader_config)
            if grader:
                graders.append(grader)

        # If no graders, add basic task completion check
        if not graders:
            graders.append(TaskCompletedGrader())

        return graders

    def _create_grader_from_config(self, config: Any) -> BaseGrader | None:
        """Create a grader from configuration."""
        from evaldeck.test_case import GraderConfig

        if isinstance(config, GraderConfig):
            grader_type = config.type.lower()

            if grader_type == "llm":
                return LLMGrader(
                    prompt=config.prompt,
                    model=config.model or "gpt-4o-mini",
                    threshold=config.threshold,
                )
            elif grader_type == "contains":
                return ContainsGrader(**config.params)
            elif grader_type == "tool_called":
                return ToolCalledGrader(**config.params)
            # Add more grader types as needed

        return None

    def evaluate(
        self,
        trace: Trace,
        test_case: EvalCase,
    ) -> EvaluationResult:
        """Evaluate a single trace against a test case (sync).

        Runs graders and metrics sequentially. Best for:
        - Code-based graders (ContainsGrader, RegexGrader, etc.)
        - Quick evaluations without I/O-bound operations
        - Contexts without an async event loop

        For I/O-bound graders (LLMGrader) or concurrent execution,
        use evaluate_async() instead.

        Args:
            trace: The execution trace to evaluate.
            test_case: The test case defining expected behavior.

        Returns:
            EvaluationResult with grades and metrics.
        """
        started_at = datetime.now()

        # Build graders
        graders = self.graders if self.graders else self._build_graders(test_case)

        # Create result
        result = EvaluationResult(
            test_case_name=test_case.name,
            status=GradeStatus.PASS,  # Start optimistic
            started_at=started_at,
            trace_id=trace.id,
        )

        # Run graders sequentially
        for grader in graders:
            try:
                grade = grader.grade(trace, test_case)
                result.add_grade(grade)
            except Exception as e:
                result.add_grade(GradeResult.error_result(grader.name, f"Grader error: {e}"))

        # Calculate metrics
        for metric in self.metrics:
            try:
                metric_result = metric.calculate(trace, test_case)
                result.add_metric(metric_result)
            except Exception:
                pass  # Metrics are optional, don't fail on error

        # Finalize
        result.completed_at = datetime.now()
        result.duration_ms = (result.completed_at - started_at).total_seconds() * 1000

        return result

    async def evaluate_async(
        self,
        trace: Trace,
        test_case: EvalCase,
    ) -> EvaluationResult:
        """Evaluate a single trace against a test case (async).

        Runs graders and metrics concurrently using asyncio.gather().
        Recommended for:
        - LLMGrader (makes async API calls to OpenAI/Anthropic)
        - Custom async graders that call external services
        - Custom async metrics that fetch benchmark data
        - Any scenario with multiple I/O-bound operations

        Performance benefit: With 3 LLMGraders each taking 2 seconds,
        sync evaluate() takes ~6 seconds while evaluate_async() takes ~2 seconds.

        Code-based graders (ContainsGrader, etc.) automatically run in a
        thread pool via asyncio.to_thread() to avoid blocking the event loop.

        Args:
            trace: The execution trace to evaluate.
            test_case: The test case defining expected behavior.

        Returns:
            EvaluationResult with grades and metrics.
        """
        started_at = datetime.now()

        # Build graders
        graders = self.graders if self.graders else self._build_graders(test_case)

        # Create result
        result = EvaluationResult(
            test_case_name=test_case.name,
            status=GradeStatus.PASS,  # Start optimistic
            started_at=started_at,
            trace_id=trace.id,
        )

        # Run graders concurrently
        async def run_grader(grader):
            try:
                return await grader.grade_async(trace, test_case)
            except Exception as e:
                return GradeResult.error_result(grader.name, f"Grader error: {e}")

        grade_results = await asyncio.gather(*[run_grader(g) for g in graders])

        for grade in grade_results:
            result.add_grade(grade)

        # Calculate metrics concurrently (supports async custom metrics)
        async def run_metric(metric):
            try:
                return await metric.calculate_async(trace, test_case)
            except Exception:
                return None  # Metrics are optional, don't fail on error

        metric_results = await asyncio.gather(*[run_metric(m) for m in self.metrics])

        for metric_result in metric_results:
            if metric_result is not None:
                result.add_metric(metric_result)

        # Finalize
        result.completed_at = datetime.now()
        result.duration_ms = (result.completed_at - started_at).total_seconds() * 1000

        return result

    def evaluate_suite(
        self,
        suite: EvalSuite,
        agent_func: Callable[[str], Trace] | Callable[[str], Awaitable[Trace]],
        on_result: Callable[[EvaluationResult], None] | None = None,
        max_concurrent: int = 0,
    ) -> SuiteResult:
        """Evaluate all test cases in a suite (sync wrapper).

        Args:
            suite: The test suite to evaluate.
            agent_func: Function that takes input string and returns a Trace.
                Can be sync or async.
            on_result: Optional callback called after each test case.
            max_concurrent: Maximum concurrent tests. 0 = unlimited.

        Returns:
            SuiteResult with all evaluation results.
        """
        return asyncio.run(self.evaluate_suite_async(suite, agent_func, on_result, max_concurrent))

    async def evaluate_suite_async(
        self,
        suite: EvalSuite,
        agent_func: Callable[[str], Trace] | Callable[[str], Awaitable[Trace]],
        on_result: Callable[[EvaluationResult], None] | None = None,
        max_concurrent: int = 0,
    ) -> SuiteResult:
        """Evaluate all test cases in a suite concurrently.

        Args:
            suite: The test suite to evaluate.
            agent_func: Function that takes input string and returns a Trace.
                Can be sync or async.
            on_result: Optional callback called after each test case.
            max_concurrent: Maximum concurrent tests. 0 = unlimited.

        Returns:
            SuiteResult with all evaluation results.
        """
        suite_result = SuiteResult(
            suite_name=suite.name,
            started_at=datetime.now(),
        )

        # Detect if agent is async
        is_async = asyncio.iscoroutinefunction(agent_func)

        # Create semaphore if limiting concurrency
        semaphore = asyncio.Semaphore(max_concurrent) if max_concurrent > 0 else None

        @asynccontextmanager
        async def maybe_semaphore():
            """Context manager that optionally acquires semaphore."""
            if semaphore:
                async with semaphore:
                    yield
            else:
                yield

        async def run_test(index: int, test_case: EvalCase) -> tuple[int, EvaluationResult]:
            """Run a single test case."""
            async with maybe_semaphore():
                result = await self._evaluate_single_async(test_case, agent_func, is_async)
                if on_result:
                    on_result(result)
                return index, result

        # Run all tests concurrently
        tasks = [run_test(i, tc) for i, tc in enumerate(suite.test_cases)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Add results in original order
        results_by_index: dict[int, EvaluationResult] = {}
        for item in results:
            if isinstance(item, Exception):
                # This shouldn't happen since _evaluate_single_async catches exceptions
                continue
            index, result = item
            results_by_index[index] = result

        for i in range(len(suite.test_cases)):
            if i in results_by_index:
                suite_result.add_result(results_by_index[i])
            else:
                # Handle case where gather returned an exception
                suite_result.add_result(
                    EvaluationResult(
                        test_case_name=suite.test_cases[i].name,
                        status=GradeStatus.ERROR,
                        error="Test execution failed unexpectedly",
                    )
                )

        suite_result.completed_at = datetime.now()
        return suite_result

    async def _evaluate_single_async(
        self,
        test_case: EvalCase,
        agent_func: Callable[[str], Trace] | Callable[[str], Awaitable[Trace]],
        is_async: bool,
    ) -> EvaluationResult:
        """Evaluate a single test case asynchronously.

        Args:
            test_case: The test case to evaluate.
            agent_func: Function to run the agent.
            is_async: Whether agent_func is async.

        Returns:
            EvaluationResult for this test case.
        """
        try:
            if is_async:
                trace = await agent_func(test_case.input)  # type: ignore
            else:
                # Run sync function in thread pool to not block event loop
                trace = await asyncio.to_thread(agent_func, test_case.input)  # type: ignore

            # Use async evaluate to run graders concurrently
            return await self.evaluate_async(trace, test_case)

        except Exception as e:
            return EvaluationResult(
                test_case_name=test_case.name,
                status=GradeStatus.ERROR,
                error=str(e),
            )


class EvaluationRunner:
    """High-level runner for executing evaluations."""

    def __init__(self, config: EvaldeckConfig | None = None) -> None:
        """Initialize the runner.

        Args:
            config: Evaldeck configuration. If None, loads from file.
        """
        if config is None:
            from evaldeck.config import EvaldeckConfig

            config = EvaldeckConfig.load()
        self.config = config
        self.evaluator = Evaluator(config=config)

    def run(
        self,
        suites: list[EvalSuite] | None = None,
        agent_func: Callable[[str], Trace] | Callable[[str], Awaitable[Trace]] | None = None,
        tags: list[str] | None = None,
        on_result: Callable[[EvaluationResult], None] | None = None,
        max_concurrent: int | None = None,
    ) -> RunResult:
        """Run evaluation on multiple suites (sync wrapper).

        Args:
            suites: Test suites to run. If None, discovers from config.
            agent_func: Function to run agent. If None, loads from config.
                Can be sync or async.
            tags: Filter test cases by tags.
            on_result: Callback for each result.
            max_concurrent: Max concurrent tests per suite. None = use config.

        Returns:
            RunResult with all suite results.
        """
        return asyncio.run(self.run_async(suites, agent_func, tags, on_result, max_concurrent))

    async def run_async(
        self,
        suites: list[EvalSuite] | None = None,
        agent_func: Callable[[str], Trace] | Callable[[str], Awaitable[Trace]] | None = None,
        tags: list[str] | None = None,
        on_result: Callable[[EvaluationResult], None] | None = None,
        max_concurrent: int | None = None,
    ) -> RunResult:
        """Run evaluation on multiple suites asynchronously.

        Args:
            suites: Test suites to run. If None, discovers from config.
            agent_func: Function to run agent. If None, loads from config.
                Can be sync or async.
            tags: Filter test cases by tags.
            on_result: Callback for each result.
            max_concurrent: Max concurrent tests per suite. None = use config.

        Returns:
            RunResult with all suite results.
        """
        # Load suites if not provided
        if suites is None:
            suites = self._discover_suites()

        # Load agent function if not provided
        if agent_func is None:
            agent_func = self._load_agent_func()

        # Filter by tags if specified
        if tags:
            suites = [s.filter_by_tags(tags) for s in suites]

        # Determine worker count
        effective_max_concurrent = (
            max_concurrent if max_concurrent is not None else self.config.execution.workers
        )

        # Run evaluation
        run_result = RunResult(
            started_at=datetime.now(),
            config=self.config.model_dump(),
        )

        for suite in suites:
            if not suite.test_cases:
                continue

            suite_result = await self.evaluator.evaluate_suite_async(
                suite=suite,
                agent_func=agent_func,
                on_result=on_result,
                max_concurrent=effective_max_concurrent,
            )
            run_result.add_suite(suite_result)

        run_result.completed_at = datetime.now()
        return run_result

    def _discover_suites(self) -> list[EvalSuite]:
        """Discover test suites from configuration."""
        from pathlib import Path

        from evaldeck.test_case import EvalSuite

        suites = []

        # Use configured suites
        if self.config.suites:
            for suite_config in self.config.suites:
                path = Path(suite_config.path)
                if path.is_dir():
                    suite = EvalSuite.from_directory(path, name=suite_config.name)
                    suites.append(suite)

        # Or discover from test_dir
        else:
            test_dir = Path(self.config.test_dir)
            if test_dir.is_dir():
                # Check for subdirectories (each is a suite)
                subdirs = [d for d in test_dir.iterdir() if d.is_dir()]
                if subdirs:
                    for subdir in subdirs:
                        suite = EvalSuite.from_directory(subdir)
                        suites.append(suite)
                else:
                    # Single suite from test_dir
                    suite = EvalSuite.from_directory(test_dir, name="default")
                    suites.append(suite)

        return suites

    def _load_agent_func(self) -> Callable[[str], Trace]:
        """Load agent function from configuration."""
        import importlib

        agent_config = self.config.agent

        if not agent_config.module or not agent_config.function:
            raise ValueError(
                "Agent module and function must be specified in config or provided directly"
            )

        module = importlib.import_module(agent_config.module)
        func = getattr(module, agent_config.function)
        return func
