#!/usr/bin/env bash
# Демонстрация AstroCare: NASA данные, симуляция, backend и frontend.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "AstroCare demo"
echo "1. NASA OSDR evidence: $ROOT/data/manifests/bundle_manifest.json"
python3 - <<'PY'
import json
from pathlib import Path
path = Path('data/manifests/bundle_manifest.json')
if not path.exists():
    print('NASA manifest unavailable; run data_pipeline/build_offline_bundle.py first.')
else:
    payload = json.loads(path.read_text())
    print(f"bundle_id={payload.get('bundle_id')} fallback={payload.get('fallback_status')}")
    print('counts=', payload.get('counts', {}))
PY

echo "2. Starting unified AstroCare backend + simulation + frontend."
exec scripts/run.sh HYPERCAPNIC_CABIN
