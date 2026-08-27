# Fresh start — report

Checkpoint: `fresh-start` · Branch: `checkpoint/fresh-start` · Status: delivered

## What changed and why

The repository is reset. One commit (`2439047`) deletes the entire legacy stack —
game-engine, dm-api, dm-ui, docs, CI workflows, agent instructions, README,
everything — 257 files, 61,241 lines. The working tree now holds only
`.checkpoints/`, `.gitattributes`, and `.claude/settings.json` (the plugin
enablement). Git history is untouched: every deleted file remains reachable via
pre-reset refs, and the repo's remote and identity are unchanged. Nothing was
rewritten or force-pushed. The rebuild starts from intent alone, through future
checkpoints.

## How to verify

1. **The tree holds only the survivors** (walkthrough of "Ben resets the repo"):

```bash
git ls-files
```

   Expect exactly nine paths: seven under `.checkpoints/`, plus `.gitattributes`
   and `.claude/settings.json`.

2. **History is intact and the reset is one ordinary commit**:

```bash
git log --oneline | head -8
```

   Expect `2439047 fresh-start: reset the repository` at the top of the
   checkpoint branch, with the full pre-reset history (259 commits) below it.

3. **Nothing legacy outside `.checkpoints/`** — open `.gitattributes` and
   `.claude/settings.json`; neither names the old stack. Intent check: is this
   what you meant by "scrap it all so nothing legacy is mentioned"?

4. **Recoverability spot-check** (walkthrough of "Ben needs something from the
   old code"):

```bash
git show 626a7f1:docs/phb-parity-spec.md | head -5
```

   Expect the old PHB parity spec's opening lines.

## Constraints now enforced

None. The architecture doc's Constraints emitted table is deliberately empty:
the reset removes every toolchain that could host a check, and spec requirement
5 forbids seeding the tree with new artifacts. The tree-only-survivors invariant
is verified by your checks above and cannot silently regress.

## Decisions made inside the contract

- The pre-delete sweep found exactly one ignored-but-present file,
  `.checkpoints/ACTIVE` — the plugin's own gitignored run state, exempt as a
  checkpoint record. No `.env`, virtualenvs, or local data existed, so the
  per-item halt in spec req 6 never triggered.
- The ticket-plan commit precedes the reset commit on the branch; the deletion
  itself is still a single commit, as required.

## Agent evidence

- `git ls-files` after the reset lists exactly the nine survivor paths.
- `git show --stat 2439047`: 257 files changed, 61,241 deletions, 0 insertions.
- `git status --ignored=matching` before deletion: only `.checkpoints/ACTIVE`.
- No CI run: workflows are deleted on this branch by design; legacy CI noise on
  the PR is ignorable per the architecture doc.

## Complaints logged

Five entries in `.checkpoints/complaints.jsonl` this session (2026-08-27):
installation not smooth (driver); approval requested without showing the spec
(spec); spec dumped inline instead of side-panel only (spec); architecture doc
reads as a spec duplicate for small checkpoints (architecture); want to skip
the architecture stage when there is no entropy risk (architecture).
