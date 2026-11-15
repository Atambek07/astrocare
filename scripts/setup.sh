#!/usr/bin/env bash
# Единая установка AstroCare: backend, frontend и проверка Python-зависимостей.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -d backend/.venv ]; then
  python3 -m venv backend/.venv
fi
backend/.venv/bin/pip install -U pip >/dev/null
backend/.venv/bin/pip install -e "backend[dev]"

if [ ! -d frontend/node_modules ]; then
  (cd frontend && npm install --no-audit --no-fund)
fi

echo "AstroCare setup complete."
echo "Backend venv: backend/.venv"
echo "Frontend deps: frontend/node_modules"
