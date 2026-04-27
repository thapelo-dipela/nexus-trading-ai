#!/usr/bin/env bash
set -euo pipefail

# stop.sh — stop dashboard and main background processes

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$ROOT_DIR/.dashboard_pid" ]; then
  DASH_PID=$(cat "$ROOT_DIR/.dashboard_pid")
  echo "Stopping dashboard (PID=$DASH_PID)" || true
  kill "$DASH_PID" 2>/dev/null || true
  rm -f "$ROOT_DIR/.dashboard_pid"
fi

if [ -f "$ROOT_DIR/.main_pid" ]; then
  MAIN_PID=$(cat "$ROOT_DIR/.main_pid")
  echo "Stopping main (PID=$MAIN_PID)" || true
  kill "$MAIN_PID" 2>/dev/null || true
  rm -f "$ROOT_DIR/.main_pid"
fi

echo "Stopped. Check server.log and main.log for details."
