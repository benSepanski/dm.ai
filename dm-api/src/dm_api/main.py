from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator, Callable, Coroutine
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from dm_api.ai.backends import check_ai_readiness
from dm_api.api.auth import log_dm_token_source
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
    readiness = check_ai_readiness(settings.ai_provider, settings.anthropic_api_key)
    if readiness.ready:
        logger.info("AI backend ready  provider=%s", readiness.provider)
    else:
        # Loud, but don't crash the boot — the rest of the app (and /health) is
        # still useful while the operator fixes the AI config.
        logger.warning(
            "AI BACKEND NOT READY  provider=%s — %s "
            "The first chat turn will fail until this is fixed.",
            readiness.provider,
            readiness.detail,
        )
    log_dm_token_source()
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
async def log_requests(
    request: Request,
    call_next: Callable[[Request], Coroutine[Any, Any, Response]],
) -> Response:
    """Log method, path, status code, and wall-clock duration for every request."""
    start = time.monotonic()
    response = await call_next(request)
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
async def health() -> dict[str, object]:
    """Liveness plus AI-backend readiness so a bad config is catchable here."""
    readiness = check_ai_readiness(settings.ai_provider, settings.anthropic_api_key)
    return {
        "status": "ok",
        "service": "dm-api",
        "ai_provider": readiness.provider,
        "ai_ready": readiness.ready,
        "ai_detail": readiness.detail,
    }
