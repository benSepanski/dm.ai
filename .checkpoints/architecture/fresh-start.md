---
slug: fresh-start
status: approved
---

# Fresh start — architecture

## Situations

- **The reset happens once, in one sitting.** A single session performs sweep →
  delete → commit → land. Nothing else touches the repo between the sweep and
  the commit; if the session dies mid-way, the tree is either untouched (before
  the delete) or fully staged in one commit (after) — never a half-deleted
  state left for someone to discover.
- **The tree afterwards is inert.** No build, no CI expectations, no tooling.
  What must hold: cloning yields only `.checkpoints/`, `.gitattributes`, and
  `.claude/settings.json`. What must never happen: a rebuild session finding
  legacy material outside `.checkpoints/` to latch onto.
- **History is the only archive.** Every deleted byte must remain reachable via
  pre-reset refs. What must never happen: history rewriting, force-pushes, or
  branch deletion riding along with the reset.

## Boundaries

```
working tree (deleted)      git history (untouched)      GitHub (one landing)
        |                           |                          |
   one reset commit  ───────────────┘                          |
        └────────────────── push / PR ─────────────────────────┘
```

- The reset commit touches only the working tree. It is forbidden from touching
  refs other than its own branch, tags, or GitHub settings.
- Landing path: a reset branch pushed to GitHub, landed by PR merge. The agent
  performs both the PR creation and the merge as part of the mechanical tail —
  the PR is plumbing, never a review surface; Ben's review already happened at
  the report gate. Legacy CI running against the PR is ignorable noise.

## Failure modes

- **Sweep finds dirt** (uncommitted / ignored-but-present files): the reset
  halts before any deletion; Ben sees the file list and decides per item.
  Nothing proceeds until the sweep passes clean. The checkpoint records the
  reset commit itself is about to stage (report, run state) are exempt — the
  sweep judges everything else.
- **Push rejected** (branch protection, missing `workflow` token scope): the
  reset survives as a local commit; Ben sees the rejection and the retry path
  (HTTPS workaround or PR). No data loss possible at this point.
- **Session dies mid-delete, pre-commit**: `git checkout .` / `git reset --hard
  HEAD` restores the tree exactly, because the sweep guaranteed everything was
  committed first. The reset re-runs from the top.
- **Merge blocked** (branch protection requires status checks that can never
  report on a tree whose workflows are deleted): the reset waits as an open PR;
  Ben sees the stall and either relaxes the required checks or admin-merges.
  Nothing is lost while the PR waits.
- **Concurrent remote push to `main`** between branch point and merge would
  reintroduce post-branch files into the merged tree. The stop-the-world rule
  covers local sessions only; the covering mode for remote drift is Ben's
  post-merge acceptance check, same as below.
- **Something legacy survives unnoticed**: caught by Ben's acceptance check
  (`git ls-files` must list only the three survivors). If found later, removing
  it is a trivial follow-up commit, not a re-run.

## Performance budgets

None — the spec implies no load or latency situation.

## Constraints emitted

| Rule | Enforced by | Config lives at |
|---|---|---|

None are enforceable here, because the reset removes every toolchain that could
host a check, and requirement 5 of the spec forbids seeding the tree with new
artifacts (a `checks/` script would be one). The tree-only-survivors invariant
is verified once by Ben's acceptance checks; it cannot silently regress, since
any regression requires a future commit adding files — which the rebuild's own
checkpoints govern. The history must-nevers (no force-push, no ref deletion)
are enforceable only server-side via branch protection — a GitHub settings
change the spec puts out of scope; Ben's `git log` acceptance check verifies
them instead.

## Review record

| Role | Verdict | Folded in |
|---|---|---|
| constraint-auditor | clean | explicit line on why history must-nevers are unenforceable (server-side only, out of scope) |
| failure-mode-reviewer | advice | merge-blocked mode with recovery, concurrent-remote-push mode named, sweep exemption for the reset commit's own checkpoint records |
| simplicity-warden | clean | none — PR-merge landing confirmed as the chosen path, not a fallback |
