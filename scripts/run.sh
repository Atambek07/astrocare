#!/usr/bin/env bash
# Запуск unified AstroCare: unified backend + simulation + WebSocket + frontend.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PORT="${ASTROCARE_BACKEND_PORT:-8765}"
FRONTEND_PORT="${ASTROCARE_FRONTEND_PORT:-3000}"
SCENARIOS=()

for scenario in "$@"; do
  SCENARIOS+=(--scenario "$scenario")
done

cd "$ROOT"
PYTHONPATH="backend/src:$ROOT" ASTRO_DOCTOR_OFFLINE="${ASTRO_DOCTOR_OFFLINE:-1}" \
  backend/.venv/bin/python -m astro_brain.astrocare_service \
  --port "$BACKEND_PORT" --ws-port "${ASTROCARE_WS_PORT:-8787}" "${SCENARIOS[@]}" &
BACKEND_PID=$!

cd frontend
if [ -d node_modules ]; then
  NEXT_PUBLIC_BRAIN_WS_URL="ws://localhost:${ASTROCARE_WS_PORT:-8787}" \
  NEXT_PUBLIC_BACKEND_HTTP_URL="http://localhost:${BACKEND_PORT}" npm run dev -- --port "$FRONTEND_PORT" &
FRONTEND_PID=$!
else
  echo "frontend/node_modules is missing; run scripts/setup.sh first." >&2
  kill "$BACKEND_PID" 2>/dev/null || true
  exit 1
fi

cleanup() {
  kill "$FRONTEND_PID" "$BACKEND_PID" 2>/dev/null || true
  wait "$FRONTEND_PID" "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
wait
