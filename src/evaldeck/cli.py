"""Command-line interface for evaldeck."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click
from rich import box
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

from evaldeck.config import EvaldeckConfig, generate_default_config, generate_example_test
from evaldeck.results import EvaluationResult, GradeStatus, RunResult

console = Console()
logger = logging.getLogger("evaldeck")


def setup_logging(verbose: bool) -> None:
    """Configure logging with rich handler."""
    # Only configure evaldeck logger, not root (to avoid noise from other libraries)
    handler = RichHandler(console=console, show_time=False, show_path=False)
    handler.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


@click.group()
@click.version_option()
def main() -> None:
    """Evaldeck - The evaluation framework for AI agents."""
    pass


@main.command()
@click.option("--force", "-f", is_flag=True, help="Overwrite existing files")
def init(force: bool) -> None:
    """Initialize a new evaldeck project."""
    config_path = Path("evaldeck.yaml")
    test_dir = Path("tests/evals")
    example_test = test_dir / "example.yaml"

    # Check for existing files
    if config_path.exists() and not force:
        console.print(f"[yellow]Config file already exists: {config_path}[/yellow]")
        console.print("Use --force to overwrite")
        return

    # Create config
    config_path.write_text(generate_default_config())
    console.print(f"[green]Created:[/green] {config_path}")

    # Create test directory
    test_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"[green]Created:[/green] {test_dir}/")

    # Create example test
    if not example_test.exists() or force:
        example_test.write_text(generate_example_test())
        console.print(f"[green]Created:[/green] {example_test}")

    # Create output directory
    output_dir = Path(".evaldeck")
    output_dir.mkdir(exist_ok=True)

    console.print()
    console.print(
        Panel(
            "[bold]Project initialized![/bold]\n\n"
            "Next steps:\n"
            "1. Edit [cyan]evaldeck.yaml[/cyan] to configure your agent\n"
            "2. Add test cases to [cyan]tests/evals/[/cyan]\n"
            "3. Run [cyan]evaldeck run[/cyan] to evaluate",
            title="Evaldeck",
            border_style="green",
        )
    )


@main.command()
@click.option("--config", "-c", type=click.Path(exists=True), help="Config file path")
@click.option("--suite", "-s", multiple=True, help="Run specific suite(s)")
@click.option("--tag", "-t", multiple=True, help="Filter by tag(s)")
@click.option("--output", "-o", type=click.Choice(["text", "json", "junit"]), default="text")
@click.option("--output-file", type=click.Path(), help="Output file path")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option(
    "--workers",
    "-w",
    type=int,
    default=None,
    help="Max concurrent tests (0=unlimited, 1=sequential). Default: from config or 0",
)
def run(
    config: str | None,
    suite: tuple[str, ...],
    tag: tuple[str, ...],
    output: str,
    output_file: str | None,
    verbose: bool,
    workers: int | None,
) -> None:
    """Run evaluations."""
    setup_logging(verbose)

    try:
        # Load config
        cfg = EvaldeckConfig.load(config)
        logger.debug(f"Loaded config: test_dir={cfg.test_dir}, agent={cfg.agent.module}")
    except FileNotFoundError:
        logger.error("No evaldeck.yaml found. Run 'evaldeck init' first.")
        sys.exit(1)

    console.print("[bold]Evaldeck[/bold] - Running evaluations...\n")

    # Discover test suites
    from evaldeck.evaluator import EvaluationRunner

    runner = EvaluationRunner(config=cfg)

    try:
        suites = runner._discover_suites()
    except Exception as e:
        console.print(f"[red]Error discovering test suites: {e}[/red]")
        sys.exit(1)

    if not suites:
        console.print("[yellow]No test suites found.[/yellow]")
        console.print(f"Add test cases to: {cfg.test_dir}/")
        sys.exit(0)

    # Filter suites if specified
    if suite:
        suites = [s for s in suites if s.name in suite]

    # Count total tests
    total_tests = sum(len(s.test_cases) for s in suites)
    console.print(
        f"Found [cyan]{total_tests}[/cyan] test(s) in [cyan]{len(suites)}[/cyan] suite(s)\n"
    )

    # Check if agent is configured
    if not cfg.agent.module or not cfg.agent.function:
        logger.warning("No agent configured in evaldeck.yaml")
        logger.info("Running in dry-run mode (no agent execution)\n")

        # Show what would be run
        for s in suites:
            console.print(f"Suite: [bold]{s.name}[/bold]")
            for tc in s.test_cases:
                console.print(f"  - {tc.name}")
        sys.exit(0)

    logger.debug(f"Agent: {cfg.agent.module}.{cfg.agent.function}")
    if cfg.agent.framework:
        logger.debug(f"Framework: {cfg.agent.framework}")

    # Run evaluations
    def on_result(result: EvaluationResult) -> None:
        """Print result as it completes."""
        if result.passed:
            icon = "[green]✓[/green]"
        elif result.status == GradeStatus.ERROR:
            icon = "[red]![/red]"
        else:
            icon = "[red]✗[/red]"

        duration = f"({result.duration_ms:.1f}ms)" if result.duration_ms else ""
        console.print(f"  {icon} {result.test_case_name} {duration}")

        if verbose:
            # Show all grades in verbose mode
            for grade in result.grades:
                if grade.passed:
                    grade_icon = "[green]✓[/green]"
                else:
                    grade_icon = "[red]✗[/red]"
                msg = grade.message or grade.status.value
                console.print(f"      [dim]{grade_icon} {grade.grader_name}: {msg}[/dim]")

                # Show extra details for LLM graders
                if grade.details and "raw_response" in grade.details:
                    response_preview = grade.details["raw_response"][:150].replace("\n", " ")
                    logger.debug(f"        LLM response: {response_preview}...")

    # Show concurrency info
    effective_workers = workers if workers is not None else cfg.execution.workers
    if effective_workers == 0:
        console.print("[dim]Running with unlimited concurrency[/dim]\n")
    elif effective_workers == 1:
        console.print("[dim]Running sequentially[/dim]\n")
    else:
        console.print(f"[dim]Running with max {effective_workers} concurrent tests[/dim]\n")

    try:
        run_result = runner.run(
            suites=suites,
            tags=list(tag) if tag else None,
            on_result=on_result,
            max_concurrent=workers,
        )
    except ValueError as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Evaluation error: {e}")
        if verbose:
            logger.exception("Full traceback:")
        sys.exit(1)

    # Print summary
    console.print()
    _print_summary(run_result)

    # Output to file if requested
    if output_file:
        _write_output(run_result, output, output_file)

    # Exit with appropriate code
    if cfg.thresholds.min_pass_rate > 0:
        if run_result.pass_rate < cfg.thresholds.min_pass_rate:
            console.print(
                f"\n[red]Pass rate {run_result.pass_rate:.1%} < "
                f"threshold {cfg.thresholds.min_pass_rate:.1%}[/red]"
            )
            sys.exit(1)

    sys.exit(0 if run_result.all_passed else 1)


def _print_summary(result: RunResult) -> None:
    """Print evaluation summary."""
    table = Table(box=box.SIMPLE)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Total", str(result.total))
    table.add_row("Passed", f"[green]{result.passed}[/green]")
    table.add_row("Failed", f"[red]{result.failed}[/red]" if result.failed else "0")
    table.add_row("Pass Rate", f"{result.pass_rate:.1%}")

    console.print(Panel(table, title="Results", border_style="blue"))


def _write_output(result: RunResult, format: str, path: str) -> None:
    """Write results to file."""
    if format == "json":
        import json

        with open(path, "w") as f:
            json.dump(result.model_dump(mode="json"), f, indent=2, default=str)
    elif format == "junit":
        _write_junit(result, path)

    console.print(f"[dim]Output written to: {path}[/dim]")


def _write_junit(result: RunResult, path: str) -> None:
    """Write results in JUnit XML format."""
    import xml.etree.ElementTree as ET

    testsuites = ET.Element("testsuites")
    testsuites.set("tests", str(result.total))
    testsuites.set("failures", str(result.failed))

    for suite_result in result.suites:
        testsuite = ET.SubElement(testsuites, "testsuite")
        testsuite.set("name", suite_result.suite_name)
        testsuite.set("tests", str(suite_result.total))
        testsuite.set("failures", str(suite_result.failed))
        testsuite.set("errors", str(suite_result.errors))

        for eval_result in suite_result.results:
            testcase = ET.SubElement(testsuite, "testcase")
            testcase.set("name", eval_result.test_case_name)
            testcase.set("time", str((eval_result.duration_ms or 0) / 1000))

            if eval_result.status == GradeStatus.FAIL:
                failure = ET.SubElement(testcase, "failure")
                messages = [g.message for g in eval_result.failed_grades if g.message]
                failure.set("message", "; ".join(messages) or "Test failed")

            elif eval_result.status == GradeStatus.ERROR:
                error = ET.SubElement(testcase, "error")
                error.set("message", eval_result.error or "Unknown error")

    tree = ET.ElementTree(testsuites)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="unicode", xml_declaration=True)


@main.command()
@click.argument("name")
@click.option("--input", "-i", "input_text", required=True, help="Test input")
@click.option("--output-contains", "-c", multiple=True, help="Expected output contains")
@click.option("--tools", "-t", multiple=True, help="Expected tool calls")
def create(
    name: str,
    input_text: str,
    output_contains: tuple[str, ...],
    tools: tuple[str, ...],
) -> None:
    """Create a new test case."""
    from evaldeck.test_case import EvalCase, ExpectedBehavior, Turn

    expected = ExpectedBehavior(
        output_contains=list(output_contains) if output_contains else None,
        tools_called=list(tools) if tools else None,
    )

    test_case = EvalCase(
        name=name,
        turns=[Turn(user=input_text, expected=expected)],
    )

    console.print(test_case.to_yaml())


@main.command()
def validate() -> None:
    """Validate configuration and test cases."""
    try:
        cfg = EvaldeckConfig.load()
        console.print("[green]✓[/green] Config file is valid")
    except FileNotFoundError:
        console.print("[red]✗[/red] No config file found")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Config error: {e}")
        sys.exit(1)

    # Validate test cases
    from evaldeck.evaluator import EvaluationRunner

    runner = EvaluationRunner(config=cfg)

    try:
        suites = runner._discover_suites()
        total_tests = sum(len(s.test_cases) for s in suites)
        console.print(f"[green]✓[/green] Found {total_tests} valid test case(s)")
    except Exception as e:
        console.print(f"[red]✗[/red] Test case error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
