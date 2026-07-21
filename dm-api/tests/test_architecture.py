"""Structural test for the repo's <400-LoC file-length guideline.

CLAUDE.md's harness-engineering principles claim this guideline is "enforced
by code review and structural tests — not docstrings" (principle #8), but
until this test existed nothing actually checked it. Two route modules
(``api/sessions.py``, ``api/combat.py``) already carry an explicit in-file
``NOTE`` explaining a deliberate decision not to split further; they get a
frozen ceiling at their current size instead of the default 400 so the
exception stays visible and documented rather than silently drifting larger.
"""

from __future__ import annotations

from pathlib import Path

import dm_api

MAX_LINES = 400

# path (relative to the dm_api package root) -> documented ceiling. Frozen at
# today's size: growing further should prompt revisiting the file's in-file
# NOTE, not a silent bump of this dict.
_DOCUMENTED_EXCEPTIONS = {
    "api/sessions.py": 461,
    "api/combat.py": 423,
}

_PACKAGE_ROOT = Path(dm_api.__file__).resolve().parent


def test_no_module_exceeds_line_limit():
    modules = list(_PACKAGE_ROOT.rglob("*.py"))
    assert modules, "expected to find at least one dm_api module"

    offenders = {}
    for path in modules:
        rel = str(path.relative_to(_PACKAGE_ROOT))
        limit = _DOCUMENTED_EXCEPTIONS.get(rel, MAX_LINES)
        line_count = sum(1 for _ in path.open(encoding="utf-8"))
        if line_count > limit:
            offenders[rel] = (line_count, limit)

    assert not offenders, (
        f"Modules exceeding their line-count ceiling (default {MAX_LINES}; "
        f"see _DOCUMENTED_EXCEPTIONS for the frozen ceilings on files with "
        f"an in-file NOTE explaining why they're already over): {offenders}"
    )


def test_documented_exceptions_still_exist_and_carry_a_note():
    """Guard against the allowlist rotting: each entry must still be present,
    over the default limit, and still explain itself with an in-file NOTE."""
    for rel in _DOCUMENTED_EXCEPTIONS:
        path = _PACKAGE_ROOT / rel
        assert path.is_file(), f"{rel} no longer exists — remove it from _DOCUMENTED_EXCEPTIONS"
        text = path.read_text(encoding="utf-8")
        line_count = text.count("\n") + 1
        assert line_count > MAX_LINES, (
            f"{rel} is now under the {MAX_LINES}-line default — remove it from "
            "_DOCUMENTED_EXCEPTIONS instead of carrying a stale exception"
        )
        first_lines = "\n".join(text.splitlines()[:5])
        assert "NOTE" in first_lines, (
            f"{rel} is allow-listed as an oversized file but no longer carries "
            "the explanatory NOTE comment near the top — add one back or split the file"
        )
