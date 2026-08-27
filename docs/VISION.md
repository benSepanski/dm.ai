# dm.ai — Vision & Roadmap

> Status: DRAFT — pending the `vision` checkpoint's approval. The roadmap is
> guidance, not contract; epochs beyond the next are explicitly non-binding and
> revised through the normal doc re-approval flow.

## Thesis

dm.ai is a **DM's table server**: a self-hosted web app a DM runs on their own
machine at (or before) a session. Players connect over the LAN from browsers.
The DM uses it to build and maintain a detailed, internally consistent fantasy
setting with AI assistance — before the session (ahead-of-time prep) and in the
middle of one (just-in-time improvisation) — while players create, level, and
play their characters through it.

The one rule that defines the product: **AI proposes, the DM disposes.**
Generated content — an NPC, a shop, a stat block, a district, a plot hook — is
always a *proposal* until the DM accepts it into *canon*. Nothing enters the
world silently, and nothing the table saw is ever silently lost.

## Pillars

1. **DM sovereignty.** Every AI output is a reviewable draft with provenance.
   Accept, edit-then-accept, reject, or defer. Deferred content can live as
   *provisional* — visible at the table now, canonized or cleaned up later.
   Sovereignty is about control, not ceremony: eventually the DM can dial
   autonomy up with an opt-in **auto mode** where the AI acts first and the
   DM reverses — review replaced by reversibility, every auto action carrying
   the same provenance and being as undoable as a proposal. Propose-first is
   always the default; auto is a dial the DM turns, per scope, never a mode
   the product assumes.
2. **Local-first, files-first — hosting is a seam, not an assumption.** Play
   requires no cloud. Campaign data is human-inspectable files on the DM's
   disk — diffable, copyable, backed up by copying a directory, with git
   snapshots as the time machine. At this scale reliability comes from small
   legible state and aggressive full resync, not transactional machinery.
   But the LAN box is one *deployment*, not the architecture: storage,
   transport/connection, identity, and boot-up sit behind narrow high-level
   interfaces whose local/LAN implementations are specializations, so a
   hosted backend could be added later without a rewrite. The same layering
   tooling that keeps rulesets out of core keeps deployment specifics out of
   the domain. No cloud code gets written until a checkpoint asks for it —
   the discipline is in the seams, not in speculative implementations. (AI
   generation may call remote models; play never depends on it — every
   non-AI feature keeps working when the model is down.)
3. **System-agnostic core.** The core knows campaigns, entities, choices,
   proposals, and sessions — never fireballs. Game rules (D&D 5.5e, Pathfinder
   2e, Starfinder 2e) are data + modules behind one boundary. We keep the
   boundary honest by building multiple systems early, one class at a time,
   and enforcing the layering with tooling, not discipline.
4. **Crash-proof by construction.** A laptop lid closing, a battery dying, or
   a kill -9 loses at most the keystrokes in flight. Every durable mutation is
   journaled; the server restarts into exactly the state the table last saw;
   players reconnect without ceremony.
5. **Table-first UX.** During play, latency is the enemy: retrieving a monster
   or accepting a proposal must not stall the room. Slow AI work is masked with
   progressive results and never blocks the DM's view. Prep can be leisurely;
   play cannot.
6. **Rules are guardrails, not walls.** Validation explains itself, and the DM
   can override any rule with a recorded exception. Players are blocked from
   silent illegal edits, not from asking; the DM is never blocked at all.

## Domain vocabulary

| Term | Meaning |
|---|---|
| Campaign | The top-level unit: one world + one party + its sessions and canon. |
| Entity | Anything in the world: NPC, monster, location, faction, item, lore note. |
| Canon | Entity state the DM has accepted as true. |
| Proposal | Draft content (AI- or human-authored) awaiting DM review; carries provenance (prompt, source, time). |
| Provisional | Content used at the table before canonization; must be resolved, never silently persists. |
| Character | A player-owned entity whose mechanical state is a **decision log** — an ordered sequence of validated choices (ancestry, class, level-ups, retrains, DM exceptions), each bound to a choice slot with provenance. The sheet is a projection computed from the log. |
| Choice slot | A ruleset-defined decision point ("ancestry", "level-4 class feat", "free boost #3") with its option catalog, prerequisites, and validators. A class is a bundle of slots + options — which is what makes "one class at a time" shippable. |
| Sheet | The derived, never hand-authored projection of a decision log: labeled values, tracked pools, feature lists. Rendered through a thin presentation contract so the UI shares rendering without sharing game semantics. |
| Play state | The mutable at-the-table overlay (current HP, conditions, expended slots) — deliberately separate from the decision log. |
| Ruleset | A game system module: choice slots, option catalogs, validation, derivation (5.5e, PF2e, SF2e). Rulesets may share an engine layer (PF2e and SF2e run the same engine with different content). |
| Exception | A DM-approved rule override recorded in a decision log with its rationale. |
| Session | A bounded play period: who was at the table, what happened, what was generated/accepted. |
| Voice guide | Per-campaign style constraints (naming conventions, tone, prose register) that steer all generation. |
| Auto mode | Opt-in, per-scope policy where AI acts without pre-approval and the DM reverses; reversibility replaces review, provenance and undoability unchanged. |

## The two loops

**Prep loop (ahead-of-time).** DM sandboxes: "give me a border town with a
corrupt customs house" → proposals stream in → DM curates in batches — accept,
edit, reject, regenerate — building canon deliberately. Voice guide and
existing canon condition every generation.

**Play loop (just-in-time).** Players go off-script. DM needs a shopkeeper, a
stat block, a name *now*. One keystroke surfaces retrieval first (canon and
SRD content), generation second — with a degradation ladder: something usable
(name pools, templates, SRD blocks) in ~1 second, AI enrichment streaming in
after. Nothing modal, no decisions forced mid-scene: generated content lands
provisional in a session tray, playable immediately; the end-of-session sweep
walks the DM through canonize / edit / demote-to-log-note for everything the
table touched, in play order, with full context. The sweep is the ritual that
turns improvised chaos into curated canon.

## Roadmap

Epochs are ordered by dependency; slices within the next epoch are
checkpoint-sized (one spec → architecture → implement cycle each). Only the
next epoch's slices are commitments-in-waiting; everything later is sketch.

### Epoch 1 — Character creation (the spine)

The first vertical slice cuts through the whole stack — UI, validation,
persistence, ruleset boundary — so the architecture is real before it is big.
System order is chosen to stress the abstraction hardest, earliest:

1. **chargen-fighter**: guided level-1 character creation for the **PF2e
   Fighter**, in a real web UI, durably saved per confirmed step, resumable
   mid-wizard after tab close or server kill. PF2e goes first because it is
   the most structurally demanding system (boost provenance, four-tier
   proficiency, heritage/feat slots at level 1) — a core that survives it has
   real slot/prerequisite/replay machinery, where 5.5e level 1 would let us
   defer exactly the machinery we're trying to force. The decision-log core,
   ruleset boundary, presentation contract, and crash-safe persistence all
   exist from this slice.
2. **chargen-content**: full Player Core breadth for the Fighter wizard —
   all ancestries/heritages/ancestry feats, the full background list, the
   full level-1 Fighter feat and gear catalogs — pure data entry plus the
   reference-check pipeline, flowing into an already-working wizard. (Slice
   1 ships a representative subset only.) Also the natural home for the
   rules-published **quick build** fast path (one tap → legal character from
   the class's suggested choices); AI-suggested builds and backstories wait
   for the muse epoch.
3. **chargen-wizard**: the PF2e Wizard — forces the spellcasting shape
   (traditions, preparation, heightening, focus pools) inside one system
   before any cross-system abstraction of it. Also proves "adding a class is
   data + slot definitions, not core code."
4. **chargen-dnd**: **D&D 5.5e Champion Fighter** (SRD 5.2-safe) — the
   cross-system stress test: binary proficiency vs ranks, background-coupled
   ability scores vs boosts, subclass at 3 vs 1, weight vs Bulk. If the core
   survives PF2e Fighter → 5.5e Fighter without a rewrite, the abstraction is
   real. Expect the boundary to bend; budget for revising it deliberately.
   This slice also brings the first **dice** (rolled ability scores): rolls
   land in the decision log as recorded inputs — replay replays the recorded
   value, keeping derivation pure — with the full roll history logged
   (rerolls visible, manual physical-dice entry tagged as such). Reroll
   policy (e.g. "reroll if total modifiers below X") is table policy the
   DM configures, not app opinion; the details are that slice's spec
   dialogue, not settled here.
5. **level-up**: the level-up wizard as appended decisions on newly unlocked
   slots; retraining as log edits with replay revalidation; staged level-ups
   with DM-gated activation as a table setting.
6. **edits-and-exceptions**: editing tiers (free narrative fields / logged
   play-state / locked build mechanics with a fix-request flow), DM exceptions
   recorded as first-class override decisions, per-table trust mode
   (locked vs free-with-audit), and the change-history view.
7. **chargen-starfinder**: SF2e (e.g. Soldier) — deliberately last: it shares
   PF2e's engine, so it validates little about system-independence but is the
   payoff test. If it costs more than rules-data entry plus a small plugin
   delta (skills roster, credits, equipment traits), the PF2e plugin
   hard-coded things a shared engine layer should own.

### Epoch 2 — The table

Player connections and live play: LAN join via QR code with one-time claim
codes and device tokens (no accounts, no passwords; DM-assisted recovery on a
new device — the DM is physically present, that's the LAN superpower); sheet
visibility rules (DM-controlled ladder from status-only to full sheets); live
HP/conditions/resources with the DM authoritative over table state; the DM
party dashboard; reconnect/resync (sequence-numbered events, snapshot
fallback, stale badges, queued writes for your own character only — no CRDTs,
ever); session start/pause/resume surviving DM laptop death mid-combat.

Built per pillar 2's seam rule: hosting, connection/boot, identity/auth, and
session transport are high-level interfaces here, and this epoch ships their
*LAN specialization* — claim-codes-and-device-tokens is the local auth
routine, not the committed auth model. The epoch's architecture docs must
leave a hosted deployment able to specialize the same interfaces differently
(real accounts, TLS, remote transport) without touching the domain, and the
layering constraints enforce that separation from the first table slice.

Identity/visibility design is deliberately *not* front-loaded into Epoch 1
(decided 2026-08-28). Epoch 1 instead makes three structural commitments —
single server choke point for all data access, wire-types-≠-storage-types
(API responses are compiler-enforced field allowlists), identity-blind
engine crates — so that this epoch's design attaches at the route layer.
This epoch's spec dialogue explicitly asks whether ownership metadata forces
a migration of Epoch 1 character files; one migration there is the accepted
cost of not designing identity early.

### Epoch 3 — The world

The entity store and canon lifecycle: NPC/location/faction records with
draft / provisional / canon / rejected / archived states and provenance;
paragraph-level private vs player-visible facets, filtered server-side so the
player payload never contains a secret; fast search and monster/stat
retrieval (local and instant, no AI round-trip for known content); import of
DM notes with verbatim preservation. The setting-vs-campaign scoping split
enters the data model here even though forking ships later — retrofitting it
is brutal.

### Epoch 4 — The muse

AI enters: proposal objects with provenance (prompt, source, time), the
review-queue inbox with keyboard-fast triage, prep-loop batch generation with
drill-down that respects parent canon, play-loop JIT generation feeding the
session tray and end-of-session sweep, layered voice guides (naming
morphology, prose register, faction idiom, thematic palette) with every
generation citing the rules it applied, rejected content kept as negative
space steering future generations, and contradiction flagging — always
non-blocking, tuned precision-over-recall, attached late rather than adding
latency.

This epoch rides a deliberately minimal model seam — one provider, simple
one-shot harnesses — but every AI call goes through that seam and records
model, harness, and prompt version from the very first generation. The seam
widens in Epoch 5; the provenance discipline starts here.

### Epoch 5 — The engine room

The AI layer becomes real infrastructure, behind the same seam Epoch 4
started: multiple model providers (remote APIs and local models) selectable
per task; multiple harness shapes — one-shot queries, multi-step/agentic
workflows, and tool-using harnesses — chosen per generation type; telemetry
on every call (latency, cost, tokens, outcome) with DM-visible spend; the
feedback loop as data (accept/edit/reject rates per model/harness/prompt
feeding prioritization of what to improve next); and the **permission
model** for AI action — who may trigger generation (DM vs players), what a
given workflow may read (player-visible canon vs DM-private facets vs other
players' sheets), what it may write (proposal-only vs provisional vs
auto-mode scopes), and the auto-mode reversibility ladder from pillar 1.
Permissions is expected to be the hardest part of this epoch and may split
into its own checkpoints — or its own epoch — at spec time.

### Epoch 6 — The proving ground

Before deep play, the discipline for trusting AI workflows at all: an eval
harness for agent workflows (goldens for generation quality, canon-
consistency checks as assertions); regression attribution — every eval run
pinned to model + harness + prompt + code versions so a regression is
attributable to a model swap vs a harness change vs a code change, and
model-version-dependent behavior is pinned and migrated deliberately like
schema; user-validation flows (how a DM marks an output wrong in a way that
becomes a test case); and the interaction-modality decisions that testing
forces — is there a dialogue mode, how users supply free text vs structured
choices, and how each modality is validated. Capstone: **AI gameplay
workflows** — AI-driven players (and an AI DM) that run scripted and
free-play sessions against the real app as integration tests, exercising
character creation, table play, and generation flows end-to-end. Slices
here may deliberately land earlier, interleaved with Epochs 4–5, whenever
an AI feature ships ahead of its eval coverage — the roadmap position marks
when the discipline must be complete, not when it starts.

### Epoch 7 — Deep play

Session logs as a passive byproduct feeding AI recaps (player-facing built
only from player-visible events by construction); retcon with blast-radius
checklists over the reference graph (logs annotated, never rewritten);
campaign forking on the setting/campaign split; richer world generation
(maps, regions) with layered private/player annotations; timeline sanity
with fuzzy dates.

## Standing engineering disciplines

Every architecture doc draws on these; each emits them as enforced tooling
config, not prose:

- **Layering is tool-enforced.** Core never imports rulesets; rulesets never
  import each other or the UI; UI reaches persistence only through the API
  boundary. Violations fail the build.
- **All persisted data is schema-validated at every boundary**, with schema
  versions and migrations from day one — a campaign directory written this
  year must load in five.
- **Replay determinism.** A character sheet is a pure function of its decision
  log + pinned rules-data version; property tests assert replay reproduces
  stored projections, and wall-clock/randomness are banned from derivation
  code by lint rule. Replay is a verify/repair tool and history feature — the
  materialized sheet is the load path.
- **Rules data is versioned, license-tagged content.** Every rules-data record
  carries stable option IDs, a data version, and per-source license metadata
  (source, license, attribution string) from day one. Characters pin the data
  version they were built against; errata produce review flags, never silent
  sheet mutations.
- **Visibility is enforced server-side.** Anything a player must not know is
  absent from the payload, not hidden by the client — "player opens devtools"
  is inside the threat model.
- **Deployment seams are tool-enforced like rulesets.** Storage, transport,
  identity, and boot live behind interfaces; domain code never imports a
  deployment specialization directly, and the dependency rules that enforce
  the core/ruleset boundary enforce this one too.
- **Every AI call is attributed.** Model, harness, prompt version, cost, and
  outcome are recorded per call from the first generation ever shipped, so
  quality regressions are attributable (model swap vs harness vs code) and
  model-version-dependent behavior is pinned and migrated deliberately, like
  schema.
- **Fast tests are a budget, not a hope.** The default test suite has an
  asserted time ceiling; slow suites are quarantined behind an explicit tag.
- **Perf budgets are asserted** where the spec implies them (UI interaction
  latency, server restart-to-resume time), not admired in dashboards.
- **Crash safety is tested**, not assumed: kill-the-server-mid-write tests are
  part of the suite from the first persistence code.

## Non-goals (v1)

- No cloud service, hosting, accounts, or internet-facing auth — the threat
  model is a mischievous friend on the LAN, not the internet. (Pillar 2's
  seams keep a hosted deployment *possible* later; building one is still a
  non-goal until a checkpoint deliberately revises this.)
- No virtual tabletop combat grid / token movement; maps are artifacts to
  show, not a battle engine.
- No voice/audio, no video, no chat platform ambitions.
- No marketplace or third-party plugin distribution; rulesets ship in-repo.
- No non-SRD/ORC licensed content, ever; the app ships only what the licenses
  allow and makes DM-entered content obviously the DM's own.
- No general offline-first sync, CRDTs, or merge machinery — the table is
  physically colocated; aggressive full resync of small state wins.
- No TLS, password hashing, or rate limiting on the LAN server; no digital
  dice mandate (physical-dice tables are first-class — modifier lookup is a
  valid mode).
- The app never wins arguments: DM authority always beats app output, with a
  graceful, logged override.
