#!/usr/bin/env bash
# setup.sh — Get a fresh clone of Kiku ready to run. One command, no manual steps.
#
# Installs the exact pinned versions from uv.lock and frontend/package-lock.json,
# so this machine ends up with the same environment as every other one.

set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
BOLD="\033[1m"
DIM="\033[2m"
RST="\033[0m"

cd "$DIR"

# --- Preflight ---

if ! command -v uv >/dev/null 2>&1; then
  echo "Kiku's Python environment is managed by uv, and it isn't installed yet."
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
  echo "  (or: pipx install uv)"
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm isn't installed — the frontend needs it. Install Node 20 or newer."
  exit 1
fi

# --- Python ---
# Anything passed to this script goes through to `uv sync`, so audio analysis is
#   ./scripts/setup.sh --extra analysis
# Note that `uv sync` makes .venv match exactly what you ask for: run it without
# --extra analysis and essentia/librosa are removed again.

echo -e "${BOLD}Setting up Kiku…${RST}"
echo -e "  ${DIM}python  → .venv from uv.lock${RST}"
uv sync --extra dev "$@"

# --- Frontend ---

echo -e "  ${DIM}web     → frontend/node_modules from package-lock.json${RST}"
npm --prefix frontend ci --silent

# --- Schema ---
# The database builds itself from the migration chain on first use, so there is
# nothing to do here. See docs/notes/OBS-003.

echo ""
echo -e "${BOLD}Ready.${RST}"
echo "  ./dev.sh              start the backend and frontend together"
echo "  uv run pytest         run the backend suite"
echo "  uv run kiku --help    see what Kiku can do"
echo ""
echo -e "${DIM}Audio analysis (essentia + librosa) is a separate extra — it's big, and"
echo -e "you only need it to run \`kiku analyze\`:  ./scripts/setup.sh --extra analysis${RST}"
