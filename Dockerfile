# Multi-stage build for smaller final image
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files and source code needed for installation
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/

# Create non-root user
RUN useradd -m -u 1000 recipeuser && \
    chown -R recipeuser:recipeuser /app

USER recipeuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    RECIPE_INGEST_LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Default to running the API server
CMD ["uvicorn", "recipe_ingest.api.app:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]

