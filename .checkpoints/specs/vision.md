---
slug: vision
status: approved
---

# Vision: land the dm.ai product vision & roadmap doc

## Problem

The repo was reset to nothing; rebuild checkpoints start from intent alone. Ben's
intent is a LAN-served, AI-assisted DM table server, but that intent currently
lives only in conversation. Without a written, approved vision and roadmap, each
checkpoint spec re-derives the product from scratch and scope drifts.

This checkpoint lands `docs/VISION.md`: the product thesis, pillars, domain
vocabulary, and a checkpoint-sized roadmap that future specs cite instead of
re-arguing. It is a guide, not a contract — later checkpoints may revise it
through the normal frozen-doc re-approval flow.

## Requirements

1. `docs/VISION.md` exists on `main` and states the product thesis (local-first
   LAN table server; AI proposes, DM disposes), the design pillars, and the
   core domain vocabulary (campaign, entity, canon vs draft, proposal,
   character-as-decision-log, ruleset module, session).
2. The doc contains a roadmap of epochs — the next epoch broken into
   candidate checkpoint-sized slices, later epochs named at sketch level —
   ordered so that every slice is independently shippable and the earliest
   slices force the system-agnostic boundaries (multiple game systems, one
   class at a time).
3. The doc records the standing engineering disciplines future architecture
   docs draw constraints from (layering rules, schema-validated persistence,
   replay determinism, test-speed and perf budgets) — as intent, not yet as
   enforced tooling.
4. The doc is honest about non-goals (no cloud service, no VTT combat grid
   ambitions in v1, no accounts/internet auth) so specs can cite them when
   cutting scope.
5. Nothing else lands: no code, no tooling, no README beyond what the doc
   itself needs.

## User stories & flows

- **A future spec dialogue starts from the vision.** Ben starts a checkpoint;
  the spec skill reads `docs/VISION.md`, picks the next roadmap slice, and the
  dialogue argues only slice-level detail — never "what is this product".
- **Ben re-reads the vision after a month away.** The epochs and pillars let
  him re-enter the project and pick the next slice in minutes.
- **The roadmap turns out wrong.** A later checkpoint's dialogue contradicts an
  epoch's ordering; the vision doc is edited deliberately and re-approved
  diff-sized, same as any frozen doc.

## Risks

- The vision ossifies and later specs cite it instead of thinking. Mitigated:
  the doc's own text marks the roadmap as revisable guidance; epochs beyond the
  next one are explicitly non-binding.
- Ambition inflates early slices ("build the plugin system first"). Mitigated:
  requirement 2 forces every slice to be independently shippable; the roadmap
  orders vertical slices ahead of frameworks.
- **Accepted:** the doc encodes today's understanding of three game systems'
  licensing and rules structure, which may be stale; each system's first
  checkpoint re-verifies before shipping content.
- **Accepted:** nothing mechanically checks that shipped checkpoints stay
  consistent with the vision — divergence is caught only by humans re-reading
  the doc during spec dialogues; deliberate revision goes through re-approval.

## Out of scope

- Any code, scaffolding, CI, or tooling — the character-creation checkpoint's
  architecture owns those.
- Committing to a tech stack — that is an architecture-stage decision.
- Detailed specs for later epochs; the roadmap names slices, their specs are
  future dialogues.

## What Ben checks

- Read `docs/VISION.md` end to end: does it say what you meant — would you hand
  it to a collaborator as "this is the project"?
- Walk "a future spec dialogue starts from the vision": pick the slice you'd do
  after character creation; does the roadmap give you enough to start that spec
  dialogue without re-explaining the product?
- Intent check on non-goals: is anything listed as a non-goal that you actually
  want, or vice versa? Non-goals are the stickiest part of the doc — later
  specs will cite them as settled (especially the security posture), so read
  them as commitments.
- Read the standing disciplines list: is each one a constraint you'd accept
  being tool-enforced against you? They become build-failing tooling in later
  checkpoints, and this doc is the moment you review them as a set.

## Review record

| Role | Verdict | Folded in |
|---|---|---|
| risk-reviewer | clean | silent-drift accepted risk; non-goals-are-sticky note in What Ben checks |
| user-advocate | clean | disciplines-list intent check added to What Ben checks |
| scope-warden | advice | req 2 rescoped: slices for the next epoch only, later epochs at sketch level |
