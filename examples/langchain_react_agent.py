"""Example: Evaluating a LangChain Agent with Evaldeck.

This example demonstrates:
1. Creating a LangChain agent with custom tools
2. Capturing execution traces with OpenTelemetry/OpenInference
3. Evaluating agent behavior with multiple graders
4. Using LLM-as-judge for semantic evaluation

Requirements:
    pip install evaldeck langchain-openai langgraph
    pip install opentelemetry-sdk openinference-instrumentation-langchain

Set your API key:
    export OPENAI_API_KEY=sk-...
"""

import os

from evaldeck import EvalCase, Evaluator, ExpectedBehavior
from evaldeck.graders import LLMGrader
from evaldeck.integrations import setup_otel_tracing

# Check for required packages
try:
    import warnings

    from langchain_core.messages import HumanMessage
    from langchain_core.tools import tool
    from langchain_openai import ChatOpenAI
    from openinference.instrumentation.langchain import LangChainInstrumentor

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from langgraph.prebuilt import create_react_agent
except ImportError as e:
    print(f"Import error: {e}")
    print("\nRequired packages not installed. Run:")
    print("  pip install evaldeck langchain-openai langgraph")
    print("  pip install opentelemetry-sdk openinference-instrumentation-langchain")
    exit(1)


# =============================================================================
# Setup OpenTelemetry Tracing
# =============================================================================

processor = setup_otel_tracing()
LangChainInstrumentor().instrument()


# =============================================================================
# 1. Define Tools for the Agent
# =============================================================================


@tool
def search_flights(origin: str, destination: str, date: str) -> str:
    """Search for available flights between two cities on a given date."""
    # Simulated flight search results
    flights = [
        {"id": "AA123", "departure": "08:00", "arrival": "11:30", "price": 299},
        {"id": "UA456", "departure": "14:00", "arrival": "17:30", "price": 349},
        {"id": "DL789", "departure": "19:00", "arrival": "22:30", "price": 279},
    ]
    return f"Found {len(flights)} flights from {origin} to {destination} on {date}:\n" + "\n".join(
        f"- {f['id']}: {f['departure']}-{f['arrival']}, ${f['price']}" for f in flights
    )


@tool
def book_flight(flight_id: str, passenger_name: str) -> str:
    """Book a specific flight for a passenger."""
    confirmation = f"CONF-{flight_id}-{hash(passenger_name) % 10000:04d}"
    return (
        f"Successfully booked flight {flight_id} for {passenger_name}. Confirmation: {confirmation}"
    )


@tool
def get_weather(city: str) -> str:
    """Get current weather for a city."""
    # Simulated weather data
    weather_data = {
        "new york": "Partly cloudy, 72°F",
        "los angeles": "Sunny, 85°F",
        "chicago": "Rainy, 65°F",
        "default": "Clear skies, 75°F",
    }
    return weather_data.get(city.lower(), weather_data["default"])


@tool
def cancel_flight(confirmation_code: str) -> str:
    """Cancel a flight booking."""
    return f"Flight with confirmation {confirmation_code} has been cancelled. Refund will be processed in 5-7 business days."


# =============================================================================
# 2. Create the Agent
# =============================================================================


def create_travel_agent():
    """Create a travel booking agent using LangGraph."""
    import warnings

    # Initialize the LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # Define tools
    tools = [search_flights, book_flight, get_weather, cancel_flight]

    # Create agent using LangGraph's prebuilt ReAct agent
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        warnings.filterwarnings("ignore", message=".*create_react_agent.*")
        agent = create_react_agent(llm, tools)

    return agent


def run_agent(agent, user_input: str) -> str:
    """Run the agent and return the final response."""
    # Clear previous traces
    processor.reset()

    # Invoke agent - OpenTelemetry captures traces automatically
    result = agent.invoke({"messages": [HumanMessage(content=user_input)]})

    # Extract final response
    messages = result.get("messages", [])
    output = messages[-1].content if messages else ""

    return output


# =============================================================================
# 3. Define Test Cases
# =============================================================================

TEST_CASES = [
    EvalCase(
        name="book_flight_happy_path",
        description="User books a flight successfully",
        input="Book me a flight from New York to Los Angeles for December 15th. My name is John Smith.",
        expected=ExpectedBehavior(
            tools_called=["search_flights", "book_flight"],
            tools_not_called=["cancel_flight"],
            output_contains=["confirmation"],
            max_steps=15,
            task_completed=True,
        ),
    ),
    EvalCase(
        name="search_only",
        description="User only wants to see flight options",
        input="What flights are available from Chicago to Miami on January 10th?",
        expected=ExpectedBehavior(
            tools_called=["search_flights"],
            tools_not_called=["book_flight", "cancel_flight"],
            output_contains=["flight"],
            max_steps=10,
        ),
    ),
    EvalCase(
        name="weather_check",
        description="User asks about weather at destination",
        input="What's the weather like in Los Angeles right now?",
        expected=ExpectedBehavior(
            tools_called=["get_weather"],
            tools_not_called=["search_flights", "book_flight"],
            task_completed=True,
        ),
    ),
]


# =============================================================================
# 4. Run Evaluation
# =============================================================================


def run_evaluation() -> None:
    """Run the full evaluation."""

    # Check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        return

    # Create agent
    agent = create_travel_agent()

    # Create evaluator with default graders
    evaluator = Evaluator()

    print("=" * 70)
    print("Evaldeck + LangChain Integration Example (OpenTelemetry)")
    print("=" * 70)

    results = []

    for test_case in TEST_CASES:
        print(f"\n{'=' * 70}")
        print(f"Test: {test_case.name}")
        print(f"Input: {test_case.input}")
        print("=" * 70)

        try:
            # Run agent - traces captured automatically via OpenTelemetry
            output = run_agent(agent, test_case.input)

            # Get captured trace
            trace = processor.get_latest_trace()

            print("\n--- Trace Summary ---")
            print(f"Steps: {trace.step_count}")
            print(f"Tools called: {trace.tools_called}")
            output_preview = (trace.output or output)[:100]
            print(
                f"Output: {output_preview}..."
                if len(output_preview) >= 100
                else f"Output: {output_preview}"
            )

            # Evaluate
            eval_result = evaluator.evaluate(trace, test_case)
            results.append(eval_result)

            print("\n--- Evaluation Results ---")
            print(f"Status: {'PASS' if eval_result.passed else 'FAIL'}")

            for grade in eval_result.grades:
                icon = "✓" if grade.passed else "✗"
                print(f"  {icon} {grade.grader_name}: {grade.message}")

            if eval_result.metrics:
                print("\n--- Metrics ---")
                for metric in eval_result.metrics:
                    print(f"  {metric.metric_name}: {metric.value} {metric.unit or ''}")

        except Exception as e:
            print(f"Error: {e}")
            import traceback

            traceback.print_exc()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print(
        f"Passed: {passed}/{total} ({100 * passed / total:.0f}%)" if total > 0 else "No tests run"
    )

    for result in results:
        icon = "✓" if result.passed else "✗"
        print(f"  {icon} {result.test_case_name}")


def run_with_llm_grader() -> None:
    """Demonstrate using an LLM grader for semantic evaluation."""

    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        return

    agent = create_travel_agent()

    # Run a test
    test_input = "I need to book the cheapest flight from NYC to LA for next week"

    print("\n" + "=" * 70)
    print("LLM Grader Example")
    print("=" * 70)
    print(f"Input: {test_input}\n")

    output = run_agent(agent, test_input)
    trace = processor.get_latest_trace()

    # Create test case with LLM grader
    test_case = EvalCase(
        name="cheapest_flight_selection",
        input=test_input,
        expected=ExpectedBehavior(
            tools_called=["search_flights", "book_flight"],
        ),
    )

    # Create LLM grader for semantic evaluation
    llm_grader = LLMGrader(
        model="gpt-4o-mini",
        task="Evaluate if the agent correctly identified and booked the CHEAPEST flight option from the search results.",
        prompt="""You are evaluating an AI travel agent.

User Request: {input}
Agent Response: {output}

Execution Trace:
{trace}

Task: {task}

Did the agent:
1. Search for flights
2. Identify the cheapest option
3. Book that specific flight

Respond with:
VERDICT: PASS or FAIL
REASON: Brief explanation
""",
    )

    # Evaluate with both standard and LLM graders
    evaluator = Evaluator()
    eval_result = evaluator.evaluate(trace, test_case)

    # Also run LLM grader
    llm_grade = llm_grader.grade(trace, test_case)

    print("--- Standard Graders ---")
    for grade in eval_result.grades:
        icon = "✓" if grade.passed else "✗"
        print(f"  {icon} {grade.grader_name}: {grade.message}")

    print("\n--- LLM Grader (Semantic) ---")
    icon = "✓" if llm_grade.passed else "✗"
    print(f"  {icon} {llm_grader.name}: {llm_grade.message}")
    if llm_grade.details:
        print(f"     Model: {llm_grade.details.get('model')}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--llm-grader":
        run_with_llm_grader()
    else:
        run_evaluation()
        print("\n\nTip: Run with --llm-grader to see LLM-based semantic evaluation")
