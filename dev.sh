#!/usr/bin/env bash
# dev.sh — Start Kiku's backend and frontend together.
# Ctrl+C stops both. That's it.

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
API_COLOR="\033[0;36m"  # cyan
WEB_COLOR="\033[0;35m"  # magenta
RST="\033[0m"
BOLD="\033[1m"

pids=()

cleanup() {
  echo ""
  echo -e "${BOLD}Shutting down...${RST}"
  for pid in "${pids[@]}"; do
    kill "$pid" 2>/dev/null && wait "$pid" 2>/dev/null
  done
  echo "See you next session."
}
trap cleanup EXIT INT TERM

# --- Preflight checks ---

if [[ ! -d "$DIR/.venv" ]]; then
  echo "No .venv/ found. Set one up first:"
  echo "  python -m venv .venv && .venv/bin/python -m pip install -e '.[api]'"
  exit 1
fi

if [[ ! -d "$DIR/frontend/node_modules" ]]; then
  echo "frontend/node_modules/ is missing. Run this first:"
  echo "  cd frontend && npm install"
  exit 1
fi

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
) &
pids+=($!)

# Give the API a moment to bind the port before Vite starts proxying.
sleep 1

# --- Start frontend ---

(
  cd "$DIR/frontend"
  npm run dev 2>&1 | while IFS= read -r line; do
    echo -e "${WEB_COLOR}[web]${RST} $line"
  done
) &
pids+=($!)

echo -e "${BOLD}Both servers listening. Ctrl+C to stop.${RST}"
echo ""

# Wait for either process to exit.
wait -n "${pids[@]}" 2>/dev/null || true
