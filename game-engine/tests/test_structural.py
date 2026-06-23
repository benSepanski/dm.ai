"""Structural tests enforcing code-quality invariants (CLAUDE.md § golden principles).

These tests are mechanical guards so principles don't drift silently:
  - No source file exceeds 400 LoC unless annotated as a known exception.
  - Annotation token: any line matching ``# NOTE: exceeds 400 LoC``.
"""

from __future__ import annotations

import pathlib

_SRC_ROOT = pathlib.Path(__file__).parent.parent / "src"
_MAX_LINES = 400
_EXCEPTION_MARKER = "# NOTE: exceeds 400 LoC"


def _source_files() -> list[pathlib.Path]:
    return list(_SRC_ROOT.rglob("*.py"))


def _is_annotated_exception(path: pathlib.Path) -> bool:
    """Return True if the file declares itself a known LoC exception."""
    try:
        # Only read the first 5 lines — the annotation is always at the top.
        lines = path.read_text(encoding="utf-8").splitlines()[:5]
    except OSError:
        return False
    return any(_EXCEPTION_MARKER in line for line in lines)


def test_no_source_file_exceeds_400_loc() -> None:
    """Every game-engine source file must be ≤ 400 lines or carry an explicit annotation.

    Data-only registries (monsters, feats, weapons, spell lists) that legitimately
    exceed 400 lines must include a ``# NOTE: exceeds 400 LoC`` comment in their
    first five lines to opt out of this check.
    """
    violations: list[str] = []
    for path in _source_files():
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        if line_count > _MAX_LINES and not _is_annotated_exception(path):
            rel = path.relative_to(_SRC_ROOT)
            violations.append(f"{rel}: {line_count} lines")

    assert not violations, (
        f"The following game-engine source files exceed {_MAX_LINES} lines without an "
        f"exception annotation ({_EXCEPTION_MARKER!r} in the first 5 lines):\n"
        + "\n".join(f"  {v}" for v in sorted(violations))
    )
