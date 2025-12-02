FROM python:3.11-slim AS builder

WORKDIR /app

# Configure apt to handle repository issues and hash mismatches
RUN echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80-retries && \
    echo 'Acquire::http::Timeout "30";' >> /etc/apt/apt.conf.d/80-retries && \
    echo 'Acquire::Check-Valid-Until "false";' >> /etc/apt/apt.conf.d/80-retries

# Clean apt cache to avoid hash mismatches
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Update package lists with retry logic
RUN apt-get update -o Acquire::Check-Valid-Until=false || \
    (rm -rf /var/lib/apt/lists/* && sleep 2 && apt-get update -o Acquire::Check-Valid-Until=false) || \
    (rm -rf /var/lib/apt/lists/* && sleep 5 && apt-get update -o Acquire::Check-Valid-Until=false)

# Install minimal build dependencies (retry on failure)
RUN apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        liblzma-dev \
    || (rm -rf /var/lib/apt/lists/* && \
        apt-get update -o Acquire::Check-Valid-Until=false && \
        apt-get install -y --no-install-recommends \
            gcc \
            python3-dev \
            liblzma-dev) \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install Python package
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir .

# Final stage - minimal runtime image
FROM python:3.11-slim

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        xz-utils \
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
    CMD curl -f http://localhost:8100/api/v1/health || exit 1

# Default command
CMD ["uvicorn", "recipe_ingest.api.app:create_app", "--host", "0.0.0.0", "--port", "8100", "--factory"]
