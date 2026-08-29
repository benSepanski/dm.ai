---
slug: chargen-content
status: approved
---

# Chargen slice 2 — architecture

> Drafted overnight against the draft spec (2026-08-28); delta pass before
> approval if spec approval changes requirements. This is a delta on the
> chargen-fighter architecture: every boundary, failure mode, and constraint
> there remains in force. This doc adds only what full content breadth, the
> reference pipeline, the first data-version bump, and quick build introduce.

## Situations

- **The workload is data entry; the engine must not learn new game words.**
  ~370 new records flow through existing slots. The spec's bounded machinery
  list (versatile heritages, background sub-choices, named Lores, two prereq
  kinds, proficiency-override/ranged-unarmed/fist-replacement effects,
  languages) lands entirely in `ruleset-pf2e` kind modules and `types`
  vocabulary — new effect variants, new slot registrations, no new
  engine-core concepts. What must never happen: engine-core growing a
  PF2e-shaped feature to make data entry easier, or a "flexible" effect DSL
  designed for content this slice doesn't ship.
- **Trust must be mechanical at this scale.** The trust chain: a pinned
  ground-truth snapshot → a deliberate, network-using tool run → a committed
  attestation keyed to the rules-data version → an offline CI check that the
  attestation is current, covers every record, and carries zero unwaived
  mismatches. What must hold: any rules-data edit invalidates the attestation
  until the tool is re-run. What must never happen: a byte of ground-truth
  content (Foundry values, text, files) committed to the repo or embedded in
  the attestation — match verdicts, field names, and hashes only; or CI
  needing the network.
- **The first data-version bump lands on live files.** Slice-1 characters pin
  `pf2e-pc.0.1.0`; this slice ships `0.2.0`, and pipeline corrections to the
  111 existing records are likely. What must hold: load stays read-only
  (status is computed, never written, at load — the no-rewrite-on-load check
  keeps passing); re-pin and accept-divergence are explicit API actions that
  write once, recording prior values in the file; no wizard operation replays
  an old log against new data before resolution. What must never happen: a
  sheet changing because the app was upgraded, or a record ID shipped in any
  prior version disappearing or changing meaning.
- **Quick build is a planner over the same engine, server-side.** One request
  expands into ordinary decisions: walk the open required slots in dependency
  order, resolve the suggested choice against the *folded draft state* (counts
  and catalogs depend on prior picks), append through the same validation,
  repeat until the checklist is empty or no suggestion applies. What must
  hold: the result is indistinguishable from a hand-built log except for
  provenance; one atomic durable write; a re-tap after a crash appends
  nothing. What must never happen: a client-side planner (the WASM engine
  previews, the server decides), an overwrite of a confirmed decision, or an
  all-or-nothing rollback that discards the legal prefix.
- **Breadth must not dull the live feel.** Projections now carry ~10x the
  option volume across the WASM boundary and the wire. What must hold: the
  fold budget unchanged; filtering happens in the UI over render-ready
  options (no new engine queries); the report measures projection payload and
  suite/rebuild/WASM-size deltas so regressions are visible before they are
  felt.

## Boundaries

The slice-1 diagram is unchanged. Additions:

```
  rules-data (JSON, v0.2.0, + attestation.json committed)
       ▲                          ▲ reads our records
       │ verifies                 │
  ┌────┴─────────────┐      ┌─────┴──────────────┐
  │ checks/ (offline: │      │ reference-check    │──network, tool-time only──▶ pinned
  │ attestation cur-  │      │ (native dev bin;   │   Foundry tag tarball
  │ rent, denylist,   │      │ never shipped, not │   → gitignored cache
  │ cross-refs, quick-│      │ in server/wasm     │   (no bytes committed)
  │ build folds clean)│      │ dep trees)         │
  └──────────────────┘      └────────────────────┘
```

- **`reference-check`** is a new workspace crate (binary): fetches the pinned
  ground-truth tag into a gitignored cache, matches records by
  publication-partition + normalized name with a reviewed override/waiver
  table, writes `rules-data/attestation.json`. Allowed edges:
  `ruleset-pf2e` + `types` (to parse our records). Nothing depends on it;
  it appears in the layering allowlist like any crate. AoN corroboration, if
  added, lives inside this tool.
- **Suggested build is content**: a block on the class record — ordered
  candidate option IDs per slot — interpreted directly by the planner walk
  (open slots in unlock order, resolve the block's entry against the folded
  draft state, append, refold). No per-slot `suggest` hook: one class and
  one build make that an interface with one consumer; a slot the block
  cannot parameterize simply stays open on the checklist. Server exposes
  one atomic quick-build route (create-and-fill, and fill-remaining on an
  existing draft) carrying the draft version like every write; these routes
  are wizard writes for every guard, including the version flag; the UI
  gets back a normal projection.
- **Provenance**: `DecisionSource` gains a `Suggested` variant. Storage
  schema bumps to v2 — the first real bump: v1 files are read-accepted
  (structurally identical), files are written as v2 on their next ordinary
  write, never on load. The downgrade guard (older binary refuses v2)
  already exists.
- **Version status** (current / older-known / unknown) is computed at load
  from one committed shipped-versions record (record IDs keyed by every
  shipped data version — the same artifact the ID-immutability lint reads,
  so lineage and immutability cannot drift apart) and exposed on roster and
  draft views; re-pin and accept-divergence are explicit routes writing
  through the same temp-file → fsync → rename discipline, storing the
  superseded pin and any superseded sheet values in the file.
- **UI**: filter and grouping are presentation over the existing option
  arrays — no new server queries, no game logic (the litmus test stands: a
  TUI needs zero Rust changes). Thresholded filter inputs live in the
  shared slot components, not per-step forks.

## Failure modes

- **Ground-truth tag unreachable / yanked at tool-time:** the tool fails
  loudly and changes nothing; CI is unaffected (offline). The attestation
  records the tag it was built from, so the run is reproducible when the
  network returns.
- **Ground truth itself is wrong** (Foundry transcription bug, or AoN/book
  disagreement): the book wins; the mismatch becomes a named waiver with a
  reason and the record's `source` keeps the book citation. Waivers are part
  of the attestation and reviewed like code.
- **Rules-data edited, attestation not re-run:** the offline check
  recomputes every current record's content hash and requires equality
  with the attested hashes — so an in-place value edit under an unchanged
  version string fails CI just like an added record (coverage gap) or a
  removed one (stale entry). This is the forcing function, not an error
  path. Waivers are bound to the hash of the mismatching state they excuse;
  a waiver matching no current mismatch fails the check rather than
  suppressing future drift.
- **Ground-truth cache torn or stale** (interrupted fetch, old tag): the
  tool verifies the cached snapshot against the pinned content hash before
  any matching; a mismatch refetches or fails loudly — it never attests
  against unverified content.
- **Denylist false positive** (a legitimate word matching a reserved noun):
  a per-record allowlist exception with a reason, colocated with the
  denylist; the lint output names the exception when it applies.
- **Quick build crashes mid-expansion:** the expansion is one engine
  transaction and one durable write; a crash before the write loses the
  whole expansion (re-tap rebuilds it), never a torn half-log. The re-tap
  carries a request-scoped idempotency ID: a retry after
  crash-between-save-and-ack returns the saved result and appends nothing.
  The crash harness gains a quick-build cycle.
- **Quick build cannot complete** (confirmed choices block suggestions, or a
  suggested pick opens a slot with no suggestion): the legal prefix is kept,
  the response says which slots remain and why, the checklist shows them —
  the same partial-draft state the wizard already renders.
- **Suggested build references a missing/renamed record:** data-lint
  failure at build time (cross-ref + folds-clean-and-finalizes checks), so
  it cannot ship; runtime never discovers it.
- **Old character, divergent replay:** roster flag with old/new values;
  sheet and file untouched until accept; wizard operations on a flagged
  draft are rejected with the flag attached. Accept from a stale tab hits
  the existing draft-version conflict machinery. A log that *errors* on
  replay (decision invalid under corrected data) carries the same flag
  naming the failing decision, with accept unavailable; "keep old
  derivation" is a recorded third outcome that stops re-flagging until the
  data version changes again.
- **Old character, unknown version** (hand-edit): unchanged slice-1
  behavior — loads read-only, `verify` says replay impossible; now
  distinguished from "older-known" in both `verify` output and roster
  status.
- **A v1 file in a v2 world:** reads fine (accepted structure), upgraded on
  its next write; `verify` treats it identically. A newer-than-the-binary
  file is refused *in place* with a clear roster message — never renamed
  aside (quarantine is for unparseable files, not valid files from the
  future), and a mixed-version dir refuses per file, loading the rest.
- **Filter typed faster than render at full catalog size:** filtering is
  in-memory over already-loaded options; if a list stutters, that is a UI
  bug to fix, not a budget to negotiate — no debounce-against-server
  machinery exists because no server call exists.

## Performance budgets

| Budget | Value | Asserted where |
|---|---|---|
| Derivation fold of a complete level-1 log | < 5 ms (unchanged, now over full catalogs) | native benchmark in `checks/perf.rs` |
| Default test suite wall time | < 20 s (unchanged; attestation check + goldens included) | CI timing gate |
| Warm incremental rebuild (engine → WASM + server) | < 10 s (unchanged; ~6x embedded data) | timed CI step; `--timings` artifact kept |

The budget levers are settled here so no budget decision lands mid-implement
(spec risk: "budget pressure"). If full data breaks a ceiling, apply in
order: (1) drop wasm-opt from the warm-rebuild loop only (release builds
keep it; the gate times the loop developers actually wait on); (2) quarantine
newly slow tests behind the existing slow tag (the default suite keeps its
20 s ceiling); (3) as the pre-authorized last resort, the warm-rebuild
ceiling may rise to 12 s — any further raise, or any other lever, is a
deliberate revision of this doc. Trimming shipped content is never a lever.
Design targets, hand-checked at review: projection payload growth measured
and reported (no asserted budget unless the wizard's feel degrades);
quick-build round trip feels instant on localhost; reference-check tool
runtime is irrelevant (deliberate, offline from CI's perspective).

## Constraints emitted

All slice-1 rows remain in force (layering allowlist, engine purity, forbid
unsafe, no-unlink, cargo-deny, wire≠storage, kind isolation, TS strictness,
bindings freshness, persistence round-trip, crash harness, confirm
idempotency, read-only load, server authority, replay determinism, rules-data
integrity, perf gates, CI on every push). New or amended rows:

| Rule | Enforced by | Config lives at |
|---|---|---|
| `reference-check` crate: may depend only on `ruleset-pf2e` + `types`; nothing depends on it; it never appears in `server`/`wasm` dep trees | layering test allowlist edit | `checks/crate_layering.rs` |
| No reserved proper noun in any record name or text; scrubbed records flagged; exceptions carry reasons | denylist lint over all rules-data (list + exceptions committed beside it) | `checks/rules_data.rs`, `rules-data/denylist.json` |
| Source book allowlist = {Pathfinder Player Core}; any new book requires a manifest-attribution edit in the same change | data lint | `checks/rules_data.rs` |
| Every cross-reference resolves: background skill-feat grants are IDs into the skill-feat catalog; suggested-build entries are IDs into shipped records | data lint (extends slice-1 cross-ref rule) | `checks/rules_data.rs` |
| Attestation current: exists, `version` equals manifest version, every record ID attested (both directions), zero unwaived mismatches; the check *recomputes* every current record's content hash and requires equality with the attested hashes; waivers are bound to the hash of the state they excuse and fail when matching no current mismatch; schema admits verdicts/field-names/hashes only (no ground-truth values or text) | offline standalone test | `checks/attestation.rs` |
| Ground-truth cache never committed, and CI never invokes `reference-check` (network stays out of CI) | gitignore + a test that the cache path is ignored and absent + a scan of the workflow file for the tool's invocation | `.gitignore`, `checks/attestation.rs` |
| ID immutability + lineage, one artifact: the committed shipped-versions record holds every shipped version's ID set; the lint requires the current manifest version present, every prior version's IDs resolvable in current data (wrong records deprecated — unselectable in new drafts, still resolvable — never deleted), and the server's older-known set drawn from this record | data lint | `checks/rules_data.rs`, `rules-data/shipped-versions.json` |
| Suggested build folds clean: expanding it on an empty draft yields zero illegal entries, an empty checklist, and a finalizable character | data-lint test through the real engine | `checks/quick_build.rs` |
| Fill-remaining preserves confirmed work: expanding on a fixture draft with confirmed choices leaves every pre-existing log entry byte-identical; when a confirmed choice blocks a suggestion, the legal prefix is persisted and the response names the unresolved slots — never an empty-handed rollback | standalone test through the real engine | `checks/quick_build.rs` |
| Quick-build server authority: the route re-validates natively; a raw request whose expansion would include an illegal entry is rejected and appends nothing; the route counts as a wizard write for the version guard (rejected on a flagged draft) | standalone test (extends the slice-1 authority pattern) | `checks/api_authority.rs`, `checks/version_guard.rs` |
| Quick-build atomicity + idempotency: SIGKILL during expansion leaves a loadable file containing either none or all of what the planner committed (a legitimate partial fill is "all"); a replayed request ID appends nothing | crash harness extension + standalone test | `checks/crash_harness.rs`, `checks/confirm_idempotency.rs` |
| Version guard: older-known + divergent (or replay-error) → flagged, file byte-identical until an explicit accept/keep-old action; older-known + identical → re-pin only via explicit action; wizard writes on a flagged draft rejected; accept records prior values, keep-old is recorded and suppresses re-flagging | standalone test with fixture characters pinned to a synthetic prior version (divergent, identical, and replay-error cases) | `checks/version_guard.rs` |
| Storage schema v2: v1 fixture reads, is not rewritten on load, upgrades on first write; v3 refused | persistence contract test (extends slice-1 rows) | `checks/persistence.rs` |
| Load remains read-only with version flags present | existing test, fixture added for a flagged character | `checks/no_rewrite_on_load.rs` |
| Golden coverage: one hand-verified build per ancestry, one versatile-heritage build, one background-sub-choice build, the quick-build character | golden tests | `checks/replay.rs` |

Deliberately unenforced, with reasons: "no Foundry bytes anywhere in the
repo" is enforced at the attestation schema and the ignored cache path — a
human pasting ground-truth text into a record field would pass tooling and is
left to review plus the denylist's noun coverage. A *forged* attestation
(verdicts hand-edited to green rather than produced by the tool) passes the
offline check by construction — unclosable without networked CI; the defense
is review: an attestation diff with no matching rules-data diff is the red
flag. "Filter appears above the threshold" and the scannability of long
lists are review-judged (UI feel is not machine-checkable; the spec's
table-distance check owns it). "Suggested build is editorially sensible" is
pinned by goldens but judged by Ben. The planner's suggestion completeness
(every required slot of the shipped build has a suggestion) is covered by
the folds-clean lint rather than a separate rule. "Never a client-side
planner" is structural — only the server's atomic route persists an
expansion, which the authority row asserts; the planner code compiling into
the WASM bundle is harmless preview capability, mirroring slice-1's
client/server-divergence entry.

## Review record

| Role | Verdict | Folded in |
|---|---|---|
| constraint-auditor | block, resolved | fill-remaining preservation row added; attestation row now recomputes per-record hashes (closing the same-version-edit hole); CI-never-invokes-reference-check clause; quick-build server-authority row + "never client-side planner" moved to deliberately-unenforced with the structural reason |
| failure-mode-reviewer | advice | hash recomputation and hash-bound stale-waiver invalidation made explicit; forged-attestation parked in deliberately-unenforced with the review defense; shipped-versions forcing lint; newer-version files refused in place (never renamed aside) + mixed-dir per-file behavior; quick-build routes named wizard writes under the version guard; harness wording fixed to "all of what the planner committed"; torn-cache verification bullet |
| simplicity-warden | advice | per-slot suggest hook dropped — the planner interprets the class-record block directly; shipped-ids fixture and manifest lineage consolidated into one committed shipped-versions record; folds-clean check pinned to `checks/quick_build.rs` |
