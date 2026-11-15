#!/usr/bin/env bash
# Прогнать backend, frontend, NASA data pipeline и simulation тесты.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== Backend Brain tests =="
(cd backend && .venv/bin/python -m pytest -q)

echo "== Frontend tests =="
(cd frontend && npm test)

echo "== Data pipeline tests =="
PYTHONPATH="$ROOT" backend/.venv/bin/python -m pytest data_pipeline/tests -q

echo "== Simulation tests =="
PYTHONPATH="$ROOT" backend/.venv/bin/python -m pytest tests/test_simulation_engine_full.py tests/test_simulation_engine.py -q
