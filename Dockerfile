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

# Copy entrypoint script
COPY docker-entrypoint.sh /app/docker-entrypoint.sh

# Set PATH to include user's local bin directory
ENV PATH=/home/appuser/.local/bin:$PATH

# Set PYTHONPATH for imports (must be set after copying source)
ENV PYTHONPATH=/app/src

# Make entrypoint script executable
RUN chmod +x /app/docker-entrypoint.sh

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Port configuration - fully configurable via API_PORT env var in docker-compose
# No EXPOSE needed - docker-compose ports mapping handles actual port exposure
# Default port if not specified (can be overridden in docker-compose)
ENV API_PORT=8100

# Health check (uses API_PORT env var, defaults to 8100 if not set)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD sh -c 'python -c "import urllib.request, os; port=os.getenv(\"API_PORT\", \"8100\"); urllib.request.urlopen(f\"http://localhost:{port}/api/v1/health\", timeout=5)"' || exit 1

# Run the application
# PYTHONPATH is baked into image (/app/src) - no need to set in docker-compose
# Port is fully configurable via API_PORT environment variable in docker-compose
# Using JSON form for proper signal handling
ENTRYPOINT ["/app/docker-entrypoint.sh"]
