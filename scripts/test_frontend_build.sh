#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/frontend"
NEXT_DIST_DIR="${NEXT_DIST_DIR:-.next-qa}" npm run build
