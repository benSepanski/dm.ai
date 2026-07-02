#!/usr/bin/env python3
"""Structural test: mechanically enforce the file-length guideline (AGENTS.md
"Code Style — Non-Negotiable Rules" #3, CLAUDE.md golden principle #8).

Per harness-engineering (<https://openai.com/index/harness-engineering/>),
this rule is meant to be "mechanically enforced," not left to review alone.
Production Python files must be <= 400 lines and test files <= 600 lines,
UNLESS the file's first 5 lines contain a ``# NOTE:`` exception comment
explaining why (see AGENTS.md for the convention). Files with such a comment
are allowed to exceed the limit without bound — the comment is the signal
that a human reviewed and accepted the tradeoff.

Usage: python scripts/check_file_lengths.py
Exits non-zero and prints every violation if any file is over budget without
a NOTE comment.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# (src_dir, limit) pairs for production code.
PRODUCTION_ROOTS = [
    (REPO_ROOT / "game-engine" / "src", 400),
    (REPO_ROOT / "dm-api" / "src", 400),
]

# (tests_dir, limit) pairs for test code.
TEST_ROOTS = [
    (REPO_ROOT / "game-engine" / "tests", 600),
    (REPO_ROOT / "dm-api" / "tests", 600),
]

NOTE_PREFIX = "# NOTE:"
NOTE_SCAN_LINES = 5


def _has_exception_comment(path: Path) -> bool:
    with path.open("r", encoding="utf-8") as f:
        for _ in range(NOTE_SCAN_LINES):
            line = f.readline()
            if not line:
                break
            if line.lstrip().startswith(NOTE_PREFIX):
                return True
    return False


def _check_root(root: Path, limit: int) -> list[str]:
    violations: list[str] = []
    if not root.is_dir():
        return violations
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        line_count = sum(1 for _ in path.open("r", encoding="utf-8"))
        if line_count > limit and not _has_exception_comment(path):
            rel = path.relative_to(REPO_ROOT)
            violations.append(
                f"{rel}: {line_count} lines (limit {limit}) — add a "
                f'"{NOTE_PREFIX}" exception comment in the first '
                f"{NOTE_SCAN_LINES} lines if this is a genuinely necessary "
                "exception, otherwise split the file."
            )
    return violations


def main() -> int:
    violations: list[str] = []
    for root, limit in PRODUCTION_ROOTS:
        violations.extend(_check_root(root, limit))
    for root, limit in TEST_ROOTS:
        violations.extend(_check_root(root, limit))

    if violations:
        print("File-length guideline violations (AGENTS.md #3):\n")
        for v in violations:
            print(f"  - {v}")
        print(f"\n{len(violations)} file(s) over budget without a NOTE exception comment.")
        return 1

    print("File-length check passed — no unexplained violations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
