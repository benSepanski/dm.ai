# T7 — rules-data version guard (spec req 6)

## What shipped

Load-time version status (computed, never written), the four explicit
resolution routes, wizard-write gating on flagged drafts, the `verify`
older-known/unknown distinction, roster/sheet flag UI with resolve dialogs,
and `checks/version_guard.rs` + a flagged-character no-rewrite case.

## How "older known" is decided

`server::version::KnownVersions::assemble` intersects the embedded
manifest's `supersedes` chain with the key set of the embedded
`rules-data/shipped-versions.json` (the same artifact the ID-immutability
lint reads). A pin outside that set is `unknown` — replay impossible.

The manifest still says `pf2e-pc.0.1.0` with an empty `supersedes` chain;
the orchestrator's bump to `0.2.0` (adding `"supersedes": ["pf2e-pc.0.1.0"]`
and the new ID set in shipped-versions.json) makes the guard fire for real
slice-1 files with no further code change.

## Test-support surface (documented deviation from "no ambient config")

The workspace bans `std::env::var`, so the injection point is a **hidden CLI
flag**, not an env var:

    server --data-dir X --extra-known-versions <file> [verify]

The file has the same shape as `shipped-versions.json`; its versions are
merged into the older-known set (counting as both superseded and recorded).
TEST-SUPPORT ONLY: nothing in production passes it, it is hidden from
`--help`, and its use is announced on stderr
(`TEST-SUPPORT: --extra-known-versions active — …`). It exists so
`checks/version_guard.rs` can fabricate a prior shipped version
(`pf2e-pc.0.0.1-test`) with synthetic fixtures instead of touching shipped
data. Safety: it can only *widen* which old pins get a replay-based review
flag; it cannot change current data, alter derivation, or unlock writes that
bypass resolution.

## Storage additions (schema stays v2 — additive, defaulted)

- `version_history: [VersionEvent]` — appended only by the resolution
  routes; absent until the first resolution. Fields: `action`
  (`re_pin | accept | keep_old | resolve_replay_error`), `from`, `to`,
  `at_millis`, `note`, `superseded_values` (accept: old→new sheet values),
  `cleared_decisions` (resolve-errors: removed decisions verbatim).
- `keep_old: { pinned, evaluated_against, at_millis }` — standing keep-old
  marker; suppresses re-flagging while `evaluated_against` equals the
  shipped version; cleared by re-pin/accept/resolve.

Example (flagged divergent, then accepted):

```json
{
  "schema_version": 2,
  "id": "c-torvald",
  "rules_version": "pf2e-pc.0.2.0",
  "state": "finalized",
  "sheet": { "…": "now the replayed derivation" },
  "log": [ "…unchanged…" ],
  "version_history": [
    {
      "action": "accept",
      "from": "pf2e-pc.0.1.0",
      "to": "pf2e-pc.0.2.0",
      "at_millis": 1787000000000,
      "note": "accepted divergent replay; superseded values recorded",
      "superseded_values": [
        { "section": "Defense", "label": "AC", "old": "18", "new": "19" }
      ]
    }
  ]
}
```

## Routes added (all writes temp-file → fsync → rename, one write each)

- `POST /api/characters/{id}/version/repin` — older-known + identical only.
- `POST /api/characters/{id}/version/accept` — older-known + divergent only
  (identical → "use re-pin"; replay-error → typed refusal naming the
  failing decision).
- `POST /api/characters/{id}/version/keep-old` — finalized + older-known
  (any outcome). Drafts are refused: a draft cannot continue against
  mismatched data, so keep-old would be a dead end (spec's keep-old story
  is the character "usable at the table on its stored sheet").
- `POST /api/characters/{id}/version/resolve-errors` — draft + replay-error:
  clears the failing decision through the existing cascade
  (`clear_preview`-derived, repeated until the log folds), re-pins, records
  the cleared decisions. The flag's `would_reopen` list is what the UI
  shows as the explicit confirmation before calling.

All four take `{ "version": n }` and return
`resolved | conflict | refused` (conflict = stale draft version, same
machinery as confirms). Wizard writes (confirm/amend/clear/step/finalize)
on a draft with a non-current pin return **409** with
`VersionFlaggedError { message, status }`.

Draft resolution semantics: divergent/identical drafts resolve via
accept/repin — decisions are *kept*; any now-illegal decision surfaces
through the projection's existing checklist-Illegal machinery on the next
wizard render (the fold accepts it; validate flags it), and the player
re-picks via normal amend. Only a fold-rejecting log takes the
resolve-errors path.

## Views (all additive)

- `RosterEntry.version: VersionStatus`.
- `DraftView.version_status` (always `current` — flagged drafts are never
  projected; they arrive as `CharacterView::FlaggedDraft { id, name, sheet,
  version, status }` with the stored sheet and no projection, so no wizard
  operation replays an old log against new data outside the flow).
- `CharacterView::Finalized` gains `version_status` + `version`.
- `VersionStatus`: `current | older_known { pinned, current, outcome } |
  kept_old { pinned, evaluated_against } | unknown { pinned, current }`;
  `ReplayOutcome`: `identical | divergent { differences: SheetDiff[] } |
  replay_error { message, failing_decision, slot, would_reopen }`.

## verify

Old-pin lines are now `KEPT-OLD` (not a failure), `OLD-IDENT` (not a
failure), `OLD-DIVER` (failure, per-value diffs), `OLD-BROKE` (failure,
names the failing decision), and `UNKNOWN … replay impossible` (failure,
unchanged wording). Exit semantics unchanged (0 clean / 1 problems).

## UI

Roster badges per status; `VersionFlag.tsx` panel with the old-vs-new diff
table, re-pin / accept / keep-old actions, and the reopen-confirmation
dialog for draft replay-errors; `App.tsx` blocks a flagged draft behind the
panel (stored sheet shown read-only) and shows the panel above finalized
sheets.

## Checks

`checks/version_guard.rs` (8 tests): identical (flag + byte-identical until
explicit re-pin + recorded event), divergent (flag lists values, accept
records priors + stores new sheet), keep-old (recorded, suppresses across
restart), replay-error (names decision, accept refused, keep-old allowed),
wizard-writes-rejected-409-then-unblocked-after-resolve, draft
resolve-errors (would_reopen listed, cascade cleared, decisions recorded),
stale-version conflict, and the verify distinctions with exit codes.
`no_rewrite_on_load.rs` gained the flagged-character case (replay computed,
zero bytes written).
