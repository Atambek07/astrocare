#!/usr/bin/env bash
# Полный контроль качества AstroCare с детерминированным порядком и JSON-сводкой.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p reports

: > reports/qa_summary.jsonl
status=0

run_check() {
  local name="$1"
  local logfile="reports/${name}.log"
  shift
  local result=0
  "$@" >"$logfile" 2>&1 || result=$?
  if [ "$result" -eq 0 ]; then
    printf '{"check":"%s","status":"PASSED"}\n' "$name" >> reports/qa_summary.jsonl
  else
    printf '{"check":"%s","status":"FAILED","exit_code":%s}\n' "$name" "$result" >> reports/qa_summary.jsonl
    status=1
  fi
  printf '%s' "$result"
}

backend_result=$(run_check "backend-tests" bash scripts/test_backend.sh)
frontend_result=$(run_check "frontend-tests" bash scripts/test_frontend.sh)
data_result=$(run_check "data-pipeline-tests" bash scripts/test_data_pipeline.sh)
simulation_result=$(run_check "simulation-tests" bash scripts/test_simulation.sh)
integration_result=$(run_check "integration-contracts" bash scripts/test_integration.sh)
e2e_result=$(run_check "end-to-end-service" bash scripts/test_e2e.sh)
build_result=$(run_check "frontend-build" bash scripts/test_frontend_build.sh)
schema_result=$(run_check "shared-schema-check" env PYTHONPATH="$ROOT" backend/.venv/bin/python shared/generate_contracts_schema.py --check)
docs_result=$(run_check "documentation-links" bash scripts/check_docs.sh)

count_pytest() {
  local file="$1"
  grep -Eo '[0-9]+ passed' "$file" 2>/dev/null | tail -1 | grep -Eo '[0-9]+' || echo 0
}

count_frontend() {
  local file="$1"
  grep -Eo 'Tests[^0-9]+[0-9]+ passed' "$file" 2>/dev/null | tail -1 | grep -Eo '[0-9]+' | tail -1 || echo 0
}

backend_passed=$(count_pytest reports/backend-tests.log)
data_passed=$(count_pytest reports/data-pipeline-tests.log)
simulation_passed=$(count_pytest reports/simulation-tests.log)
integration_passed=$(count_pytest reports/integration-contracts.log)
frontend_passed=$(count_frontend reports/frontend-tests.log)

if [ "$backend_result" -ne 0 ] || [ "$frontend_result" -ne 0 ] || [ "$data_result" -ne 0 ] || [ "$simulation_result" -ne 0 ] || [ "$integration_result" -ne 0 ] || [ "$e2e_result" -ne 0 ] || [ "$build_result" -ne 0 ] || [ "$schema_result" -ne 0 ] || [ "$docs_result" -ne 0 ]; then
  readiness="NOT_READY"
else
  readiness="READY_WITH_LIMITATIONS"
fi

commit="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
cat > reports/qa_summary.json <<EOF
{
  "timestamp": "$timestamp",
  "commit": "$commit",
  "environment": {
    "python": "$(backend/.venv/bin/python --version | cut -d' ' -f2)",
    "node": "$(node --version)",
    "doctor_mode": "offline_deterministic"
  },
  "commands": [
    "scripts/test_backend.sh",
    "scripts/test_frontend.sh",
    "scripts/test_data_pipeline.sh",
    "scripts/test_simulation.sh",
    "scripts/test_integration.sh",
    "scripts/test_e2e.sh",
    "scripts/test_frontend_build.sh",
    "shared/generate_contracts_schema.py --check",
    "scripts/check_docs.sh"
  ],
  "test_counts": {
    "backend_passed": $backend_passed,
    "frontend_passed": $frontend_passed,
    "data_pipeline_passed": $data_passed,
    "simulation_passed": $simulation_passed,
    "integration_passed": $integration_passed
  },
  "checks": {
    "backend": $([ "$backend_result" -eq 0 ] && echo true || echo false),
    "frontend": $([ "$frontend_result" -eq 0 ] && echo true || echo false),
    "data_pipeline": $([ "$data_result" -eq 0 ] && echo true || echo false),
    "simulation": $([ "$simulation_result" -eq 0 ] && echo true || echo false),
    "integration": $([ "$integration_result" -eq 0 ] && echo true || echo false),
    "end_to_end_service": $([ "$e2e_result" -eq 0 ] && echo true || echo false),
    "frontend_build": $([ "$build_result" -eq 0 ] && echo true || echo false),
    "shared_schema": $([ "$schema_result" -eq 0 ] && echo true || echo false),
    "documentation_links": $([ "$docs_result" -eq 0 ] && echo true || echo false)
  },
  "failure_count": $status,
  "skipped_count": 0,
  "blocked_checks": [],
  "build_status": "$([ "$build_result" -eq 0 ] && echo PASSED || echo FAILED)",
  "readiness_status": "$readiness"
}
EOF

printf 'QA complete: %s\n' "$readiness"
exit "$status"
