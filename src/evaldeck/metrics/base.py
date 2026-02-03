"""Base metric class."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from evaldeck.results import MetricResult

if TYPE_CHECKING:
    from evaldeck.test_case import EvalCase
    from evaldeck.trace import Trace


class BaseMetric(ABC):
    """Base class for all metrics.

    Metrics calculate quantitative measurements from traces.
    Unlike graders, metrics don't pass/fail - they just measure.

    Supports both sync and async calculation. Override calculate_async()
    for metrics that need to make async I/O calls (e.g., fetching external
    benchmark data).
    """

    name: str = "base"
    unit: str | None = None

    @abstractmethod
    def calculate(self, trace: Trace, test_case: EvalCase | None = None) -> MetricResult:
        """Calculate the metric value (sync).

        Args:
            trace: The execution trace to measure.
            test_case: Optional test case for context.

        Returns:
            MetricResult with the calculated value.
        """
        pass

    async def calculate_async(
        self, trace: Trace, test_case: EvalCase | None = None
    ) -> MetricResult:
        """Calculate the metric value (async).

        Default implementation runs sync calculate() in a thread pool.
        Override this method for true async behavior (e.g., async API calls
        for external benchmarking services).

        Args:
            trace: The execution trace to measure.
            test_case: Optional test case for context.

        Returns:
            MetricResult with the calculated value.
        """
        return await asyncio.to_thread(self.calculate, trace, test_case)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
