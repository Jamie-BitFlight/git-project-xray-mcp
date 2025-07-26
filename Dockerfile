# Stage 1: Builder
FROM python:3.11-alpine AS builder

# Set working directory
WORKDIR /app

# Install system dependencies for git (Alpine-specific)
RUN apk add --no-cache \
    build-base \
    git \
    libffi-dev \
    openssl-dev \
    python3-dev \
    && rm -rf /var/cache/apk/*

# Copy pyproject.toml and source code
COPY pyproject.toml .
COPY src/ ./src/

# Explicitly install tree-sitter and its language bindings first, preferring binary wheels
RUN pip install --no-cache-dir --only-binary :all: \
    "tree-sitter>=0.20.0" \
    "tree-sitter-python>=0.20.0" \
    "tree-sitter-javascript>=0.20.0" \
    "tree-sitter-typescript>=0.20.0" \
    "tree-sitter-go>=0.20.0"

# Install remaining Python dependencies (your project)
RUN pip install --no-cache-dir .

# Stage 2: Runtime
FROM python:3.11-alpine AS runtime

# Set working directory
WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy application source code (only essential files for runtime)
COPY src/ ./src/
COPY run_server.py .
COPY debug_treesitter.py .
COPY README.md .
COPY test_xray.py .

# Set Python path
ENV PYTHONPATH=/app/src

# Default command
CMD ["python", "run_server.py"]
