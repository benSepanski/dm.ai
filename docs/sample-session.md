# Sample Session — "The Bells of Mirebrook"

A real, unedited playtest of dm.ai (2026-06-10), run end-to-end against a live
server with the `claude_cli` AI backend. Everything below — narration,
proposals, summaries — is verbatim model/API output. Setup steps are shown
with the API calls behind them; at the table you'd do the same through the
dashboard and Swagger UI (see [running-a-game.md](./running-a-game.md)).

This playtest also drove fixes that now live in the codebase — see
[Playtest findings](#playtest-findings) at the end.

## Setup

**World** — `POST /api/worlds/`:

```json
{
  "name": "Greyveil Marsh",
  "setting_description": "A fog-drowned river-town called Mirebrook clings to rotting stilts above the Greyveil Marsh, where lantern-lit barges ferry the dead downriver to a drowned cathedral. Lately the bells of the sunken church have begun ringing on their own, and the dead have started arriving at the docks before anyone reports them missing."
}
```

**Party** — `POST /api/characters/` twice: Dorn Ashvale (Human Fighter 3,
STR 16 / AC 16) and Kira Veth (High Elf Wizard 3, INT 16 / AC 12).

**Session** — `POST /api/sessions/` with both PC ids in
`player_character_ids`. From here on, everything happens in the chat box.

## Turn 1 — the opening scene

> **DM:** Set the opening scene: Dorn Ashvale (human fighter 3) and Kira Veth
> (high elf wizard 3) arrive in Mirebrook at dusk on a funeral barge, just as
> the sunken cathedral bells begin to ring on their own across the marsh.
> Establish atmosphere and give the players a hook.

The AI DM's reply (excerpt):

> The barge slides beneath the first of the lanterns at dusk — guttering
> tallow flames strung on ropes between the stilt-posts, yellowing the fog
> from below. […] It arrives before you can see it: the *smell*. Rot-wood and
> tallow, river-mud and something underneath — something sweet in the way old
> flowers are sweet, the way a room smells three days after someone dies in
> it and no window has been opened.
>
> […] Then the bells begin. Not a peal. Not a rhythm. A single sustained
> *clang*, resonating up from somewhere beneath the water to the south […]
> coming from no tower you can see — because the tower is thirty feet
> underwater, and has been for eleven years.
>
> On the dock, a man in a grey wool coat stands watching your barge with an
> expression you read immediately: he was not expecting you. […] "This is the
> third one this week," he says, to no one in particular.
>
> **What do you do?**

Alongside the prose, the same turn produced **three structured proposals**
that appear as reviewable cards in the dashboard's right panel (the raw
blocks are stripped from the chat — players only see the narration):

| Type | Name | Content highlights |
|---|---|---|
| location | Mirebrook | town; "economy built on death-logistics: coffin-wrights, ferrymen, preservationists" |
| character | Ossian Dray | NPC dock registrar; "Paperwork is a form of warding." |
| location | Cathedral of the Pale Lady | dungeon; "the clergy remained — those who could breathe water" |

## Turns 2–3 — investigation and an NPC

Turn 2 (the party inspects the early-arriving coffin) produced the session's
central mystery — bronze coins etched with necromantic sigils placed on the
corpse's eyes, and pine gouges *made from the inside of the lid* — plus a
proposed NPC. Turn 3 introduced **Maren Sill**, a surviving member of the
Watchers, the drowned cathedral's clergy, as a character proposal.

## Accepting proposals

`POST /api/ai/proposals/{id}/accept` on the Mirebrook and Maren Sill cards
(one click each in the UI). Both immediately became real entities:

- `GET /api/worlds/{id}/locations` now lists Mirebrook with its full
  description, lore, and history.
- Maren Sill exists as an NPC character row — and a `entity_update`
  WebSocket event pushed her onto every connected player's sidebar.

Note: character proposals carry roleplay fields only (traits, ideals, bonds,
flaws) — if an accepted NPC will see combat, PATCH in hp/ac/stats first.

## Turn 4 — asking for a rules call

> **DM:** Maren mentions a locked strongbox of Watcher records in the old
> tide-office. Kira wants to pick the lock with her thieves tools. What
> should she roll, against what DC, and what happens on a success or failure?

The AI's ruling (excerpt):

> **Dexterity (Thieves' Tools), DC 14.** […] If Kira **is not proficient**
> with thieves' tools, she rolls a straight Dexterity check. Wizards don't
> get the proficiency by default — she'd need a Criminal background, the
> Skilled feat, or similar.
>
> **On a Failure (10–13)** — The corroded mechanism grinds, pins slipping.
> The lock doesn't open — but a pin shears. […] **On a Hard Failure (9 or
> below)** — The lock jams completely. Getting it open now requires either a
> **Strength (Athletics) DC 16** to force the hasp — loud, destructive — or
> finding whoever holds the original key.

A correct 2024-rules call (tool proficiency, tiered failure consequences)
with table-ready stakes. For *resolved* mechanics — attacks, saves,
initiative — use the combat tracker instead: dice go through the
deterministic rules engine, not the AI.

## Ending the session

`PUT /api/sessions/{id}/end` generated this summary (stored on the session,
and fed to future sessions automatically):

> The party arrives in Mirebrook with a funeral barge and investigates a
> corpse bearing mysterious bronze coins inscribed with necromantic and
> conjuration magic—tokens that compel the dead toward a submerged cathedral.
> They meet Maren Sill, a Watcher survivor of the cathedral's flooding eleven
> years ago, who reveals that someone has recently reactivated an ancient
> death-rite […] Now they seek locked Watcher records that may expose who is
> distributing the coins and what has awakened in the deep.

## Next week — session 2 remembers

A new session was created in the same world, and the first message was:

> **DM:** Remind the party what happened in our last session before we continue.

The AI's recap — with **no manual context pasted** — correctly referenced the
bronze coins and their sigils, Maren Sill and the Watchers, the Sinking
eleven years ago, the self-ringing bells as a signal, and the locked records:

> You arrived in Mirebrook aboard a funeral barge […] Among the cargo of the
> dead, you discovered something wrong: one of the bodies carried **bronze
> coins** — strange tokens etched with necromantic and conjuration sigils.
> Not payment for passage. Something more like a **summons**. […] That's
> where you stand. The records are within reach. The bells rang again last
> night. **What do you do?**

This is the cross-session world context at work: the system prompt receives
the world's setting/lore plus the summaries of previous ended sessions.

## Playtest findings

Four playtest agents ran this stack hard: a campaign playthrough (above), a
combat-mechanics gauntlet (4 rounds, downing a goblin, edge-case fuzzing),
a full stage-change workflow (arrive in town → ask for an inn → AI
generates inn + innkeeper + rough patrons → dialogue → bar brawl with the
AI-created NPCs → map sync across two simulated player laptops → aftermath
narration), and a second multi-stage run ("The Ruined Watchtower": travel
rulings → proposal accept/reject → spellcaster combat → a PC driven to
0 HP → two combats in one session → cross-session recall of both fights).
Full loop verdicts: **zero HTTP 500s, no hangs, no malformed AI JSON**;
combat math was rules-correct down to melee-crits-on-unconscious counting
as two failed death saves; WebSocket fan-out was perfectly symmetric across
simulated players (80/80 and 96/96 events).

**Fixed as a result of these playtests:**

- A turn that proposes several entities (like Turn 1's three blocks) only
  captured the *first* proposal; the rest were silently dropped. All blocks
  are now extracted and stored.
- Raw `[PROPOSAL]` JSON stayed embedded in the chat narration players see.
  Blocks are now stripped; proposals live only in the review panel.
- The end-of-session summarizer answered the session's last open question
  instead of only summarizing. Its prompt now forbids continuing the
  conversation.
- A typo'd actor/target id in a combat action returned HTTP 200 and wrote a
  permanent garbage row into the combat log. Now a 404.
- Hostile NPCs rendered **party-blue** on the battle map (party membership
  was inferred from "exists in the world" rather than character type). Token
  color now follows `CharacterType`; the sidebar party panel lists PCs only.
- Enrolling a stat-less character (the shape an accepted AI proposal
  creates) silently fabricated a 10 HP / AC 10 placeholder. Combat start now
  fails loudly with a 422 naming the characters that need stats.
- **The AI confabulated combat outcomes** — the combat log never enters chat
  history, so "describe the aftermath" invented a result that contradicted
  the actual fight. Ending combat now writes a mechanical SYSTEM summary
  into the chat (rounds, final HP, who went down), and the AI narrates from
  it accurately.
- `themes` on world creation required objects instead of plain strings.
- **Death saves never rolled.** A PC at 0 HP just sat there — `next-turn`
  now rolls the dying creature's death save automatically at the start of
  its turn and logs it (natural 20 = back up at 1 HP).
- **Death-save progress was destroyed at combat end.** The end-combat sync
  now persists death-save state to the character record, and the SYSTEM
  summary reports it ("DOWN, death saves 1 success / 2 failure" / "DEAD").
- **Lowercase `char_class` silently became Fighter in combat** ("wizard" →
  Fighter). The bridge now matches class names case-insensitively.
- **Spellcasting had no real API surface** — save-DC spells, healing, AoE,
  and slot tracking had to be adjudicated in chat. The engine's
  spellcasting module is now wired to `POST .../combat/cast-spell`: spell
  attacks, save DCs, cantrip scaling, healing, rider conditions,
  concentration, and slot tracking with upcasting, with spent slots
  persisting on the character after the fight.
- **No in-combat healing or stabilize action** — the rescue play used to be
  "end combat, then PATCH". Downed PCs are now saved mid-fight via
  `cast-spell` (Cure Wounds / Healing Word), `heal` (potions, fiat), or
  `stabilize` (Medicine check).
- **The action economy wasn't enforced across requests** (two attacks in
  one turn both succeeded; Dodge/Dash/Help had no carry-over). Per-combatant
  turn state is now persisted: one action + one bonus action per turn,
  reset when the turn comes around; violations are 409s.
- **Mid-combat PATCHes were lost** — combatants were snapshotted at combat
  start, and ending combat wrote the snapshot back over your patch.
  Character PATCHes now write through to active combat snapshots.
- **No rest endpoints** — `POST /api/characters/{id}/rest` now applies the
  2024 short/long rest rules (hit dice healing, slot recovery, exhaustion).
  And `stats` PATCHes merge key-by-key instead of replacing the whole blob.
- **Monsters at 0 HP got PC-style death saves** — monsters now die outright
  at 0 HP (2024 PHB; death saves remain for PCs and NPCs).
- **`next-turn` didn't skip dead/unconscious combatants** — it now skips
  the dead and the stable unconscious. Dying PCs still get their turn:
  that's when their death save rolls.
- **Initiative ties had no DEX tie-break** — ties now break on Dexterity.
- **Failed (`cannot_act`) actions polluted the combat log** — rule
  rejections (incapacitated actor, economy spent) are now 409s that never
  enter the log or broadcast.

**Known issues (open):**

- Areas of effect are theater-of-the-mind: a multi-target spell takes an
  explicit `target_ids` list — the engine doesn't compute who's inside a
  20-ft radius from map positions (token positions are cosmetic).
- The cast-spell endpoint doesn't verify the spell is on the caster's
  known/prepared list or class spell list — the DM submits casts, so table
  discipline covers it.
- Opportunity attacks and readied attacks have a dedicated flow (submit
  `"Opportunity Attack"` / `"Readied Action"` to `combat/action` — see
  `docs/api.md`); reaction spells (Shield, Counterspell) do not — adjudicate
  in chat, though reaction-speed spells do consume the caster's reaction
  slot when cast via the API.
- Occasional narration slips: the AI can invent details beyond the
  mechanical summary or name proposed NPCs before acceptance. The system
  prompt now forbids both explicitly, which reduces but doesn't eliminate
  it — the AI DM is a strong co-pilot, not an infallible one, which is why
  the proposal review flow exists.
