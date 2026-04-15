FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
COPY ../game-engine /game-engine

RUN uv pip install --system -e /game-engine
RUN uv pip install --system -e .

COPY src/ ./src/

CMD ["uvicorn", "dm_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
