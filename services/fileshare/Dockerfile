FROM python:3.11-slim

# Install curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-cache

# Copy application code
COPY fileshare ./fileshare

# Create uploads directory
RUN mkdir -p /app/uploads

# Expose port
EXPOSE 5000

# Run the application
CMD ["uv", "run", "python", "-m", "fileshare.app"]
