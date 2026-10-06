#!/usr/bin/env bash
# dev.sh — Start Kiku's backend and frontend together.
# Ctrl+C stops both. That's it.

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
API_COLOR="\033[0;36m"  # cyan
WEB_COLOR="\033[0;35m"  # magenta
RST="\033[0m"
BOLD="\033[1m"

# Job control gives each background job its own process group, so cleanup can
# signal the whole tree (kiku + reload workers, npm + vite), not just the wrapper.
set -m

pids=()
stopping=0

cleanup() {
  [[ $stopping -eq 1 ]] && return
  stopping=1
  trap '' INT TERM
  [[ ${#pids[@]} -eq 0 ]] && return
  echo ""
  echo -e "${BOLD}Shutting down...${RST}"
  for pid in "${pids[@]}"; do
    kill -TERM -- "-$pid" 2>/dev/null || true
  done
  # Give them a moment to exit, then stop whatever ignored the polite ask.
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    alive=0
    for pid in "${pids[@]}"; do
      kill -0 -- "-$pid" 2>/dev/null && alive=1
    done
    [[ $alive -eq 0 ]] && break
    sleep 0.5
  done
  for pid in "${pids[@]}"; do
    kill -KILL -- "-$pid" 2>/dev/null || true
  done
  echo "See you next session."
}
trap cleanup EXIT INT TERM

port_in_use() {
  ss -ltn "( sport = :$1 )" 2>/dev/null | grep -q LISTEN
}

# --- Preflight checks ---

if [[ ! -d "$DIR/.venv" ]]; then
  echo "No .venv/ found. Set one up first:"
  echo "  ./scripts/setup.sh"
  exit 1
fi

if [[ ! -d "$DIR/frontend/node_modules" ]]; then
  echo "frontend/node_modules/ is missing. Run this first:"
  echo "  ./scripts/setup.sh"
  exit 1
fi

for entry in "8000:backend" "5173:frontend"; do
  port="${entry%%:*}"
  if port_in_use "$port"; then
    echo "Port $port is already taken — an earlier $(echo "${entry##*:}") is probably still running."
    echo "  See what holds it:  ss -ltnp 'sport = :$port'"
    exit 1
  fi
done

# --- Start backend ---

echo -e "${BOLD}Starting Kiku...${RST}"
echo -e "  ${API_COLOR}[api]${RST}  Backend  → http://localhost:8000"
echo -e "  ${WEB_COLOR}[web]${RST}  Frontend → http://localhost:5173"
echo ""

(
  source "$DIR/.venv/bin/activate"
  kiku serve --reload 2>&1 | while IFS= read -r line; do
    echo -e "${API_COLOR}[api]${RST} $line"
  done
) </dev/null &
pids+=($!)

# Give the API a moment to bind the port before Vite starts proxying.
sleep 1

# --- Start frontend ---

(
  cd "$DIR/frontend"
  npm run dev -- --strictPort 2>&1 | while IFS= read -r line; do
    echo -e "${WEB_COLOR}[web]${RST} $line"
  done
) </dev/null &
pids+=($!)

echo -e "${BOLD}Both servers listening. Ctrl+C to stop.${RST}"
echo ""

# Wait for either process to exit.
wait -n "${pids[@]}" 2>/dev/null || true
