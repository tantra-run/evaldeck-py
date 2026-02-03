# LLM-Based Graders

LLM-based graders use a language model to evaluate agent outputs. They're ideal for subjective criteria that can't be captured by simple rules.

## When to Use

Use LLM graders for:

- Evaluating helpfulness or quality
- Checking accuracy of information
- Assessing tone and professionalism
- Comparing against reference outputs
- Any subjective evaluation

## Setup

### API Keys

LLM graders require API keys:

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Installation

```bash
pip install evaldeck[openai]      # For OpenAI models
pip install evaldeck[anthropic]   # For Anthropic models
pip install evaldeck[all]         # Both
```

## LLMGrader

The basic LLM grader evaluates pass/fail based on a prompt.

### YAML Configuration

```yaml
graders:
  - type: llm
    prompt: |
      Evaluate if this response is helpful and accurate.

      User asked: {{ input }}
      Agent responded: {{ output }}

      Is the response helpful? Answer PASS or FAIL.
    model: gpt-4o-mini
```

### Template Variables

| Variable | Description |
|----------|-------------|
| `{{ input }}` | The test case input |
| `{{ output }}` | The agent's final output |
| `{{ trace }}` | Full trace as JSON |
| `{{ task }}` | Test case description |
| `{{ reference }}` | Reference output (if provided) |

### Full Example

```yaml
name: customer_support_quality
input: "I can't log into my account"

graders:
  - type: llm
    prompt: |
      You are evaluating a customer support AI agent.

      Customer message: {{ input }}
      Agent response: {{ output }}

      Evaluate the response on these criteria:
      1. Does it acknowledge the customer's issue?
      2. Does it provide actionable next steps?
      3. Is the tone empathetic and professional?

      If all criteria are met, respond with: VERDICT: PASS
      If any criteria fail, respond with: VERDICT: FAIL

      Explain your reasoning briefly.
    model: gpt-4o-mini
```

### Response Parsing

The grader looks for these patterns in the LLM response:

- `VERDICT: PASS` or `VERDICT: FAIL`
- `PASS` or `FAIL` (at start of line)
- `Result: PASS` or `Result: FAIL`

## Threshold-Based Scoring

For numeric scoring instead of pass/fail:

```yaml
graders:
  - type: llm
    prompt: |
      Score this response from 1-5 for helpfulness.

      Response: {{ output }}

      Provide your score as: SCORE: <number>
    model: gpt-4o-mini
    threshold: 4  # Must score 4 or higher to pass
```

The grader extracts the score and compares against the threshold.

## LLMRubricGrader

For detailed multi-criteria evaluation:

```yaml
graders:
  - type: llm_rubric
    prompt: |
      Evaluate this customer service response.
      Response: {{ output }}
    rubric:
      accuracy:
        description: "Information provided is correct"
        weight: 0.4
      helpfulness:
        description: "Response helps solve the problem"
        weight: 0.3
      tone:
        description: "Professional and empathetic tone"
        weight: 0.3
    model: gpt-4o-mini
    threshold: 3.5  # Weighted average must be ≥ 3.5
```

## Model Selection

### Available Models

**OpenAI:**

- `gpt-4o` - Most capable, higher cost
- `gpt-4o-mini` - Good balance (recommended)
- `gpt-4-turbo` - Previous generation

**Anthropic:**

- `claude-3-opus` - Most capable
- `claude-3-sonnet` - Good balance
- `claude-3-haiku` - Fast and cheap

### Configuration

Set default model in `evaldeck.yaml`:

```yaml
graders:
  llm:
    model: gpt-4o-mini
    provider: openai
```

Override per grader:

```yaml
graders:
  - type: llm
    model: gpt-4o  # Use more capable model for this test
    prompt: "..."
```

## Python Usage

```python
from evaldeck.graders import LLMGrader

grader = LLMGrader(
    prompt="""
    Is this response helpful?
    Response: {{ output }}
    Answer PASS or FAIL.
    """,
    model="gpt-4o-mini",
    provider="openai",  # or "anthropic"
    threshold=None,     # None for pass/fail, float for scoring
    timeout=60,         # Timeout in seconds
)

result = grader.grade(trace, test_case)
print(result.status)   # PASS or FAIL
print(result.message)  # LLM's explanation
```

## Prompt Engineering Tips

### 1. Be Specific About Criteria

```yaml
# Vague (bad)
prompt: "Is this good?"

# Specific (good)
prompt: |
  Evaluate the response on:
  1. Accuracy of information
  2. Completeness of answer
  3. Clarity of explanation
```

### 2. Provide Context

```yaml
prompt: |
  You are evaluating an AI travel agent.
  The agent helps users book flights and hotels.

  User request: {{ input }}
  Agent response: {{ output }}

  Did the agent appropriately handle this travel request?
```

### 3. Specify Output Format

```yaml
prompt: |
  Evaluate and respond in this exact format:
  VERDICT: PASS or FAIL
  REASON: <brief explanation>
```

### 4. Include Reference When Available

```yaml
name: accuracy_check
input: "What is the capital of France?"
reference_output: "The capital of France is Paris."

graders:
  - type: llm
    prompt: |
      Compare the agent's response to the reference.

      Reference: {{ reference }}
      Agent response: {{ output }}

      Is the agent's response accurate? PASS or FAIL.
```

## Cost Management

LLM graders cost money. Optimize by:

### 1. Use Cheaper Models for Simple Checks

```yaml
graders:
  - type: llm
    model: gpt-4o-mini  # Cheaper, often sufficient
    prompt: "..."
```

### 2. Layer with Code-Based Graders

Run fast checks first, LLM only if needed:

```yaml
expected:
  # Free, fast checks
  tools_called: [required_tool]
  output_not_contains: [error]

graders:
  # Only runs if above pass
  - type: llm
    prompt: "..."
```

### 3. Batch Similar Tests

Group tests that need the same type of evaluation.

## Determinism

LLM graders are non-deterministic. The same input may produce different results.

### Strategies for Consistency

1. **Use low temperature** (when available)
2. **Clear, specific prompts** reduce ambiguity
3. **Multiple runs** for critical tests
4. **Thresholds** instead of binary pass/fail

```yaml
graders:
  - type: llm
    prompt: "Score 1-10..."
    threshold: 7  # More robust than exact pass/fail
```

## Error Handling

When LLM calls fail:

```yaml
graders:
  - type: llm
    prompt: "..."
    timeout: 60     # Timeout in seconds
```

Failed calls return `GradeStatus.ERROR` with details in the message.

## Best Practices

1. **Combine with code-based graders** - Use LLM for what rules can't check
2. **Start with gpt-4o-mini** - Upgrade only if needed
3. **Test your prompts** - Run manually before automating
4. **Monitor costs** - Track API usage
5. **Cache when possible** - Same input = same grade (coming soon)
