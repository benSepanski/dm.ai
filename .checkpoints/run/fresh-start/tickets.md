# fresh-start — tickets

Resumable plan. Approved docs: `.checkpoints/specs/fresh-start.md`,
`.checkpoints/architecture/fresh-start.md`. Branch: `checkpoint/fresh-start`.

- [x] 1. Apply the architecture's Constraints emitted table — table is empty
      with a recorded justification (reset removes all toolchains; spec req 5
      forbids seed artifacts). No-op by design.
- [ ] 2. Pre-delete sweep: `git status --ignored`. Halt on any uncommitted or
      ignored-but-present file; Ben decides per item (commit / stash elsewhere /
      confirm deletion). Exempt: checkpoint run records this reset stages.
- [ ] 3. Delete everything in the working tree except `.checkpoints/`,
      `.gitattributes`, `.claude/settings.json`. Includes ignored files Ben
      confirmed for deletion in ticket 2.
- [ ] 4. Single reset commit on this branch; verify `git ls-files` lists only
      the survivors.
- [ ] 5. Report at `.checkpoints/run/fresh-start/report.md`; present to Ben.
- [ ] 6. (post-acceptance mechanical tail) remove ACTIVE, push branch via the
      HTTPS workaround, open PR (plumbing-only body linking the report), merge,
      delete branch.
