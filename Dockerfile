FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for tree-sitter
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    tree-sitter>=0.20.0 \
    tree-sitter-python>=0.20.0 \
    tree-sitter-javascript>=0.20.0 \
    tree-sitter-typescript>=0.20.0 \
    tree-sitter-go>=0.20.0 \
    fastmcp>=0.1.0 \
    pydantic>=2.0.0

# Copy source code
COPY src/ ./src/
COPY test_xray.py ./
COPY run_server.py ./
COPY debug_treesitter.py ./
COPY README.md ./

# Set Python path
ENV PYTHONPATH=/app/src

# Default command
CMD ["python", "run_server.py"]