---
slug: roster-ergonomics
status: approved
---

# Chargen slice 4: roster ergonomics — random character & clone

## Problem

Iterating on characters is expensive: every experiment starts with a
hand-built level-1 character, and the upcoming level-up slice multiplies
that cost — trying different level-2/3 paths means minting fresh subjects
over and over. Per the vision (revised 2026-08-30), this tiny slice ships
the two roster features that make characters cheap to mint and fork:
**random level-1 character** (one tap → a legal, named review draft) and
**clone** (duplicate any character as a new file and identity). Both have
product value beyond testing: pregens, quick NPCs, variants.

The random path builds on machinery that already exists: the quick-build
suggestion planner fills required slots from the class's published
suggestions and lands a normal draft. What is new: random legal picks
across every slot (independent of published suggestions, so repeated
mints vary — and classes without a published quick build, like the
Wizard, work too), a class choice, and a name generator.

## Requirements

1. The roster offers **Random character** beside create and quick build:
   pick a class (Fighter, Wizard) or "any" (uniform over shipped classes),
   one tap. The result is a normal draft with every required slot filled,
   landing at the review step exactly like quick build — one more click
   finalizes. The request is idempotent via a client request ID, same as
   quick build; the UI holds the pending request ID until the server
   acknowledges, so a failed tap surfaces a retry that reuses it (a fresh
   tap is a new mint).
2. Random slot filling is random for **every** slot — it never pins to the
   published quick-build suggestions, so repeated mints of the same class
   produce genuinely different builds (a Dexterity-line Fighter and a
   Strength-line Fighter are both reachable outcomes; the deterministic
   suggested build remains what the separate quick-build button is for).
   Each pick is drawn from the **legal** options — where legality includes
   set-level constraints: a group's remaining
   minimum (e.g. the Wizard's curriculum floor) narrows the legal option
   set for its later picks, so a random sequence can never strand a
   constraint it could still satisfy. A random pick is never illegal.
   For the shipped classes and data, every random mint fills every
   required slot; the existing quick-build "unresolved" surface remains
   as the safety net for future data where no legal option exists, and
   is expected to be unreachable this slice.
3. Generated picks are recorded as ordinary decisions in the log with a
   provenance source distinguishing them from player picks — random, and
   (for req 5) clone, beside the existing suggested source. Randomness runs once, at generation
   time, in the planner — never in derivation; replay replays the
   recorded decisions and `verify` passes on every random character.
4. Names come from **own-authored per-ancestry name pools** shipped as
   editable data (app data, not license-bearing rules records; growing a
   pool is a data edit, not a code change), at least a dozen names per
   shipped ancestry. The generated name fills the name slot; a user-typed
   name (optional, as with quick build) is never overwritten. A missing
   or empty pool falls back to a small ancestry-agnostic default pool; a
   malformed pool file fails the mint with a clear error — it never
   crashes the server and never writes a partial draft. Names need not be
   unique — the character ID is identity.
5. **Clone** works on any roster character, draft or finalized (not
   quarantined): a small dialog asks for the new name, prefilled
   "<name> (copy)", then creates a new character — new ID, new file, the
   same decision log and rules-data pin, with exactly one difference: the
   name decision records the clone-time name with clone provenance. The
   clone's sheet is re-derived by replaying the copied log under the same
   pin — clones are born verify-clean; a source whose stored sheet
   diverges from replay refuses to clone, pointing at `verify`. A cloned
   draft resumes at the same step with the same choices; a cloned
   finalized character is finalized, its sheet matching the original
   everywhere but the name. A clone of a character pinned to an older
   rules-data version inherits that pin and meets the established
   quiet-re-pin behavior on first open, like any other character. The
   clone is fully independent — no link back; deleting either leaves the
   other untouched. Clone idempotency uses the same client-request-ID
   scheme as quick build; a retried request returns the already-created
   character (the retried request's name is ignored — first write wins).
6. Existing flows are untouched: the wizard, quick build, fill-remaining,
   `verify`, and every existing character file behave exactly as before.
   The new provenance sources are new character-file vocabulary, so the
   character schema version bumps under the established
   schema-version-plus-migration discipline: every pre-slice file loads
   unchanged and `verify` handles both old and new provenance values. No
   rules-data version bump — name pools live outside license-tagged rules
   data.

## User stories & flows

- **Minting a test party.** Ben taps Random character → "any" three
  times: three named drafts land in review, each fully filled and legal
  (empty checklist), each finalized with one click. A whole test party
  exists in under a minute, and `verify` replays all three cleanly.
- **The class with no quick build.** Ben mints a random Wizard: thesis,
  school, and a curriculum-legal spellbook are all filled; the review
  step shows the picks with their "random" provenance; the finalized
  sheet's spellcasting block is derived and correct.
- **Clone and delete.** Before experimenting, Ben clones finalized
  Torvald as "Torvald B": the new sheet matches the original everywhere
  but the name. He deletes Torvald B later; Torvald is untouched. (The
  actual divergence experiment lives in the draft-fork story below —
  finalized characters stay uneditable until edits-and-exceptions.)
- **Forking a half-built draft.** Ben clones a mid-wizard draft; the
  clone resumes at the same step with every confirmed choice intact,
  and confirming different choices in the clone never touches the
  original.
- **The crash.** Ben taps Random character and kill -9s the server
  mid-mint. On restart the UI offers the failed mint's retry; the retry
  (same request ID) returns the draft if it was saved, or mints it if
  the crash landed first — either way exactly one new character exists.
  A fresh tap instead would be a legitimate second mint.
- **The skeptical inspection.** A random character's file reads like any
  other: a recognizable sheet and an ordered decision list, each
  generated decision marked as generated (and a clone's name decision
  marked as clone). Hand-tampering the sheet is still caught by
  `verify`.

## Risks

- **Random builds are legal but bad** (a Strength-dumped Fighter).
  Accepted: legality is the contract; quality is what quick-build
  suggestions are for. The review-step landing keeps a human glance
  before finalize.
- **Random generation exercises planner paths quick build never hit**
  (constraint interactions, the Wizard's curriculum minimum) and may
  surface latent planner bugs. Partly the point of the slice; req 2's
  constraint-narrowing rule is the mechanism that keeps it sound.
- **Clone's name-differs-from-log precedent.** A finalized clone's log
  differs from its source in one decision — the first time the app
  writes a finalized log it didn't walk through the wizard. Mitigated:
  the difference is exactly the name decision, carrying clone
  provenance; the sheet is re-derived from the copied log, so clones
  are born verify-clean and a corrupt source cannot propagate (it
  refuses to clone instead).
- **Name pools read as content** and could drift toward stereotype or
  accidental real-world/Golarion names. Mitigated: own-authored, small,
  editable data reviewed like any other data file.
- **Accepted:** cheap minting means abandoned drafts and trash files
  accumulate; cleanup stays manual (one-at-a-time delete) this slice —
  bulk operations are explicitly out of scope.
- **Accepted:** no bulk-mint, no "reroll just the name" button — minting
  again is cheap enough.

## Out of scope

- Random characters above level 1, random ability arrays, or any dice —
  the chargen-dnd slice owns dice; level-up owns levels.
- Published quick-build suggestions for the Wizard (wizard-content owns
  that); this slice's random fallback covers the Wizard.
- Bulk minting, bulk delete, party templates, NPC-specific features.
- Any other editing of finalized characters (edits-and-exceptions), and
  any clone-with-tweaks flow — clone is exact except the name.
- Renaming existing characters outside clone.
- Random name generation as a standalone tool surfaced in the UI.

## What Ben checks

- Walk "minting a test party": three random "any" characters, finalize
  each; eyeball each sheet for legality (checklist empty at review) and
  run `verify` across the roster.
- Mint three or four random Fighters in a row: confirm they genuinely
  differ from each other and from the quick-build Fighter (different
  attribute lines, ancestries, feats) — variety is the feature.
- Walk "the class with no quick build": mint a random Wizard, hand-check
  the spellbook against the school's curriculum minimum and the
  spellcasting block against the derived numbers.
- Mint one random character after typing a name first: the typed name
  stands, only the other slots are generated.
- Walk "clone and delete" on finalized Torvald: compare the two sheets
  side by side (only the name differs), delete the clone, confirm the
  original is untouched.
- Walk "forking a half-built draft": clone a mid-wizard draft, take the
  two drafts down different choices, confirm neither bleeds into the
  other.
- Walk "the crash": kill -9 mid-mint, restart, retry — confirm exactly
  one new character exists; then tap fresh and confirm that one is a
  second, distinct mint.
- Open a random character's file: are generated decisions legibly
  marked? Tamper with the sheet and confirm `verify` catches it; then
  confirm the tampered character refuses to clone.
- Read a dozen generated names per ancestry: do they fit the ancestry's
  flavor, and is the pool file something you'd happily edit by hand?
- Intent check: is minting a test subject fast and pleasant enough that
  you would actually reach for it — both for level-up testing next slice
  and for a pregen at a real table?

## Review record

| Role | Verdict | Folded in |
|---|---|---|
| risk-reviewer | advice | constraint-narrowing mechanism (req 2); name-pool failure modes (req 4); clone re-derives + refuses divergent source (req 5); schema-version bump for new provenance (req 6); stale-pin clone clause (req 5); clone retry first-write-wins (req 5); draft-accumulation accepted risk |
| user-advocate | advice | crash walk added to checks + retry mechanics surfaced (req 1, story); typed-name check; "clone and diverge" retitled "clone and delete"; unresolved surface marked expected-unreachable (req 2) |
| scope-warden | advice | one checkpoint, no split; set-level-constraint mechanism (req 2); clone provenance folded into reqs 3/5; clone idempotency mechanism named (req 5); pool-size floor stated (req 4) |
