# LLM-as-Judge

Use language models to evaluate subjective criteria like helpfulness, tone, and accuracy.

## Basic LLM Grading

```yaml
# tests/evals/helpful_response.yaml
name: response_is_helpful
input: "How do I reset my password?"

graders:
  - type: llm
    prompt: |
      Evaluate if this customer support response is helpful.

      User asked: {{ input }}
      Agent responded: {{ output }}

      A helpful response should:
      1. Acknowledge the user's issue
      2. Provide clear steps to resolve it
      3. Offer additional assistance

      Answer: VERDICT: PASS or FAIL
      Reason: Your explanation
    model: gpt-4o-mini
```

## With Scoring

Use numeric scores instead of pass/fail:

```yaml
name: quality_score
input: "Explain quantum computing"

graders:
  - type: llm
    prompt: |
      Rate this explanation from 1-5.

      Question: {{ input }}
      Response: {{ output }}

      Scoring:
      1 = Incorrect or confusing
      2 = Partially correct but unclear
      3 = Correct but basic
      4 = Clear and informative
      5 = Excellent, comprehensive

      SCORE: <number>
      REASON: <explanation>
    model: gpt-4o-mini
    threshold: 4  # Must score 4+ to pass
```

## Multi-Criteria Rubric

Evaluate across multiple dimensions:

```yaml
name: comprehensive_evaluation
input: "I'm having trouble with my order"

graders:
  - type: llm_rubric
    rubric:
      accuracy:
        description: "Information provided is factually correct"
      helpfulness:
        description: "Response helps solve the user's problem"
      empathy:
        description: "Response shows understanding of user's frustration"
      completeness:
        description: "Response addresses all aspects of the query"
    model: gpt-4o-mini
    threshold: 3.5  # Average score must be >= 3.5
```

## Python Usage

```python
from evaldeck import Trace, EvalCase, Evaluator
from evaldeck.graders import LLMGrader, LLMRubricGrader

# Create trace
trace = Trace(input="How do I cancel my subscription?")
trace.complete(output="To cancel, go to Settings > Subscription > Cancel. "
                      "You'll retain access until the end of your billing period.")

# Simple LLM grader
grader = LLMGrader(
    prompt="""
    Is this response helpful and accurate?
    Question: {input}
    Response: {output}
    Answer PASS or FAIL with explanation.
    """,
    model="gpt-4o-mini"
)

# Rubric grader
rubric_grader = LLMRubricGrader(
    rubric={
        "clarity": "Response is easy to understand",
        "accuracy": "Instructions are correct",
        "completeness": "All necessary steps are included",
    },
    model="gpt-4o-mini",
    pass_threshold=0.7
)

# Evaluate
evaluator = Evaluator(graders=[grader, rubric_grader])
test = EvalCase(name="cancel_subscription", input=trace.input)
result = evaluator.evaluate(trace, test)

for grade in result.grades:
    print(f"{grade.grader_name}: {grade.status}")
    if grade.score:
        print(f"  Score: {grade.score}")
    print(f"  Reason: {grade.message}")
```

## Custom Prompts

### Compare to Reference

```yaml
graders:
  - type: llm
    prompt: |
      Compare the agent's response to the reference answer.

      Question: {{ input }}
      Reference Answer: {{ reference }}
      Agent Response: {{ output }}

      Is the agent's response as good or better than the reference?
      Consider accuracy, completeness, and clarity.

      VERDICT: PASS or FAIL
      REASON: explanation

reference_output: |
  To reset your password:
  1. Click "Forgot Password" on the login page
  2. Enter your email address
  3. Check your inbox for the reset link
  4. Create a new password
```

### Evaluate Tool Usage

```yaml
graders:
  - type: llm
    prompt: |
      Evaluate if the agent used tools appropriately.

      User Request: {{ input }}
      Tools Called: {{ trace }}
      Final Output: {{ output }}

      Consider:
      1. Were the right tools selected for the task?
      2. Were tools called in a logical order?
      3. Did the agent avoid unnecessary tool calls?

      VERDICT: PASS or FAIL
```

### Domain-Specific Evaluation

```yaml
graders:
  - type: llm
    prompt: |
      You are a medical information accuracy checker.

      User Question: {{ input }}
      Agent Response: {{ output }}

      Evaluate ONLY for factual medical accuracy.
      DO NOT pass responses that could be harmful if followed.

      VERDICT: PASS or FAIL
      SAFETY_CONCERN: Yes/No
      REASON: explanation
    model: gpt-4o  # Use more capable model for medical content
```

## Cost Optimization

LLM grading costs money. Optimize by:

### 1. Layer with Code Graders

Run free checks first:

```yaml
expected:
  # Fast, free checks
  output_not_contains: ["error", "I don't know"]
  tools_called: [search_knowledge_base]

graders:
  # Only run if above pass
  - type: llm
    prompt: "Is this accurate?"
```

### 2. Use Cheaper Models

```yaml
graders:
  - type: llm
    model: gpt-4o-mini  # $0.15/1M tokens vs $5/1M for gpt-4o
    prompt: "..."
```

### 3. Keep Prompts Concise

```yaml
# Verbose (more tokens)
prompt: |
  You are an expert evaluator. Your task is to carefully
  analyze the following response and determine whether...
  [100 more words]

# Concise (fewer tokens)
prompt: |
  Is this response helpful? Answer PASS or FAIL.
  Response: {{ output }}
```

## Complete Example

```python
#!/usr/bin/env python3
"""LLM grading example."""

import os
from evaldeck import Trace, Step, EvalCase, ExpectedBehavior, Evaluator
from evaldeck.graders import LLMGrader

# Ensure API key is set
if not os.environ.get("OPENAI_API_KEY"):
    print("Set OPENAI_API_KEY environment variable")
    exit(1)


def customer_support_agent(input: str) -> Trace:
    """Simulated customer support agent."""
    trace = Trace(input=input)

    trace.add_step(Step.tool_call(
        tool_name="search_knowledge_base",
        tool_args={"query": input},
        tool_result={"articles": [{"title": "Password Reset Guide", "id": 123}]}
    ))

    trace.complete(
        output="I'd be happy to help you reset your password! "
               "Please click 'Forgot Password' on the login page, "
               "enter your email, and follow the link we send you. "
               "Let me know if you need any other assistance!"
    )
    return trace


def main():
    # Create test with LLM grading
    test = EvalCase(
        name="password_reset_help",
        input="I forgot my password, help!",
        expected=ExpectedBehavior(
            tools_called=["search_knowledge_base"]
        )
    )

    # Create evaluator with LLM grader
    llm_grader = LLMGrader(
        prompt="""
        Evaluate this customer support response:

        Customer: {input}
        Agent: {output}

        Rate on:
        1. Empathy - Does it acknowledge the customer's frustration?
        2. Clarity - Are the instructions clear?
        3. Helpfulness - Does it solve the problem?

        VERDICT: PASS if all criteria are met, FAIL otherwise
        REASON: Brief explanation
        """,
        model="gpt-4o-mini"
    )
    evaluator = Evaluator(graders=[llm_grader])

    # Run evaluation
    trace = customer_support_agent(test.input)
    result = evaluator.evaluate(trace, test)

    # Report
    print(f"Test: {result.test_case_name}")
    print(f"Overall: {'PASS' if result.passed else 'FAIL'}")
    print()

    for grade in result.grades:
        print(f"{grade.grader_name}:")
        print(f"  Status: {grade.status}")
        print(f"  Reason: {grade.message}")
        print()


if __name__ == "__main__":
    main()
```
