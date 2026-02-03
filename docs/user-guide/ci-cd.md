# CI/CD Integration

Integrate Evaldeck into your continuous integration pipeline to catch agent regressions before deployment.

## Overview

Evaldeck supports CI/CD with:

- **Exit codes** - Non-zero on failure
- **JUnit XML output** - Standard test reporting format
- **JSON output** - For custom processing
- **Threshold configuration** - Define pass criteria

## GitHub Actions

### Basic Setup

```yaml
# .github/workflows/evaldeck.yaml
name: Agent Evaluation

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  evaluate:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e ".[all]"

      - name: Run evaluations
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          evaldeck run --output junit --output-file results.xml

      - name: Publish Test Results
        uses: mikepenz/action-junit-report@v4
        if: always()
        with:
          report_paths: results.xml
```

### With Test Artifacts

```yaml
jobs:
  evaluate:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -e ".[all]"

      - name: Run evaluations
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          evaldeck run \
            --output junit --output-file results.xml \
            --output json --output-file results.json \
            --verbose

      - name: Upload results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: evaluation-results
          path: |
            results.xml
            results.json

      - name: Publish Test Results
        uses: mikepenz/action-junit-report@v4
        if: always()
        with:
          report_paths: results.xml
```

### Separate Test Stages

```yaml
jobs:
  # Fast smoke tests
  smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e ".[all]"
      - name: Run smoke tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: evaldeck run --tag smoke

  # Full regression (only on main)
  regression:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    needs: smoke
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e ".[all]"
      - name: Run full regression
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: evaldeck run --tag regression
```

## GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - evaluate

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip/

evaluate:
  stage: evaluate
  image: python:3.11
  script:
    - pip install -e ".[all]"
    - evaldeck run --output junit --output-file results.xml
  artifacts:
    when: always
    reports:
      junit: results.xml
    paths:
      - results.xml
    expire_in: 1 week
```

## CircleCI

```yaml
# .circleci/config.yml
version: 2.1

jobs:
  evaluate:
    docker:
      - image: cimg/python:3.11
    steps:
      - checkout
      - run:
          name: Install dependencies
          command: pip install -e ".[all]"
      - run:
          name: Run evaluations
          command: evaldeck run --output junit --output-file results.xml
      - store_test_results:
          path: results.xml
      - store_artifacts:
          path: results.xml

workflows:
  main:
    jobs:
      - evaluate
```

## Jenkins

```groovy
// Jenkinsfile
pipeline {
    agent {
        docker {
            image 'python:3.11'
        }
    }

    environment {
        OPENAI_API_KEY = credentials('openai-api-key')
    }

    stages {
        stage('Setup') {
            steps {
                sh 'pip install -e ".[all]"'
            }
        }

        stage('Evaluate') {
            steps {
                sh 'evaldeck run --output junit --output-file results.xml'
            }
            post {
                always {
                    junit 'results.xml'
                }
            }
        }
    }
}
```

## Configuration for CI

### Strict Thresholds

For production CI, require all tests to pass:

```yaml
# evaldeck.ci.yaml
version: 1

agent:
  module: my_agent
  function: run_agent

test_dir: tests/evals

thresholds:
  min_pass_rate: 1.0  # 100% must pass

defaults:
  timeout: 60         # Longer timeout for CI
  retries: 1          # One retry on failure
```

### Tag-Based Strategy

```yaml
# Critical tests - must all pass
evaldeck run --tag critical --config evaldeck.ci.yaml

# Non-critical tests - allow some failures
evaldeck run --tag experimental --config evaldeck.dev.yaml
```

## Handling Secrets

### GitHub Secrets

```yaml
env:
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### Environment Files

```yaml
- name: Setup environment
  run: |
    echo "OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }}" >> .env
    source .env
```

### Vault Integration

```yaml
- name: Get secrets from Vault
  uses: hashicorp/vault-action@v2
  with:
    url: https://vault.example.com
    token: ${{ secrets.VAULT_TOKEN }}
    secrets: |
      secret/data/evaldeck OPENAI_API_KEY | OPENAI_API_KEY
```

## Interpreting Results

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All tests passed |
| 1 | One or more tests failed |
| 2 | Configuration or runtime error |

### JUnit Report

```xml
<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="evaldeck" tests="10" failures="2" errors="0" time="45.2">
    <testcase name="book_flight_basic" classname="booking" time="1.2"/>
    <testcase name="book_flight_complex" classname="booking" time="2.1">
      <failure message="ToolCalledGrader failed">
        Expected tool 'confirm_booking' was not called
      </failure>
    </testcase>
  </testsuite>
</testsuites>
```

### JSON Report

```json
{
  "total": 10,
  "passed": 8,
  "failed": 2,
  "errors": 0,
  "pass_rate": 0.8,
  "duration_ms": 45200,
  "suites": [
    {
      "name": "booking",
      "results": [...]
    }
  ]
}
```

## Best Practices

### 1. Fast Feedback Loop

Run smoke tests on every PR:

```yaml
on:
  pull_request:
    branches: [main]

jobs:
  smoke:
    steps:
      - run: evaldeck run --tag smoke
```

### 2. Nightly Full Regression

```yaml
on:
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight

jobs:
  regression:
    steps:
      - run: evaldeck run --tag regression
```

### 3. Artifact Retention

Keep results for debugging:

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: eval-results-${{ github.sha }}
    path: results/
    retention-days: 30
```

### 4. Notifications

Alert on failures:

```yaml
- name: Notify on failure
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {"text": "Agent evaluation failed on ${{ github.ref }}"}
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

### 5. Cost Management

LLM graders cost money. Optimize CI:

```yaml
# Use cheaper models in CI
defaults:
  graders:
    llm:
      model: gpt-4o-mini  # Not gpt-4o

# Limit to critical tests in PRs
on:
  pull_request:
jobs:
  evaluate:
    steps:
      - run: evaldeck run --tag critical  # Not full suite
```
