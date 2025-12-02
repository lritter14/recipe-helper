# Multi-stage Dockerfile for Recipe Ingestion API
# Stage 1: Builder stage
FROM python:3.11-slim AS builder

# Set build arguments
ARG DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application source code
COPY src/ ./src/

# Set PATH to include user's local bin directory and PYTHONPATH for imports
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONPATH=/app/src

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8100

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8100/api/v1/health', timeout=5)" || exit 1

# Run the application
CMD ["uvicorn", "recipe_ingest.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8100"]
