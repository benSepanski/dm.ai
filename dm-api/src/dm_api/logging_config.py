"""Central logging configuration for dm-api.

Call ``configure_logging()`` once at application startup (in ``main.py``).
After that, every module obtains its own logger with ``logging.getLogger(__name__)``
and inherits the root formatter.

Log format
----------
Each line looks like::

    2026-05-09 12:34:55,600 INFO     dm_api.api.ws  ws connect  session_id=abc total=1
    2026-05-09 12:34:56,789 INFO     dm_api.main  request  method=POST path=/api/sessions/abc/chat status=200 duration_ms=1430
    2026-05-09 12:34:57,401 INFO     dm_api.ai.dm_orchestrator  orchestrator done  session_id=abc ... duration_ms=1430

Key=value pairs in the message body are machine-readable so log aggregators
(Loki, CloudWatch Insights, Datadog, etc.) can extract fields without custom
parsers.

Configuration
-------------
Set the ``LOG_LEVEL`` environment variable (or ``log_level`` in ``.env``)::

    LOG_LEVEL=DEBUG    # show AI call details, token counts, request bodies
    LOG_LEVEL=INFO     # (default) major events only
    LOG_LEVEL=WARNING  # quiet mode

To upgrade to JSON-structured logging in production, replace the ``Formatter``
in ``configure_logging()`` with a JSON formatter (e.g. ``python-json-logger``).
The logger names and message structure are already aggregator-friendly.

Mocking in tests
----------------
Standard ``unittest.mock`` patterns work::

    with patch("dm_api.ai.condenser.logger") as mock_log:
        # assert mock_log.info.call_args ...

Or simply set the log level to WARNING in tests to silence chatty output::

    logging.getLogger("dm_api").setLevel(logging.WARNING)
"""

from __future__ import annotations

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging for the dm-api process.

    Safe to call multiple times (idempotent via handler-count check on the
    root logger).  Call once at FastAPI lifespan startup.

    Args:
        level: Log level string — DEBUG, INFO, WARNING, ERROR, CRITICAL.
    """
    numeric = getattr(logging, level.upper(), logging.INFO)

    root = logging.getLogger()
    if root.handlers:
        # Already configured (e.g. uvicorn set it up, or tests called us twice).
        root.setLevel(numeric)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root.addHandler(handler)
    root.setLevel(numeric)

    # Silence noisy third-party loggers that aren't useful at INFO level.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
