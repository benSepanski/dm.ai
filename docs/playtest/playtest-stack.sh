#!/usr/bin/env bash
#
# playtest-stack.sh — bring the dm.ai stack up/down for a UI playtest.
#
# This is the *host* run path used by the agentic UI playtest (see README.md):
#   - Postgres + Redis run in Docker (docker-compose).
#   - The API (uvicorn) and UI (vite) run on the host.
#   - AI_PROVIDER defaults to `claude_cli` so no ANTHROPIC_API_KEY is required —
#     it uses the logged-in `claude` CLI on your PATH. The Docker image can't
#     run claude_cli (no `claude` binary in it; see PT-7), which is why the API
#     runs on the host for this path.
#
# For the fully-documented all-Docker `anthropic` path instead, set a real
# ANTHROPIC_API_KEY in .env and run `docker-compose up` (per the README).
#
# Usage:
#   docs/playtest/playtest-stack.sh up       # start everything, wait until healthy
#   docs/playtest/playtest-stack.sh down     # stop API + UI and the datastores
#   docs/playtest/playtest-stack.sh status   # show health of each piece
#   docs/playtest/playtest-stack.sh logs     # tail the API + UI logs
#
# Env overrides: AI_PROVIDER, DM_TOKEN, API_PORT, UI_PORT.
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUN_DIR="$REPO_ROOT/.playtest"        # pidfiles + logs (gitignored)
API_PORT="${API_PORT:-8000}"
UI_PORT="${UI_PORT:-5173}"
AI_PROVIDER="${AI_PROVIDER:-claude_cli}"
DM_TOKEN="${DM_TOKEN:-dev-dm-token}"

API_PIDFILE="$RUN_DIR/api.pid"
UI_PIDFILE="$RUN_DIR/ui.pid"
API_LOG="$RUN_DIR/api.log"
UI_LOG="$RUN_DIR/ui.log"

c_info=$'\033[1;36m'; c_ok=$'\033[1;32m'; c_warn=$'\033[1;33m'; c_err=$'\033[1;31m'; c_off=$'\033[0m'
log()  { printf '%s[playtest]%s %s\n' "$c_info" "$c_off" "$*"; }
ok()   { printf '%s[playtest]%s %s\n' "$c_ok"   "$c_off" "$*"; }
warn() { printf '%s[playtest]%s %s\n' "$c_warn" "$c_off" "$*"; }
die()  { printf '%s[playtest]%s %s\n' "$c_err"  "$c_off" "$*" >&2; exit 1; }

# --- tool detection -----------------------------------------------------------

# Print the path to a Python >=3.11 interpreter (the API targets py311+).
find_python() {
  local p
  for p in python3.13 python3.12 python3.11 python3; do
    if command -v "$p" >/dev/null 2>&1; then
      if "$p" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3,11) else 1)'; then
        command -v "$p"; return 0
      fi
    fi
  done
  return 1
}

# Print the directory containing a node >=18 binary (vite needs >=18; this repo
# has historically had an ancient nvm default of v11 on PATH — skip it).
find_node_bin() {
  local n major best d
  if command -v node >/dev/null 2>&1; then
    major="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)"
    [ "${major:-0}" -ge 18 ] && { dirname "$(command -v node)"; return 0; }
  fi
  for n in /opt/homebrew/bin/node /usr/local/bin/node; do
    if [ -x "$n" ] && [ "$("$n" -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)" -ge 18 ]; then
      dirname "$n"; return 0
    fi
  done
  if [ -d "$HOME/.nvm/versions/node" ]; then
    best="$(ls "$HOME/.nvm/versions/node" 2>/dev/null | sed 's/^v//' \
            | sort -t. -k1,1n -k2,2n | awk -F. '$1>=18' | tail -1)"
    [ -n "$best" ] && { echo "$HOME/.nvm/versions/node/v$best/bin"; return 0; }
  fi
  return 1
}

# Kill whatever is listening on a TCP port (macOS + Linux).
kill_port() {
  local port="$1" pids
  pids="$(lsof -ti "tcp:$port" 2>/dev/null || true)"
  [ -n "$pids" ] && kill $pids 2>/dev/null || true
}

# Kill a process recorded in a pidfile, plus any children, then remove the file.
kill_pidfile() {
  local file="$1" pid
  [ -f "$file" ] || return 0
  pid="$(cat "$file" 2>/dev/null || true)"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    pkill -P "$pid" 2>/dev/null || true
    kill "$pid" 2>/dev/null || true
  fi
  rm -f "$file"
}

wait_for() { # wait_for <url> <label> <timeout-secs>
  local url="$1" label="$2" timeout="${3:-60}" i
  for ((i = 0; i < timeout; i++)); do
    if curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then ok "$label is up"; return 0; fi
    sleep 1
  done
  return 1
}

# --- commands -----------------------------------------------------------------

cmd_up() {
  mkdir -p "$RUN_DIR"
  command -v docker >/dev/null 2>&1 || die "docker not found — start Docker Desktop first."
  docker info >/dev/null 2>&1 || die "Docker daemon is down — start Docker Desktop, then retry."

  # .env (created once; never overwritten so your edits survive).
  if [ ! -f "$REPO_ROOT/.env" ]; then
    log "writing .env (AI_PROVIDER=$AI_PROVIDER)"
    cat > "$REPO_ROOT/.env" <<EOF
AI_PROVIDER=$AI_PROVIDER
ANTHROPIC_API_KEY=unused-with-claude-cli
ORCHESTRATOR_MODEL=claude-sonnet-4-6
GENERATION_MODEL=claude-haiku-4-5-20251001
DATABASE_URL=postgresql+asyncpg://dmuser:dmpass@localhost:5432/dmdb
REDIS_URL=redis://localhost:6379
SECRET_KEY=change-me-in-production
FRONTEND_URL=http://localhost:$UI_PORT
DM_TOKEN=$DM_TOKEN
EOF
  fi
  if [ "$AI_PROVIDER" = "claude_cli" ] && ! command -v claude >/dev/null 2>&1; then
    warn "AI_PROVIDER=claude_cli but no 'claude' on PATH — AI turns will fail."
  fi

  log "starting datastores (postgres, redis)…"
  ( cd "$REPO_ROOT" && docker compose up -d postgres redis >/dev/null )
  for ((i = 0; i < 40; i++)); do
    if docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T postgres \
         pg_isready -U dmuser -d dmdb >/dev/null 2>&1; then break; fi
    sleep 1
  done

  # API venv (created + populated once).
  local py
  py="$(find_python)" || die "need Python >=3.11 on PATH for the API venv."
  if [ ! -x "$REPO_ROOT/dm-api/.venv/bin/python" ]; then
    log "creating API venv with $py …"
    "$py" -m venv "$REPO_ROOT/dm-api/.venv"
    log "installing game-engine + dm-api (first run, ~1-2 min)…"
    ( cd "$REPO_ROOT/dm-api" && . .venv/bin/activate \
      && pip install -q --upgrade pip \
      && pip install -q -e ../game-engine \
      && pip install -q -e . )
  fi

  log "running migrations…"
  ( cd "$REPO_ROOT/dm-api" && . .venv/bin/activate && set -a && . "$REPO_ROOT/.env" && set +a \
    && alembic upgrade head >/dev/null )

  # API (no --reload: single process so teardown is clean).
  kill_port "$API_PORT"
  log "starting API on :$API_PORT …"
  ( cd "$REPO_ROOT/dm-api" && . .venv/bin/activate && set -a && . "$REPO_ROOT/.env" && set +a \
    && nohup uvicorn dm_api.main:app --host 0.0.0.0 --port "$API_PORT" >"$API_LOG" 2>&1 &
    echo $! > "$API_PIDFILE" )
  wait_for "http://localhost:$API_PORT/health" "API" 40 \
    || die "API failed to come up — see $API_LOG"

  # UI deps (use a real node; install only when node_modules is missing).
  local node_bin
  node_bin="$(find_node_bin)" || die "need Node >=18 on PATH for the UI (vite)."
  if [ ! -d "$REPO_ROOT/dm-ui/node_modules" ]; then
    log "installing UI deps with $(PATH="$node_bin:$PATH" node -v) …"
    ( cd "$REPO_ROOT/dm-ui" && PATH="$node_bin:$PATH" npm install --silent )
  fi

  # UI (run the vite binary directly, not via npm, so the pid we save is the
  # process that actually binds the port — clean teardown).
  kill_port "$UI_PORT"
  log "starting UI on :$UI_PORT …"
  ( cd "$REPO_ROOT/dm-ui" \
    && PATH="$node_bin:$PATH" VITE_API_URL="http://localhost:$API_PORT" \
       nohup ./node_modules/.bin/vite --host --port "$UI_PORT" >"$UI_LOG" 2>&1 &
    echo $! > "$UI_PIDFILE" )
  wait_for "http://localhost:$UI_PORT" "UI" 40 || die "UI failed to come up — see $UI_LOG"

  echo
  ok "stack is up:"
  echo "    UI:      http://localhost:$UI_PORT"
  echo "    API:     http://localhost:$API_PORT  ($(curl -fsS "http://localhost:$API_PORT/health" 2>/dev/null))"
  echo "    DM token: $DM_TOKEN"
  echo "    logs:    $API_LOG , $UI_LOG"
  echo "    down:    $0 down"
}

cmd_down() {
  log "stopping UI + API…"
  kill_pidfile "$UI_PIDFILE"
  kill_pidfile "$API_PIDFILE"
  # Safety net for stacks started outside this script (e.g. earlier manual runs).
  kill_port "$UI_PORT"
  kill_port "$API_PORT"
  pkill -f "uvicorn dm_api.main:app" 2>/dev/null || true
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    log "stopping datastores…"
    ( cd "$REPO_ROOT" && docker compose down >/dev/null 2>&1 || true )
  fi
  ok "stack is down. (Postgres data persists in the docker volume; add '--wipe' to remove it.)"
  if [ "${1:-}" = "--wipe" ]; then
    ( cd "$REPO_ROOT" && docker compose down -v >/dev/null 2>&1 || true )
    ok "datastore volume removed."
  fi
}

cmd_status() {
  local api ui
  if curl -fsS --max-time 2 "http://localhost:$API_PORT/health" >/dev/null 2>&1; then
    api="$(curl -fsS "http://localhost:$API_PORT/health")"; ok "API  :$API_PORT  $api"
  else warn "API  :$API_PORT  down"; fi
  if curl -fsS --max-time 2 "http://localhost:$UI_PORT" >/dev/null 2>&1; then
    ok "UI   :$UI_PORT  up"
  else warn "UI   :$UI_PORT  down"; fi
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    ( cd "$REPO_ROOT" && docker compose ps --services --filter status=running 2>/dev/null \
      | sed 's/^/    docker: /' )
  fi
}

cmd_logs() {
  [ -f "$API_LOG" ] || die "no logs yet — run '$0 up' first."
  tail -n 40 -f "$API_LOG" "$UI_LOG"
}

case "${1:-}" in
  up)     cmd_up ;;
  down)   shift || true; cmd_down "${1:-}" ;;
  status) cmd_status ;;
  logs)   cmd_logs ;;
  *) echo "usage: $0 {up|down [--wipe]|status|logs}" >&2; exit 2 ;;
esac
