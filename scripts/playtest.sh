#!/usr/bin/env bash
# Local playtest stack for dm.ai — runs the full UI + API with no Docker,
# no PostgreSQL, and no Redis, so coding agents (and humans without the
# full stack) can boot the app and drive it in a browser.
#
#   API  http://localhost:8000  (uvicorn, SQLite at .playtest/dm.db)
#   UI   http://localhost:5173  (vite dev server, proxies /api to the API)
#   AI   `claude` CLI backend (AI_PROVIDER=claude_cli) — no API key needed
#
# Usage:
#   scripts/playtest.sh setup    # install python venv + npm deps (idempotent)
#   scripts/playtest.sh start    # setup if needed, then boot API + UI
#   scripts/playtest.sh stop     # stop both servers
#   scripts/playtest.sh status   # report what is running
#   scripts/playtest.sh reset    # stop and delete the SQLite database
#   scripts/playtest.sh smoke    # run the Playwright smoke playtest
#
# Env overrides (export before calling):
#   AI_PROVIDER          claude_cli (default) or anthropic (+ ANTHROPIC_API_KEY)
#   ORCHESTRATOR_MODEL   defaults to Haiku here (fast/cheap playtests);
#                        production default is Sonnet — see dm_api/config.py
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT/.playtest"
VENV="$ROOT/.venv"
DB_FILE="$RUN_DIR/dm.db"
API_PID_FILE="$RUN_DIR/api.pid"
UI_PID_FILE="$RUN_DIR/ui.pid"

export AI_PROVIDER="${AI_PROVIDER:-claude_cli}"
export ORCHESTRATOR_MODEL="${ORCHESTRATOR_MODEL:-claude-haiku-4-5-20251001}"
export DATABASE_URL="sqlite+aiosqlite:///$DB_FILE"

setup() {
  if [ ! -x "$VENV/bin/python" ]; then
    if command -v uv >/dev/null 2>&1; then
      uv venv "$VENV"
    else
      python3 -m venv "$VENV"
    fi
  fi
  if ! "$VENV/bin/python" -c "import dm_api, game_engine, aiosqlite" >/dev/null 2>&1; then
    if command -v uv >/dev/null 2>&1; then
      uv pip install --python "$VENV/bin/python" -e "$ROOT/game-engine" -e "$ROOT/dm-api[dev]"
    else
      "$VENV/bin/pip" install -e "$ROOT/game-engine" -e "$ROOT/dm-api[dev]"
    fi
  fi
  if [ ! -d "$ROOT/dm-ui/node_modules" ]; then
    (cd "$ROOT/dm-ui" && npm install)
  fi
  echo "setup: ok"
}

running() { # running <pid-file>
  [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null
}

wait_for() { # wait_for <url> <name>
  for _ in $(seq 1 60); do
    if curl -sf -o /dev/null "$1"; then
      echo "$2: ready at $1"
      return 0
    fi
    sleep 1
  done
  echo "$2: did not become ready at $1" >&2
  return 1
}

start() {
  setup
  mkdir -p "$RUN_DIR"
  if ! running "$API_PID_FILE"; then
    "$VENV/bin/python" -m dm_api.db.bootstrap
    (cd "$ROOT/dm-api" && nohup "$VENV/bin/uvicorn" dm_api.main:app --port 8000 \
      > "$RUN_DIR/api.log" 2>&1 & echo $! > "$API_PID_FILE")
  fi
  if ! running "$UI_PID_FILE"; then
    (cd "$ROOT/dm-ui" && nohup npm run dev -- --strictPort \
      > "$RUN_DIR/ui.log" 2>&1 & echo $! > "$UI_PID_FILE")
  fi
  wait_for http://localhost:8000/health "api"
  wait_for http://localhost:5173/ "ui"
  echo "logs: $RUN_DIR/api.log  $RUN_DIR/ui.log"
}

stop() {
  for pid_file in "$UI_PID_FILE" "$API_PID_FILE"; do
    if running "$pid_file"; then
      # Kill the whole process group: `npm run dev` spawns vite as a child.
      pkill -P "$(cat "$pid_file")" 2>/dev/null || true
      kill "$(cat "$pid_file")" 2>/dev/null || true
    fi
    rm -f "$pid_file"
  done
  echo "stopped"
}

status() {
  running "$API_PID_FILE" && echo "api: running (pid $(cat "$API_PID_FILE"))" || echo "api: stopped"
  running "$UI_PID_FILE" && echo "ui: running (pid $(cat "$UI_PID_FILE"))" || echo "ui: stopped"
}

reset() {
  stop
  rm -f "$DB_FILE"
  echo "database reset"
}

smoke() {
  # The smoke test needs the playwright package; prefer a global install so
  # we don't bloat dm-ui's node_modules with a browser-automation dep.
  NODE_PATH="$(npm root -g)" node "$ROOT/scripts/playtest_smoke.cjs"
}

case "${1:-}" in
  setup) setup ;;
  start) start ;;
  stop) stop ;;
  status) status ;;
  reset) reset ;;
  smoke) smoke ;;
  *) echo "usage: $0 {setup|start|stop|status|reset|smoke}" >&2; exit 2 ;;
esac
