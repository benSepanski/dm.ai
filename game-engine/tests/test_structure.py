"""Structural tests that mechanically enforce harness-engineering rules.

These tests are the mechanical enforcement layer for the golden principles
in AGENTS.md and CLAUDE.md. They run in CI on every push and catch violations
that code review might miss.

Checks performed:
- No production file exceeds 400 lines (data files with noted exceptions are exempt).
- Every non-``__init__`` Python source file has ``from __future__ import annotations``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).parent.parent / "src" / "game_engine"

# Pattern: a line in the first 5 lines that documents why the file exceeds 400 lines.
# Matches any of the established NOTE patterns used in this repo.
_EXEMPT_PATTERN = re.compile(r"#\s*NOTE:.*(?:exceeds|intentionally exceeds).*400", re.IGNORECASE)

_PRODUCTION_FILES = sorted(SRC_ROOT.rglob("*.py"))
_ANNOTATED_FILES = [p for p in _PRODUCTION_FILES if p.name != "__init__.py"]


def _is_size_exempt(path: Path) -> bool:
    """Return True if the first 5 lines contain a size-exception NOTE."""
    try:
        with path.open(encoding="utf-8") as fh:
            for _ in range(5):
                line = fh.readline()
                if not line:
                    break
                if _EXEMPT_PATTERN.search(line):
                    return True
    except OSError:
        return False
    return False


@pytest.mark.parametrize(
    "path",
    _PRODUCTION_FILES,
    ids=lambda p: str(p.relative_to(SRC_ROOT)),
)
def test_file_within_400_lines(path: Path) -> None:
    """No production source file may exceed 400 lines without an explicit NOTE.

    To exempt a data file, add as the very first line::

        # NOTE: exceeds 400 LoC — <one-line reason>

    or the longer form from AGENTS.md.
    """
    line_count = path.read_text(encoding="utf-8").count("\n")
    if _is_size_exempt(path):
        return
    assert line_count <= 400, (
        f"{path.relative_to(SRC_ROOT)} has {line_count} lines (limit 400). "
        "Split the file or add a NOTE exemption comment at the top if it is "
        "a cohesive data table."
    )


@pytest.mark.parametrize(
    "path",
    _ANNOTATED_FILES,
    ids=lambda p: str(p.relative_to(SRC_ROOT)),
)
def test_future_annotations_present(path: Path) -> None:
    """Every non-init source file must declare ``from __future__ import annotations``.

    This enables forward references in type hints (PEP 563) and is required by
    the mypy configuration for this project.
    """
    text = path.read_text(encoding="utf-8")
    assert "from __future__ import annotations" in text, (
        f"{path.relative_to(SRC_ROOT)} is missing 'from __future__ import annotations'. "
        "Add it immediately after the module docstring."
    )
