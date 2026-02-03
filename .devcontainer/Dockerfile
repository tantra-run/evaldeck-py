FROM mcr.microsoft.com/devcontainers/python:1-3.11-bullseye

# Remove yarn repo (has expired GPG key) and install system dependencies
RUN rm -f /etc/apt/sources.list.d/yarn.list && \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspaces/evaldeck

# Upgrade pip
RUN pip install --upgrade pip

# Install Python development tools
RUN pip install --no-cache-dir \
    ruff \
    mypy \
    pytest \
    pytest-asyncio \
    pre-commit \
    build \
    twine

# Create directory for evaldeck output
RUN mkdir -p /workspaces/evaldeck/.evaldeck

# Set Python path
ENV PYTHONPATH="/workspaces/evaldeck/src:${PYTHONPATH}"
