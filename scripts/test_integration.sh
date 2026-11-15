#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHONPATH="$ROOT" backend/.venv/bin/python -m pytest backend/tests/test_unified_contracts.py backend/tests/test_astrocare_service.py -q
