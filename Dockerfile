FROM python:3.13-slim AS base

WORKDIR /app

# Install system dependencies for polars, shap, and other native libs
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency files first for layer caching
COPY pyproject.toml requirements.txt ./

# Install the package with dev dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Copy source code
COPY . .

# Default: run the test suite
CMD ["pytest", "tests/", "-q", "--tb=short"]
