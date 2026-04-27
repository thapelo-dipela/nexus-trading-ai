#!/usr/bin/env bash
set -euo pipefail

# run.sh — start dashboard_server.py and main.py (dry-run) in background using .venv
# Usage: ./run.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT_DIR/.venv"

if [ ! -d "$VENV" ]; then
  echo "Virtualenv not found at $VENV — create one first: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

source "$VENV/bin/activate"

echo "Starting dashboard_server.py (logs -> server.log)"
nohup "$VENV/bin/python" "$ROOT_DIR/dashboard_server.py" > "$ROOT_DIR/server.log" 2>&1 &
echo $! > "$ROOT_DIR/.dashboard_pid"

echo "Starting main.py (dry-run) (logs -> main.log)"
nohup "$VENV/bin/python" "$ROOT_DIR/main.py" --dry-run > "$ROOT_DIR/main.log" 2>&1 &
echo $! > "$ROOT_DIR/.main_pid"

echo "Started. To follow logs: tail -f server.log main.log"
