#!/usr/bin/env bash
# Проверка обязательной документации и относительных ссылок.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

required=(
  docs/INDEX.md
  docs/QA_BASELINE_REPORT.md
  docs/BUG_REGISTER.md
  docs/API_ENDPOINT_AUDIT.md
  docs/NASA_DATA_VALIDATION_REPORT.md
  docs/SIMULATION_VALIDATION_REPORT.md
  docs/CONTRACT_VALIDATION_REPORT.md
  docs/ERROR_HANDLING_AND_OBSERVABILITY.md
  docs/PERFORMANCE_REPORT.md
  docs/QA_FINAL_REPORT.md
)
for file in "${required[@]}"; do
  test -f "$file" || { echo "missing required document: $file"; exit 1; }
done

PYTHONPATH="$ROOT" backend/.venv/bin/python - <<'PY'
import re
from pathlib import Path

root = Path('.')
files = [Path('README.md'), *sorted((root / 'docs').glob('*.md'))]
pattern = re.compile(r'\]\(([^)]+)\)')
broken = []

for path in files:
    text = path.read_text(encoding='utf-8')
    for raw in pattern.findall(text):
        target = raw.split('#', 1)[0].strip()
        if not target or target.startswith(('http://', 'https://', 'mailto:')):
            continue
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            broken.append(f'{path}: {target}')

if broken:
    print('\n'.join(f'broken documentation link: {item}' for item in broken))
    raise SystemExit(1)

print(f'Checked {len(files)} documentation files; all local links resolve.')
PY
