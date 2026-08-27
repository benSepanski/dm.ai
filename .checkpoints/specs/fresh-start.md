---
slug: fresh-start
status: approved
---

# Fresh start: reset dm.ai for a checkpoint-driven rebuild

## Problem

dm.ai has grown into a three-part stack (game-engine, dm-api, dm-ui) whose code
predates the checkpoint discipline now adopted for it. Ben wants to restart the
repository from scratch, claude-panski-v3 style: a single commit hard-deletes the
current implementation while git history and the repo identity remain, and every
piece of the rebuild goes through its own checkpoint (spec → architecture →
implement).

This checkpoint is the reset itself, not the rebuild. The rebuild happens as
future checkpoints.

## Requirements

1. A single commit removes **everything** from the working tree except git
   itself, the `.checkpoints/` scaffolding, the `.gitattributes` line that
   scaffolding requires, and the `.claude/settings.json` plugin enablement that
   keeps the checkpoints plugin active in this repo. No source, docs, CI config,
   agent instructions, README, or data files survive — nothing legacy remains to
   be built on.
2. Git history is preserved; the repo identity (remote, name) is unchanged.
3. The `.checkpoints/` files that exist (this spec, its architecture doc,
   approval records, `complaints.jsonl`, `.gitignore`) are committed as part of
   the reset. Git does not track empty directories; absent stage dirs reappear
   on demand.
4. After the reset, nothing in the working tree **outside `.checkpoints/`**
   references the legacy stack. The checkpoint record itself (this spec and its
   descendants) is exempt — it is history of the reset, not an input to the
   rebuild, and rebuild checkpoints must not treat it as one.
5. The reset commit adds no seed artifact — no README, no design doc. The first
   rebuild checkpoint creates whatever the fresh repo needs.
6. Before deleting, the implement stage runs `git status --ignored` and halts if
   anything is uncommitted or ignored-but-present (e.g. `.env`, virtualenvs,
   local data): Ben decides per item — commit, stash elsewhere, or confirm
   deletion — before the reset proceeds.

## User stories & flows

- **Ben resets the repo.** Ben accepts this checkpoint's report; the mechanical
  tail lands the reset commit on `main`. Cloning the repo afterwards yields a
  tree containing only `.checkpoints/`, `.gitattributes`, and
  `.claude/settings.json`.
- **A rebuild session starts clean.** Ben opens a new session in the reset repo
  and starts the first rebuild checkpoint. Nothing outside `.checkpoints/`
  mentions game-engine, dm-api, dm-ui, or D&D 5.5e specifics, so the design
  dialogue starts from Ben's intent alone.
- **Ben needs something from the old code.** He retrieves it deliberately via
  git history (`git log`, `git show <ref>:<path>`) — an explicit act, never an
  ambient influence on the rebuild.
- **Unhappy path — dirty or ignored files at reset time.** The pre-delete sweep
  halts and lists them; Ben commits, stashes elsewhere, or confirms deletion per
  item, then re-runs the reset. Nothing is deleted before the sweep passes.
- **Unhappy path — push rejected.** If branch protection or credential scope
  rejects the push, nothing is lost: the reset exists as a local commit; fix the
  push path and push again.

## Risks

- The delete is recoverable only through git history; anything not committed
  before the reset commit is lost. Mitigated: the `git status --ignored` sweep
  (req 6) runs first, and the reset lands as an ordinary reviewed commit — no
  history rewriting, no force-push.
- The reset is not atomic with the sweep. Mitigated: it runs as a single
  stop-the-world session — no other agent or session works this repo between
  sweep and commit.
- Deleting `.github/workflows/` over HTTPS needs a token with `workflow` scope,
  and `main` may have branch protection. **Accepted**: a rejected push loses
  nothing (see unhappy path); the tail retries via the repo's known HTTPS push
  workaround or a PR merge.
- Scrapping the SRD data registries and PHB-parity spec means the rebuild
  re-derives that content from scratch. **Accepted** — the point is that nothing
  legacy steers the rebuild.
- Out-of-repo references to deleted paths (session memory notes, open
  PRs/issues, muscle memory) will dangle after the reset. **Accepted**; cleaning
  those up is ordinary follow-up work outside this checkpoint.
- CI configured on the GitHub side may fail or hang on a tree with no code once
  workflows are deleted. **Accepted** — the first rebuild checkpoint sets up CI
  for the new stack.

## Out of scope

- The rebuild itself — every rebuilt piece is its own future checkpoint,
  including the new design doc, README, and CI.
- Any history rewriting, branch pruning, tag cleanup, or GitHub settings
  changes. Old branches and tags stay as they are.
- Archiving or exporting legacy content anywhere outside git history, and any
  cleanup of out-of-repo references (session memory, issue tracker).

## What Ben checks

- Clone (or `git ls-files` on) the repo after the merge: the tree holds only
  `.checkpoints/`, `.gitattributes`, and `.claude/settings.json`.
- `git log` still shows the full pre-reset history, and one ordinary commit
  performs the reset.
- Skim the surviving files outside `.checkpoints/`: nothing in them names or
  describes the legacy stack.
- Spot-check recoverability: pick one old file (e.g. the PHB parity spec) and
  confirm `git show` on a pre-reset ref still retrieves it.

## Review record

| Role | Verdict | Folded in |
|---|---|---|
| risk-reviewer | advice | ignored/untracked-file sweep (req 6), `.claude/` fate named, push-path risk, stop-the-world atomicity line, memory pruning descoped |
| user-advocate | advice | dirty-tree unhappy path resolved end-to-end, memory pruning removed from tail, `.checkpoints/` self-reference exemption (req 4) |
| scope-warden | advice | `.checkpoints/` exemption in req 4, memory pruning moved out of scope, req 3 phrased against files that exist |
