# Test service Dockerfile
FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /tests

# Copy test dependencies
COPY tests/pyproject.toml tests/uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy test files
COPY tests/ ./

# Run tests with verbose output
CMD ["uv", "run", "pytest", "-v", "--tb=short"]
