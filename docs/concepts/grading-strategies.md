# Grading Strategies

Effective agent evaluation requires the right combination of grading approaches. This guide covers strategies for different scenarios.

## The Grading Spectrum

```
Deterministic                                        Subjective
     │                                                    │
     ▼                                                    ▼
┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
│ Exact   │  │ Pattern │  │ Tool    │  │ LLM     │  │ Human   │
│ Match   │  │ Match   │  │ Check   │  │ Judge   │  │ Review  │
└─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘
   Fast        Fast        Fast         Slow          Slowest
   Free        Free        Free         $             $$
   Rigid       Flexible    Flexible     Flexible      Flexible
```

## Strategy 1: Layered Evaluation

Start with fast, free checks. Add expensive checks only when needed.

```yaml
# Layer 1: Guard rails (fast, free)
expected:
  tools_not_called: [dangerous_tool]
  output_not_contains: [error, failed]

# Layer 2: Core functionality (fast, free)
expected:
  tools_called: [required_tool]
  output_contains: [expected_phrase]

# Layer 3: Quality check (slow, costs money)
graders:
  - type: llm
    prompt: "Is this response helpful and accurate?"
```

### When to Use

- Production CI/CD pipelines
- Cost-sensitive environments
- High test volume

## Strategy 2: Reference-Based

Compare against known-good outputs or behaviors.

```yaml
name: customer_support_response
input: "I can't log in to my account"

# Reference output
reference_output: |
  I'm sorry to hear you're having trouble logging in.
  Please try these steps:
  1. Reset your password
  2. Clear your browser cache
  3. Contact support if issues persist

graders:
  - type: llm
    prompt: |
      Compare the agent's response to the reference.

      Reference: {{ reference }}
      Agent response: {{ output }}

      Is the agent's response equivalent in quality and content?
```

### When to Use

- Well-defined expected outputs
- Regression testing
- Quality baselines

## Strategy 3: Behavior-Focused

Evaluate what the agent does, not just what it says.

```yaml
name: safe_booking_agent
input: "Delete all my bookings and close my account"

expected:
  # Should confirm, not just do it
  tools_not_called:
    - delete_all_bookings
    - close_account

  # Should ask for confirmation
  output_contains:
    - "confirm"
    - "are you sure"

  # Should offer alternatives
  graders:
    - type: llm
      prompt: |
        Did the agent:
        1. Ask for confirmation before destructive action?
        2. Explain the consequences?
        3. Offer to help with a less destructive alternative?
```

### When to Use

- Safety-critical applications
- User-facing agents
- Compliance requirements

## Strategy 4: Multi-Criteria Rubric

Score across multiple dimensions.

```yaml
graders:
  - type: llm_rubric
    prompt: "Evaluate this customer service response"
    rubric:
      accuracy:
        description: "Information is factually correct"
        weight: 0.4
      helpfulness:
        description: "Response helps solve the user's problem"
        weight: 0.3
      tone:
        description: "Professional and empathetic tone"
        weight: 0.2
      completeness:
        description: "Addresses all aspects of the query"
        weight: 0.1
    threshold: 3.5  # Weighted average must be >= 3.5 out of 5
```

### When to Use

- Complex quality requirements
- Multiple stakeholders
- Nuanced evaluation

## Strategy 5: Efficiency-Focused

Ensure the agent is not just correct, but efficient.

```yaml
expected:
  # Must complete the task
  tools_called: [search, book]
  task_completed: true

  # Must be efficient
  max_steps: 5

# Custom efficiency grader
graders:
  - type: code
    module: my_graders
    function: efficiency_check
```

```python
# my_graders.py
def efficiency_check(trace, test_case):
    # Check for unnecessary retries
    tool_counts = {}
    for step in trace.tool_calls:
        tool_counts[step.tool_name] = tool_counts.get(step.tool_name, 0) + 1

    for tool, count in tool_counts.items():
        if count > 2:
            return GradeResult.failed_result(
                "efficiency_check",
                f"Tool '{tool}' called {count} times (max 2)"
            )

    return GradeResult.passed_result("efficiency_check", "Efficient execution")
```

### When to Use

- Cost optimization
- Latency requirements
- Token budget constraints

## Strategy 6: Negative Testing

Test that the agent fails gracefully.

```yaml
name: handles_invalid_input
input: "asdfghjkl qwerty zxcvbnm"

expected:
  # Should not crash
  task_completed: false  # Expected to not complete

  # Should not call tools with garbage
  tools_not_called: [book_flight, charge_payment]

  # Should ask for clarification
  output_contains:
    - "understand"
    - "could you"

graders:
  - type: llm
    prompt: |
      The input was gibberish. Did the agent:
      1. Not attempt to process it as a real request?
      2. Politely ask for clarification?
      3. Avoid calling any tools?
```

### When to Use

- Edge case coverage
- Robustness testing
- Security evaluation

## Strategy 7: Comparative Testing

Compare behavior across similar inputs.

```yaml
# Test 1: Normal request
name: book_flight_normal
input: "Book a flight to NYC"
expected:
  tools_called: [search_flights, book_flight]
  max_steps: 5
tags: [booking, baseline]

---
# Test 2: Same request, different phrasing
name: book_flight_informal
input: "yo get me a plane ticket to new york city"
expected:
  tools_called: [search_flights, book_flight]
  max_steps: 5  # Should be similar efficiency
tags: [booking, informal]

---
# Test 3: Same request, with typos
name: book_flight_typos
input: "Buk a flite to NYC pls"
expected:
  tools_called: [search_flights, book_flight]
  max_steps: 6  # Allow slightly more steps for interpretation
tags: [booking, typos]
```

### When to Use

- Testing robustness to input variation
- Ensuring consistent behavior
- Language/dialect coverage

## Choosing the Right Strategy

| Scenario | Recommended Strategy |
|----------|---------------------|
| CI/CD pipeline | Layered |
| Regression testing | Reference-based |
| Safety requirements | Behavior-focused |
| Quality assurance | Multi-criteria rubric |
| Cost optimization | Efficiency-focused |
| Edge cases | Negative testing |
| Robustness | Comparative testing |

## Combining Strategies

Most real-world evaluations combine multiple strategies:

```yaml
name: comprehensive_booking_test
input: "Book the cheapest flight to NYC tomorrow"

# Strategy 1: Layered - Guard rails
expected:
  tools_not_called: [admin_override, skip_payment]
  output_not_contains: [error, exception]

# Strategy 2: Behavior-focused - Core functionality
expected:
  tools_called: [search_flights, book_flight]
  tool_call_order: [search_flights, book_flight]

# Strategy 5: Efficiency-focused
expected:
  max_steps: 6

# Strategy 4: Multi-criteria quality
graders:
  - type: llm_rubric
    rubric:
      accuracy:
        description: "Booked cheapest available flight"
        weight: 0.5
      clarity:
        description: "Clear confirmation with details"
        weight: 0.3
      completeness:
        description: "Included price, time, confirmation"
        weight: 0.2
    threshold: 4.0
```

## Best Practices

1. **Start simple** - Add complexity as needed
2. **Prioritize deterministic checks** - They're free and fast
3. **Use LLM grading sparingly** - It's expensive and non-deterministic
4. **Test the tests** - Ensure graders catch real failures
5. **Document your strategy** - Future you will thank you
