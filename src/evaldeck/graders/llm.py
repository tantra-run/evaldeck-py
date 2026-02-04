"""LLM-based graders (model-as-judge)."""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING, Any

from evaldeck.graders.base import BaseGrader
from evaldeck.results import GradeResult, GradeStatus

if TYPE_CHECKING:
    from evaldeck.test_case import EvalCase
    from evaldeck.trace import Trace


class LLMGrader(BaseGrader):
    """Use an LLM to grade agent output.

    This grader sends the trace/output to an LLM with a grading prompt
    and parses the response to determine pass/fail.

    Supports OpenAI and Anthropic APIs (user provides their own API key).
    """

    name = "llm"

    # Default grading prompt template
    DEFAULT_PROMPT = """You are evaluating an AI agent's response.

User Input: {input}
Agent Output: {output}

Task: {task}

Evaluate whether the agent's response meets the requirements.
Respond with exactly one of: PASS or FAIL
Then provide a brief explanation.

Format:
VERDICT: PASS or FAIL
REASON: Your explanation
"""

    def __init__(
        self,
        prompt: str | None = None,
        model: str = "gpt-4o-mini",
        provider: str | None = None,
        api_key: str | None = None,
        threshold: float | None = None,
        temperature: float = 0.0,
        task: str | None = None,
    ) -> None:
        """Initialize LLM grader.

        Args:
            prompt: Custom grading prompt. Use {input}, {output}, {trace} placeholders.
            model: Model to use (e.g., "gpt-4o-mini", "claude-3-haiku-20240307").
            provider: API provider ("openai" or "anthropic"). Auto-detected from model.
            api_key: API key. If None, uses environment variable.
            threshold: Score threshold for pass (if using scored evaluation).
            temperature: Model temperature.
            task: Task description for the default prompt.
        """
        self.prompt_template = prompt or self.DEFAULT_PROMPT
        self.model = model
        self.provider = provider or self._detect_provider(model)
        self.api_key = api_key
        self.threshold = threshold
        self.temperature = temperature
        self.task = task or "Determine if the agent completed the task correctly."

    def _detect_provider(self, model: str) -> str:
        """Detect API provider from model name."""
        if model.startswith("claude"):
            return "anthropic"
        return "openai"

    def _get_api_key(self) -> str:
        """Get API key from init or environment."""
        if self.api_key:
            return self.api_key

        if self.provider == "anthropic":
            key = os.environ.get("ANTHROPIC_API_KEY")
            if key:
                return key
            raise ValueError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable."
            )

        # Default to OpenAI
        key = os.environ.get("OPENAI_API_KEY")
        if key:
            return key
        raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")

    def _format_prompt(self, trace: Trace, test_case: EvalCase) -> str:
        """Format the grading prompt with trace data."""
        # Build trace summary
        trace_summary = self._build_trace_summary(trace)

        return self.prompt_template.format(
            input=trace.input,
            output=trace.output or "(no output)",
            trace=trace_summary,
            task=self.task,
            test_case_name=test_case.name,
            expected=str(test_case.expected.model_dump(exclude_none=True)),
        )

    def _build_trace_summary(self, trace: Trace) -> str:
        """Build a human-readable trace summary."""
        lines = ["Execution Trace:"]
        for i, step in enumerate(trace.steps, 1):
            if step.type.value == "tool_call":
                lines.append(f"  {i}. Tool: {step.tool_name}({step.tool_args})")
                if step.tool_result:
                    result_str = str(step.tool_result)[:200]
                    lines.append(f"      Result: {result_str}")
            elif step.type.value == "llm_call":
                output_preview = (step.output or "")[:100]
                lines.append(f"  {i}. LLM: {output_preview}...")
            elif step.type.value == "reasoning":
                reasoning_preview = (step.reasoning_text or "")[:100]
                lines.append(f"  {i}. Reasoning: {reasoning_preview}...")
        return "\n".join(lines)

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API (sync)."""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "OpenAI package not installed. Run: pip install evaldeck[openai]"
            ) from None

        client = OpenAI(api_key=self._get_api_key())
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
        )
        return response.choices[0].message.content or ""

    async def _call_openai_async(self, prompt: str) -> str:
        """Call OpenAI API (async)."""
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "OpenAI package not installed. Run: pip install evaldeck[openai]"
            ) from None

        client = AsyncOpenAI(api_key=self._get_api_key())
        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
        )
        return response.choices[0].message.content or ""

    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API (sync)."""
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "Anthropic package not installed. Run: pip install evaldeck[anthropic]"
            ) from None

        client = Anthropic(api_key=self._get_api_key())
        response = client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text  # type: ignore[no-any-return]

    async def _call_anthropic_async(self, prompt: str) -> str:
        """Call Anthropic API (async)."""
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            raise ImportError(
                "Anthropic package not installed. Run: pip install evaldeck[anthropic]"
            ) from None

        client = AsyncAnthropic(api_key=self._get_api_key())
        response = await client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text  # type: ignore[no-any-return]

    def _parse_response(self, response: str) -> tuple[GradeStatus, str, float | None]:
        """Parse LLM response to extract verdict.

        Returns:
            Tuple of (status, reason, score).
        """
        response_upper = response.upper()

        # Look for explicit VERDICT: PASS/FAIL
        verdict_match = re.search(r"VERDICT:\s*(PASS|FAIL)", response_upper)
        if verdict_match:
            status = GradeStatus.PASS if verdict_match.group(1) == "PASS" else GradeStatus.FAIL
        elif "PASS" in response_upper and "FAIL" not in response_upper:
            status = GradeStatus.PASS
        elif "FAIL" in response_upper:
            status = GradeStatus.FAIL
        else:
            # Couldn't determine, default to fail
            status = GradeStatus.FAIL

        # Extract reason
        reason_match = re.search(r"REASON:\s*(.+)", response, re.IGNORECASE | re.DOTALL)
        reason = reason_match.group(1).strip() if reason_match else response[:200]

        # Extract score if present
        score = None
        score_match = re.search(r"SCORE:\s*(\d+(?:\.\d+)?)", response)
        if score_match:
            score = float(score_match.group(1))
            # Normalize to 0-1 if needed
            if score > 1:
                score = score / 10 if score <= 10 else score / 100

        return status, reason, score

    def grade(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        """Grade the trace using an LLM (sync)."""
        try:
            # Format prompt
            prompt = self._format_prompt(trace, test_case)

            # Call LLM
            if self.provider == "anthropic":
                response = self._call_anthropic(prompt)
            else:
                response = self._call_openai(prompt)

            return self._build_result(response)

        except Exception as e:
            return GradeResult.error_result(self.name, f"LLM grader error: {e}")

    async def grade_async(self, trace: Trace, test_case: EvalCase) -> GradeResult:
        """Grade the trace using an LLM (async).

        Uses async API clients for better performance in concurrent evaluation.
        """
        try:
            # Format prompt
            prompt = self._format_prompt(trace, test_case)

            # Call LLM asynchronously
            if self.provider == "anthropic":
                response = await self._call_anthropic_async(prompt)
            else:
                response = await self._call_openai_async(prompt)

            return self._build_result(response)

        except Exception as e:
            return GradeResult.error_result(self.name, f"LLM grader error: {e}")

    def _build_result(self, response: str) -> GradeResult:
        """Build GradeResult from LLM response."""
        # Parse response
        status, reason, score = self._parse_response(response)

        # Apply threshold if score-based
        if self.threshold is not None and score is not None:
            status = GradeStatus.PASS if score >= self.threshold else GradeStatus.FAIL

        return GradeResult(
            grader_name=self.name,
            status=status,
            score=score,
            message=reason,
            details={
                "model": self.model,
                "raw_response": response,
            },
        )


class LLMRubricGrader(LLMGrader):
    """LLM grader with a detailed scoring rubric."""

    name = "llm_rubric"

    RUBRIC_PROMPT = """You are evaluating an AI agent's response using a scoring rubric.

User Input: {input}
Agent Output: {output}

Scoring Rubric:
{rubric}

For each criterion, provide a score from 1-5 where:
1 = Poor, 2 = Below Average, 3 = Average, 4 = Good, 5 = Excellent

Format your response as:
CRITERION: criterion_name
SCORE: X
REASON: explanation

After scoring all criteria, provide:
TOTAL_SCORE: X/Y
VERDICT: PASS or FAIL
"""

    def __init__(
        self,
        rubric: dict[str, str],
        pass_threshold: float = 0.7,
        **kwargs: Any,
    ) -> None:
        """Initialize rubric grader.

        Args:
            rubric: Dict mapping criterion names to descriptions.
            pass_threshold: Minimum score ratio to pass (0-1).
            **kwargs: Passed to LLMGrader.
        """
        self.rubric = rubric
        self.pass_threshold = pass_threshold
        super().__init__(**kwargs)
        self.prompt_template = self.RUBRIC_PROMPT

    def _format_prompt(self, trace: Trace, test_case: EvalCase) -> str:
        """Format prompt with rubric."""
        rubric_text = "\n".join(
            f"- {name}: {description}" for name, description in self.rubric.items()
        )
        return self.prompt_template.format(
            input=trace.input,
            output=trace.output or "(no output)",
            rubric=rubric_text,
        )
