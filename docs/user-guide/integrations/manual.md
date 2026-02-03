# Manual Trace Construction

For custom agents or unsupported frameworks, build traces manually.

## Basic Trace Structure

```python
from evaldeck import Trace, Step

# Create trace
trace = Trace(input="User's request")

# Add steps
trace.add_step(Step.tool_call(tool_name="search", tool_args={"query": "..."}, tool_result=result))
trace.add_step(Step.llm_call("gpt-4o-mini", prompt, response))

# Complete trace
trace.complete(output="Final response")
```

## Creating a Trace

```python
from evaldeck import Trace, TraceStatus

trace = Trace(
    input="Book a flight from NYC to LA",     # Required: user input
    # Optional fields:
    # output="...",                            # Set later with complete()
    # status=TraceStatus.SUCCESS,              # Set later with complete()
    # steps=[],                                # Add with add_step()
    framework="custom",                        # Your framework name
    agent_name="BookingAgent",                 # Agent identifier
    metadata={"user_id": "123"}               # Custom metadata
)
```

## Adding Steps

### Tool Call

```python
from evaldeck import Step

step = Step.tool_call(
    tool_name="search_flights",
    tool_args={"from": "NYC", "to": "LA", "date": "2024-03-15"},
    tool_result={"flights": [{"id": "AA123", "price": 299}]},
    # Optional:
    duration_ms=150,
    status="success",  # or "error"
    error=None,        # Error message if status="error"
    metadata={"api_version": "v2"}
)

trace.add_step(step)
```

### LLM Call

```python
step = Step.llm_call(
    model="gpt-4o-mini",
    input="User wants to book a flight from NYC to LA on March 15th",
    output="I'll search for available flights.",
    # Optional:
    token_usage=TokenUsage(prompt_tokens=100, completion_tokens=20, total_tokens=120),
    duration_ms=500,
    metadata={"temperature": 0.7}
)

trace.add_step(step)
```

### Reasoning Step

```python
step = Step.reasoning(
    text="User wants a one-way flight. I should search for flights first, then book.",
    # Optional:
    duration_ms=10
)

trace.add_step(step)
```

## Completing the Trace

```python
# Success
trace.complete(
    output="Your flight has been booked. Confirmation: ABC123",
    status="success"  # Optional, defaults to "success"
)

# Failure
trace.complete(
    output="Sorry, I couldn't complete the booking.",
    status="failure"
)

# Error
trace.complete(
    output="An error occurred: Connection timeout",
    status="error"
)

# Timeout
trace.complete(
    output="Operation timed out",
    status="timeout"
)
```

## Complete Example

```python
from evaldeck import Trace, Step, TokenUsage, Evaluator, EvalCase, ExpectedBehavior
import time

def run_booking_agent(user_input: str) -> Trace:
    """Custom booking agent with manual tracing."""

    trace = Trace(
        input=user_input,
        framework="custom",
        agent_name="BookingAgent"
    )

    # Step 1: Parse user request (LLM call)
    start = time.time()
    parsed = {"from": "NYC", "to": "LA", "date": "2024-03-15"}  # Simulated
    trace.add_step(Step.llm_call(
        model="gpt-4o-mini",
        input=f"Parse this request: {user_input}",
        output=str(parsed),
        token_usage=TokenUsage(prompt_tokens=50, completion_tokens=30, total_tokens=80),
        duration_ms=int((time.time() - start) * 1000)
    ))

    # Step 2: Search flights (tool call)
    start = time.time()
    search_result = [
        {"id": "AA123", "price": 299, "departure": "08:00"},
        {"id": "UA456", "price": 349, "departure": "10:30"},
    ]
    trace.add_step(Step.tool_call(
        tool_name="search_flights",
        tool_args=parsed,
        tool_result=search_result,
        duration_ms=int((time.time() - start) * 1000)
    ))

    # Step 3: Select best flight (reasoning)
    trace.add_step(Step.reasoning(
        text="AA123 is cheapest at $299. Will book this flight."
    ))

    # Step 4: Book flight (tool call)
    start = time.time()
    booking_result = {"confirmation": "ABC123", "flight": "AA123"}
    trace.add_step(Step.tool_call(
        tool_name="book_flight",
        tool_args={"flight_id": "AA123"},
        tool_result=booking_result,
        duration_ms=int((time.time() - start) * 1000)
    ))

    # Step 5: Generate response (LLM call)
    start = time.time()
    response = f"Your flight AA123 from NYC to LA on March 15 is booked. Confirmation: ABC123"
    trace.add_step(Step.llm_call(
        model="gpt-4o-mini",
        input=f"Generate confirmation message for: {booking_result}",
        output=response,
        token_usage=TokenUsage(prompt_tokens=40, completion_tokens=25, total_tokens=65),
        duration_ms=int((time.time() - start) * 1000)
    ))

    # Complete trace
    trace.complete(output=response)

    return trace


# Run and evaluate
trace = run_booking_agent("Book a flight from NYC to LA on March 15")

test_case = EvalCase(
    name="book_flight",
    input="Book a flight from NYC to LA on March 15",
    expected=ExpectedBehavior(
        tools_called=["search_flights", "book_flight"],
        output_contains=["confirmation", "ABC123"],
        max_steps=6
    )
)

evaluator = Evaluator()
result = evaluator.evaluate(trace, test_case)

print(f"Evaluation: {'PASS' if result.passed else 'FAIL'}")
print(f"Steps: {len(trace.steps)}")
print(f"Tools called: {trace.tools_called}")
print(f"Total tokens: {trace.total_tokens}")
```

## Wrapping Existing Code

### Function Decorator

```python
from evaldeck import Trace, Step
from functools import wraps
import time

# Thread-local trace storage
import threading
_trace_context = threading.local()

def get_current_trace() -> Trace:
    return getattr(_trace_context, 'trace', None)

def set_current_trace(trace: Trace):
    _trace_context.trace = trace

def traced_tool(func):
    """Decorator to capture function calls as tool steps."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        trace = get_current_trace()
        start = time.time()

        try:
            result = func(*args, **kwargs)

            if trace:
                trace.add_step(Step.tool_call(
                    tool_name=func.__name__,
                    tool_args={"args": args, "kwargs": kwargs},
                    tool_result=result,
                    duration_ms=int((time.time() - start) * 1000)
                ))

            return result

        except Exception as e:
            if trace:
                trace.add_step(Step.tool_call(
                    tool_name=func.__name__,
                    tool_args={"args": args, "kwargs": kwargs},
                    tool_result=None,
                    status="error",
                    error=str(e),
                    duration_ms=int((time.time() - start) * 1000)
                ))
            raise

    return wrapper


# Usage
@traced_tool
def search_flights(from_city: str, to_city: str):
    # Your implementation
    return {"flights": [...]}

@traced_tool
def book_flight(flight_id: str):
    # Your implementation
    return {"confirmation": "ABC123"}


def run_agent(input: str) -> Trace:
    trace = Trace(input=input)
    set_current_trace(trace)

    try:
        # Your agent logic using decorated functions
        flights = search_flights("NYC", "LA")
        booking = book_flight("AA123")
        output = f"Booked! Confirmation: {booking['confirmation']}"
        trace.complete(output=output)
    except Exception as e:
        trace.complete(output=str(e), status="error")

    return trace
```

## For evaldeck.yaml

Expose a function that returns a Trace:

```yaml
# evaldeck.yaml
agent:
  module: my_agent
  function: run_agent
```

```python
# my_agent.py
from evaldeck import Trace

def run_agent(input: str) -> Trace:
    """Entry point for Evaldeck CLI."""
    trace = Trace(input=input)

    # Your agent logic here...
    # Add steps as execution proceeds...

    trace.complete(output="...")
    return trace
```

## Best Practices

1. **Capture all steps** - Don't skip reasoning or intermediate calls
2. **Include timing** - `duration_ms` helps identify bottlenecks
3. **Track tokens** - `token_usage` for cost analysis
4. **Handle errors** - Set appropriate status and error messages
5. **Add metadata** - Include useful debugging information
