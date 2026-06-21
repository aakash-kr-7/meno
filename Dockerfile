# ==============================================================================
# (a) What this file is: Dockerfile for the MENO API service.
# (b) What it does: Defines container steps to install compiler dependencies, pip install the package, and copy code.
# (c) How it fits into the MENO system: Standardizes deployment and local container execution for the API service.
# ==============================================================================

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml
COPY pyproject.toml .

# Create minimal directory and init to let setuptools succeed for dependency cache
RUN mkdir -p core apps/api && touch core/__init__.py apps/__init__.py apps/api/__init__.py && pip install --no-cache-dir .

# Copy the rest of the application
COPY . .

# Re-install package to copy final code
RUN pip install --no-cache-dir .

# Default runtime command
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
