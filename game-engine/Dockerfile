FROM python:3.12-slim

WORKDIR /app

# Copy package files
COPY pyproject.toml ./
COPY src/ ./src/

# Install the package and its dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Copy tests
COPY tests/ ./tests/

# Default command runs tests
CMD ["pytest", "tests/", "-v"]
