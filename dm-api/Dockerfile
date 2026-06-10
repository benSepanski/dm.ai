# Build context is the repository root (see docker-compose.yml) so the
# game-engine package can be installed alongside dm-api.
FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY game-engine /game-engine
COPY dm-api/pyproject.toml .
COPY dm-api/src/ ./src/
COPY dm-api/alembic.ini .
COPY dm-api/alembic/ ./alembic/

RUN uv pip install --system -e /game-engine
RUN uv pip install --system -e .

CMD ["uvicorn", "dm_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
