"""Structural test for the repo's <400-LoC file-length guideline.

CLAUDE.md's harness-engineering principles claim this guideline is "enforced
by code review and structural tests — not docstrings" (principle #8), but
until this test existed nothing actually checked it — a logic module could
grow past 400 lines silently. SRD content registries under ``data/`` are
exempt: they are literal data tables (weapon stats, spell text, monster
blocks), not logic, and several already legitimately exceed 400 lines.
"""

from __future__ import annotations

from pathlib import Path

import game_engine

MAX_LINES = 400

_PACKAGE_ROOT = Path(game_engine.__file__).resolve().parent


def _logic_modules() -> list[Path]:
    return [
        path
        for path in _PACKAGE_ROOT.rglob("*.py")
        if "data" not in path.relative_to(_PACKAGE_ROOT).parts
    ]


def test_no_logic_module_exceeds_line_limit():
    modules = _logic_modules()
    assert modules, "expected to find at least one game_engine module"

    offenders = {}
    for path in modules:
        line_count = sum(1 for _ in path.open(encoding="utf-8"))
        if line_count > MAX_LINES:
            offenders[str(path.relative_to(_PACKAGE_ROOT))] = line_count

    assert not offenders, (
        f"Modules exceeding the {MAX_LINES}-line guideline (split per "
        f"CLAUDE.md's harness-engineering principles, e.g. how _reactions.py "
        f"and _masteries.py were split out of _attacks.py): {offenders}"
    )
