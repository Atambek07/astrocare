#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHONPATH="$ROOT" backend/.venv/bin/python -m pytest tests/test_simulation_engine_full.py tests/test_simulation_engine.py tests/test_simulation_numerics.py -q
