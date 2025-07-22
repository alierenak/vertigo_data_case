# Multi-stage build for DBT on GCP Cloud Run
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy DBT project
COPY dbt_project/ ./dbt_project/
COPY load_data_to_bigquery.py ./
COPY run_dbt.py ./

# Set DBT profiles directory
ENV DBT_PROFILES_DIR=/app/dbt_project

# Create non-root user
RUN useradd --create-home --shell /bin/bash dbt
RUN chown -R dbt:dbt /app
USER dbt

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import dbt.main; print('DBT is ready')" || exit 1

# Default command
CMD ["python", "run_dbt.py"]