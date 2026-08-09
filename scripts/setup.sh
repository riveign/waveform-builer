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
# `uv sync` makes .venv match exactly what is asked for, so the default has to be
# the full working environment — otherwise re-running this script would silently
# strip essentia and librosa off a machine that had them. Pass --lean for the
# smaller install (CI, or frontend-only work), and anything else straight to uv.

EXTRAS=(--extra dev --extra analysis)
if [[ "${1:-}" == "--lean" ]]; then
  EXTRAS=(--extra dev)
  shift
fi

echo -e "${BOLD}Setting up Kiku…${RST}"
echo -e "  ${DIM}python  → .venv from uv.lock${RST}"
uv sync "${EXTRAS[@]}" "$@"

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
echo -e "${DIM}Skip the audio-analysis stack (essentia, librosa, tensorflow — big, and only"
echo -e "needed for \`kiku analyze\`) with:  ./scripts/setup.sh --lean${RST}"
