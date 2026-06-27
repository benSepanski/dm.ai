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
# Set DM_TOKEN to a secret of your choosing — it's the password that
# unlocks DM controls in the UI. (Leave it unset and the API generates one
# per run, printed in its startup logs.)
docker-compose up
```

This brings up PostgreSQL (your campaign's permanent home), Redis, the API
(port 8000, migrations run automatically), and the UI (port 5173).

Without Docker, run the three pieces yourself — see "Running locally" in the
[README](../README.md). Either way, keep the API single-process: WebSocket
fan-out is in-memory.

> **`AI_PROVIDER=claude_cli` does not work inside Docker.** The API image is a
> plain Python base — it has no `claude` binary and none of your host's
> `~/.claude` authentication. If you set `claude_cli`, run the **API on the
> host** instead (see "Running locally" in the README), where it can find your
> installed, authenticated CLI. The Docker stack supports `AI_PROVIDER=anthropic`
> (with `ANTHROPIC_API_KEY`).

### Sanity checks

- `curl http://localhost:8000/health` → `{"status": "ok", ..., "ai_ready": true}`.
  If `ai_ready` is `false`, the AI backend is misconfigured (bad/placeholder
  `ANTHROPIC_API_KEY`, or `claude` not on PATH) — fix it **before** game night;
  `ai_detail` says what's wrong. The API also logs a loud warning at startup.
- Open `http://localhost:8000/docs` — the interactive Swagger UI you'll use
  for character creation.

### Create the party

PCs are built in the UI with the **Create Character** wizard (the button is
in the top bar; it's open to everyone, so players can roll up their own PCs).
The wizard is engine-backed — it walks through origin (class / species /
background), ability scores (standard array or point buy), and skills, then
applies the 2024 PHB rules for proficiencies, HP, AC, and spell slots so you
never hand-enter a stat block. Rule-bending choices come back as non-fatal
warnings on the review step. You need a world first — easiest order:

1. Open the dashboard, create your world + first session (this also gives you
   the world id, visible in the invite URL or via `GET /api/worlds/...`).
2. Click **Create Character**, pick your world, and run each PC through the
   wizard.

Editing a character afterward (`PATCH`) is DM-only — add an
`X-DM-Token: <your DM_TOKEN>` header when you call it via curl or Swagger.

The wizard is PC-only. Create monsters and NPCs via the Swagger UI
(`POST /api/characters/`) or curl with `"type": "MONSTER"` / `"type": "NPC"`
(like PC creation, this endpoint is open — no `X-DM-Token` needed):

```bash
curl -X POST http://localhost:8000/api/characters/ \
  -H 'Content-Type: application/json' \
  -d '{
    "world_id": "<world-uuid>",
    "type": "MONSTER",
    "name": "Dire Wolf",
    "char_class": null,
    "level": 1,
    "hp_current": 22, "hp_max": 22, "ac": 14, "speed": 50,
    "stats": {"strength": 17, "dexterity": 15, "constitution": 15,
              "intelligence": 3, "wisdom": 12, "charisma": 7}
  }'
```

The party appears in the left sidebar and on the battle map.

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

> **Roles:** the browser that holds the DM token (entered on the new-session
> form, or via **Unlock DM** in the top bar) is the DM; every other browser
> is a player. Players get a read-only view — no chat input, no combat
> controls, no proposal cards — and the server redacts DM-only data from
> their API responses: NPC/monster stat blocks and roleplay secrets,
> location lore/history, world lore, and all AI proposals. Don't share the
> DM token with the table.

## 3. The play loop

1. **Narrate into the chat box.** You are the DM of record; the AI co-DM
   narrates scenes, voices NPCs, and adjudicates 5.5e rules.
2. **Review proposals.** When the AI invents something durable — a location,
   an NPC, a dungeon — it attaches a structured proposal that shows up as a
   card in the right panel. Accept it (it becomes a real DB entity, and
   characters/locations appear in the UI for everyone) or reject it with a
   note. Nothing enters your world without your say-so.
3. **Combat.** Use the combat tracker (right panel) to start combat — it
   rolls initiative through the real rules engine (ties break on DEX).
   Submit actions, advance turns, end combat; HP, conditions, and spell
   slots sync back to the character records. Combat resolution is
   engine-driven (deterministic dice, 2024 rules), not AI-driven. All combat
   and rest endpoints below are DM-only — when calling them directly via
   curl or the Swagger UI, include your `X-DM-Token` header. Things to
   know:
   - Characters created from accepted AI proposals have **no combat stats** —
     give them hp/ac/stats (PATCH via the Swagger UI, with your
     `X-DM-Token` header) *before* the fight, or combat start will refuse
     them with a clear 422. A mid-combat PATCH also works: it writes through
     to the live fight and survives combat end.
   - Ending combat posts a system message into the chat with the mechanical
     outcome (rounds, final HP, who went down or died, death-save tallies),
     so the AI DM narrates the aftermath from what actually happened.
   - **When a PC drops to 0 HP:** keep advancing turns — the engine rolls
     their death save automatically at the start of each of their turns and
     logs it (natural 20 brings them back up at 1 HP; three failures kills).
     The rescue plays, all live mid-combat: cast a healing spell
     (`POST .../combat/cast-spell` with Cure Wounds or Healing Word), pour a
     potion (`POST .../combat/heal` with the amount), or stabilize after a
     DC 10 Medicine check (`POST .../combat/stabilize` — they stay down but
     stop rolling saves, and `next-turn` skips them). Monsters skip all of
     this: at 0 HP they die outright, and the dead are skipped on
     `next-turn`.
   - **Running a spellcaster:** `POST .../combat/cast-spell` resolves SRD
     spells end-to-end — spell attack rolls, save DCs, damage with cantrip
     scaling, healing, rider conditions, concentration, and slot tracking
     with upcasting (`slot_level`). Slots derive from class/level
     automatically and spent slots persist on the character after the
     fight; a long rest (`POST /api/characters/{id}/rest`) restores them.
     Multi-target spells like Fireball take a `target_ids` list (templates/
     areas are theater-of-the-mind: you pick who's in the blast).
   - **Between fights, rest instead of hand-patching:**
     `POST /api/characters/{id}/rest` with `{"rest_type": "short",
     "hit_dice_to_spend": 2}` or `{"rest_type": "long"}` applies the 2024
     rest rules (hit dice healing, slot recovery, exhaustion). PATCH still
     works for adjudicated changes — and `stats` now merges key-by-key, so
     clearing conditions doesn't require re-sending ability scores.
   - The action economy is enforced across requests: one action + one bonus
     action per combatant per turn (off-hand attacks use the bonus action;
     a spell consumes whichever its casting time says). A second attack in
     the same turn is rejected with a 409 — and Dodge/Dash/Help genuinely
     carry over until the combatant's next turn.
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
- **End the session when you wrap** with the **End Session** button in the
  top bar (DM only). This generates a 2-3 sentence AI summary and stores it
  on the session.
- **Next week:** create a new session in the same world. The AI's system
  prompt automatically includes the world's setting, its lore, and the
  summaries of up to 10 previous ended sessions — so "remind the party what
  happened last time" actually works. The **New Session** button in the top
  bar detaches your browser from the current session (the session itself
  stays in the database).

## 5. Operating your game — config, data & independent runs

A first-time operator hits a few sharp edges; here's where everything lives.

### Which config is in effect

- **The canonical config is the repo-root `.env`.** `docker-compose` loads it
  via `env_file`, so every Docker service reads it. Running the API **from
  `dm-api/` does _not_ load the root `.env`** — settings like `DM_TOKEN` then
  fall back to defaults. When running the API on the host, start it from the
  repo root (or pass an explicit env file) so the same `.env` applies.
- **Effective config is observable.** `GET /health` reports the active
  `ai_provider` and whether it's ready; the API also logs the provider, models,
  and DM-token source at startup. Per-world overrides (provider, models, context
  budget, storage URLs) live in the **Game Settings** modal and
  `GET/PUT /api/worlds/{world_id}/config`.

### The DM token

- `DM_TOKEN` is the password that unlocks DM controls. **Set it explicitly.**
  If it's unset, the API generates a *new* token on every startup (printed in
  the logs) — which silently invalidates any browser you'd already unlocked.
  Pinning `DM_TOKEN` in `.env` keeps the DM logged in across restarts.

### Where your data lives & backups

- All durable state is in PostgreSQL, persisted in the `postgres_data` Docker
  volume (see §4). To back up or move a campaign, dump the database:

  ```bash
  # Back up
  docker-compose exec -T db pg_dump -U dmuser dmdb > campaign-backup.sql
  # Restore into a fresh stack
  docker-compose exec -T db psql -U dmuser dmdb < campaign-backup.sql
  ```

- A "game" is identified by its world id (and the session ids under it),
  visible in the session URL and via `GET /api/worlds/...`.

### Running independent games

- Everything shares one database and one in-process WebSocket registry, so a
  single stack is one logical deployment. To run **two isolated games in
  parallel** (separate data and ports), start a second stack with its own
  Compose project name and host ports:

  ```bash
  # Second, isolated instance: distinct volumes + ports
  docker-compose -p dmai-table2 up
  # (override the published 5173/8000/5432 ports in an override file or env)
  ```

  The `-p` project name gives the second stack its own `postgres_data` volume,
  so the two campaigns never share state.

### Which provider needs which runtime

- `AI_PROVIDER=anthropic` works anywhere (Docker or host) given a valid
  `ANTHROPIC_API_KEY`. `AI_PROVIDER=claude_cli` requires the **API on the host**
  with an installed, authenticated `claude` CLI — it cannot run in the Docker
  image (see §1).

## 6. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Players can't reach the UI | Use the LAN IP, not localhost; check OS firewall allows port 5173; vite must be running with the repo's config (binds all interfaces). |
| Chat hangs ~no reply | The AI call is in flight (10-60 s is normal, longer with `claude_cli`). Check API logs; with `AI_PROVIDER=anthropic`, verify `ANTHROPIC_API_KEY`. |
| Player screens stopped updating | The WebSocket auto-reconnects within ~2 s and re-syncs; if not, refresh — state reloads from the server. |
| "No active combat" 404 | Combat ended or never started; start it from the combat tracker. |
| `docker-compose up` UI changes not appearing | Only `src/` is volume-mounted; config changes (vite.config.ts, package.json) need an image rebuild: `docker-compose up --build ui`. |
| Wiped DB but browser stuck on dead session | The UI detects the missing session and returns to the new-session screen automatically. |

## 7. Sample session

See [sample-session.md](./sample-session.md) for a real transcript produced
by playtesting this exact setup, annotated with the API calls behind it.
