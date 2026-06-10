# Running a Game Night

A practical guide for using dm.ai to run a real D&D 5.5e session — one DM
laptop, players joining from their own devices over the local network, and a
campaign that persists between sessions. For endpoint details see
[api.md](./api.md); for system internals see [architecture.md](./architecture.md).

## 1. Before game night

### Start the stack

```bash
cp .env.example .env
# Set ANTHROPIC_API_KEY, or set AI_PROVIDER=claude_cli if you use Claude Code
docker-compose up
```

This brings up PostgreSQL (your campaign's permanent home), Redis, the API
(port 8000, migrations run automatically), and the UI (port 5173).

Without Docker, run the three pieces yourself — see "Running locally" in the
[README](../README.md). Either way, keep the API single-process: WebSocket
fan-out is in-memory.

### Sanity checks

- `curl http://localhost:8000/health` → `{"status": "ok", ...}`
- Open `http://localhost:8000/docs` — the interactive Swagger UI you'll use
  for character creation.

### Create the party

There is no character-builder UI yet; create PCs once via the Swagger UI
(`POST /api/characters/`) or curl. You need a world first — easiest order:

1. Open the dashboard, create your world + first session (this also gives you
   the world id, visible in the invite URL or via `GET /api/worlds/...`).
2. For each PC:

```bash
curl -X POST http://localhost:8000/api/characters/ \
  -H 'Content-Type: application/json' \
  -d '{
    "world_id": "<world-uuid>",
    "type": "pc",
    "name": "Kira Swiftblade",
    "race": "Human",
    "char_class": "Fighter",
    "level": 3,
    "hp_current": 28, "hp_max": 28, "ac": 17, "speed": 30,
    "stats": {"strength": 16, "dexterity": 14, "constitution": 14,
              "intelligence": 10, "wisdom": 12, "charisma": 8}
  }'
```

Monsters and NPCs are created the same way with `"type": "monster"` or
`"type": "npc"`. The party appears in the left sidebar and on the battle map.

## 2. LAN play — players join your session

1. Find your laptop's LAN IP (`ipconfig getifaddr en0` on macOS,
   `hostname -I` on Linux).
2. Open the dashboard **via that IP** yourself: `http://<lan-ip>:5173`.
   (The invite link copies whatever URL you're on — `localhost` would be
   useless to your players.)
3. Click **Copy Invite Link** in the top bar and share it. Players open
   `http://<lan-ip>:5173/session/<session-id>` in any browser.

Everything is live for every connected browser:

- your typed messages and the AI's replies (the DM message appears on player
  screens immediately, before the AI finishes thinking),
- combat tracker updates (initiative, HP, turns),
- battle-map token drags.

> **Trust note:** there is no authentication and no player/DM role split —
> every connected browser sees the full DM dashboard, including proposal
> accept/reject buttons and combat controls. Fine for friends on your wifi;
> agree on who presses what.

## 3. The play loop

1. **Narrate into the chat box.** You are the DM of record; the AI co-DM
   narrates scenes, voices NPCs, and adjudicates 5.5e rules.
2. **Review proposals.** When the AI invents something durable — a location,
   an NPC, a dungeon — it attaches a structured proposal that shows up as a
   card in the right panel. Accept it (it becomes a real DB entity, and
   characters/locations appear in the UI for everyone) or reject it with a
   note. Nothing enters your world without your say-so.
3. **Combat.** Use the combat tracker (right panel) to start combat — it
   rolls initiative through the real rules engine. Submit actions, advance
   turns, end combat; HP and conditions sync back to the character records.
   Combat resolution is engine-driven (deterministic dice, 2024 rules), not
   AI-driven. Two things to know:
   - Characters created from accepted AI proposals have **no combat stats** —
     give them hp/ac/stats (PATCH via the Swagger UI) *before* the fight, or
     combat start will refuse them with a clear 422. Stats can't be changed
     mid-combat (combatants are snapshotted at initiative).
   - Ending combat posts a system message into the chat with the mechanical
     outcome (rounds, final HP, who went down or died, death-save tallies),
     so the AI DM narrates the aftermath from what actually happened.
   - **When a PC drops to 0 HP:** keep advancing turns — the engine rolls
     their death save automatically at the start of each of their turns and
     logs it (natural 20 brings them back up at 1 HP; three failures kills).
     There's no in-combat heal/stabilize action yet, so the rescue play is:
     resolve the fight, end combat, then PATCH the character's
     `hp_current`/conditions to reflect the healing or stabilization you
     narrated. Death-save progress survives into the character record.
   - **Running a spellcaster:** the combat API resolves *attack-roll* spells
     well if you model them as attacks — e.g. Fire Bolt is an Attack action
     with `attack_details: {weapon_name: "Fire Bolt", damage_dice: "1d10",
     damage_type: "fire", attack_ability: "intelligence", is_ranged: true}`
     (to-hit comes out right; damage runs ~+INT high since attacks add the
     ability mod). Save-DC spells, healing, AoE, and spell slots have no API
     surface yet — adjudicate those in the chat (the AI gives solid rulings)
     and apply results via PATCH after the fight.
   - The engine doesn't enforce the action economy across requests — you're
     the only one submitting actions, so one attack per turn is on you.
4. **Battle map.** Toggle with "Show Map". Tokens mirror the combatants
   during combat (party = blue, enemies = red, downed = grey) and the party
   roster otherwise. Drag tokens — every connected screen follows. Positions
   are cosmetic (theater-of-the-mind engine; range/reach are flags on the
   attack), so use the map for shared spatial intuition, not strict
   measurement. Note: token positions are saved per-browser; someone joining
   mid-fight sees default positions until tokens move again.

## 4. Persistence — pausing, resuming, and next week

- **Everything durable lives in PostgreSQL** (worlds, characters, sessions,
  full chat history, proposals, combat state). The `postgres_data` Docker
  volume survives `docker-compose down` / `up`. Avoid `down -v` — that wipes
  the campaign.
- **Refreshing the page is safe.** Each browser remembers its session in
  localStorage and re-loads history from the server. Laptop sleep is also
  fine — the WebSocket reconnects and catches up automatically.
- **Bookmark the session URL.** `/session/<id>` is the canonical handle;
  anyone with it can rejoin.
- **End the session when you wrap** (`PUT /api/sessions/{id}/end`, or curl —
  there's no UI button yet). This generates a 2-3 sentence AI summary and
  stores it on the session.
- **Next week:** create a new session in the same world. The AI's system
  prompt automatically includes the world's setting, its lore, and the
  summaries of up to 10 previous ended sessions — so "remind the party what
  happened last time" actually works. The **New Session** button in the top
  bar detaches your browser from the current session (the session itself
  stays in the database).

## 5. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Players can't reach the UI | Use the LAN IP, not localhost; check OS firewall allows port 5173; vite must be running with the repo's config (binds all interfaces). |
| Chat hangs ~no reply | The AI call is in flight (10-60 s is normal, longer with `claude_cli`). Check API logs; with `AI_PROVIDER=anthropic`, verify `ANTHROPIC_API_KEY`. |
| Player screens stopped updating | The WebSocket auto-reconnects within ~2 s and re-syncs; if not, refresh — state reloads from the server. |
| "No active combat" 404 | Combat ended or never started; start it from the combat tracker. |
| `docker-compose up` UI changes not appearing | Only `src/` is volume-mounted; config changes (vite.config.ts, package.json) need an image rebuild: `docker-compose up --build ui`. |
| Wiped DB but browser stuck on dead session | The UI detects the missing session and returns to the new-session screen automatically. |

## 6. Sample session

See [sample-session.md](./sample-session.md) for a real transcript produced
by playtesting this exact setup, annotated with the API calls behind it.
