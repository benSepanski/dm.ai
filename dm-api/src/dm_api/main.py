import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from dm_api.api.router import router
from dm_api.config import settings
from dm_api.logging_config import configure_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging(settings.log_level)
    logger.info(
        "dm-api starting up  ai_provider=%s orchestrator=%s",
        settings.ai_provider,
        settings.orchestrator_model,
    )
    yield
    logger.info("dm-api shutting down")


app = FastAPI(
    title="dm.ai API",
    description="AI-powered Dungeon Master toolkit API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next: object) -> Response:
    """Log method, path, status code, and wall-clock duration for every request."""
    start = time.monotonic()
    response: Response = await call_next(request)  # type: ignore[operator]
    duration_ms = int((time.monotonic() - start) * 1000)
    logger.info(
        "request  method=%s path=%s status=%s duration_ms=%d",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


app.include_router(router, prefix="/api")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "dm-api"}
