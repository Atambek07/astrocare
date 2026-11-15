# Error Handling and Observability

**Status:** implemented for current local service architecture.

---

## 1. Principles

1. Invalid data is rejected; it is never silently repaired.
2. Missing data remains missing.
3. Optional AI failure degrades to deterministic fallback.
4. Runtime and network failures do not corrupt simulation state.
5. User-facing errors are safe and actionable.
6. Internal diagnostics are logged without exposing filesystem paths or stack traces to end users.

---

## 2. Backend behavior

| Situation | Behavior |
| --- | --- |
| Malformed JSON | HTTP 400, `{"error":"invalid JSON body: ..."}`. |
| Input contract violation | HTTP 400 with field-specific message. |
| Unknown route | HTTP 404 JSON with path. |
| Unknown astronaut/report | HTTP 404 JSON. |
| Unexpected exception | HTTP 500 with exception class only. |
| Ollama unavailable/slow | Doctor Layer uses rule-based fallback. |
| WebSocket client disconnect | Client removed; other clients continue. |

The dashboard logs only when verbose mode is enabled. The simulation loop logs skipped Brain samples to stderr; it does not crash the service.

---

## 3. Simulation behavior

| Situation | Behavior |
| --- | --- |
| Unknown scenario | `KeyError`, surfaced as HTTP 400. |
| Unknown countermeasure | `ValueError`, surfaced as HTTP 400. |
| Invalid speed | `ValueError`, surfaced as HTTP 400. |
| Negative mission time | `ValueError`; mission time never decreases. |
| State reaches validation bound | Value is clamped; state remains finite. |
| Simulation runtime error | Loop logs exception and stops without taking down HTTP service. |

Events are stored for mission lifecycle, scenario lifecycle, daily sleep, countermeasures and What-If completion. Each event includes engine version, model version, random seed and source type.

---

## 4. Frontend behavior

| Situation | Behavior |
| --- | --- |
| WebSocket unavailable | Explicit `MOCK` mode and connection state. |
| WebSocket reconnecting | `reconnecting` state; mock does not masquerade as live. |
| Simulation service unavailable | Simulation view shows error banner; polling continues. |
| Simulation command fails | Error banner with backend detail or HTTP status. |
| NASA static artifact absent | Data Sources shows “NASA data manifests are not available.” |
| Malformed WebSocket tick | zod parser rejects and logs a warning; UI does not crash. |
| 3D/WebGL failure | 2D twin fallback. |

---

## 5. Data pipeline behavior

| Situation | Behavior |
| --- | --- |
| Network unavailable | Cache fallback where available; otherwise explicit unavailable. |
| Checksum mismatch | Download rejected. |
| Restricted file | Skipped and recorded. |
| Unknown unit | Value retained; normalized unit null; status warning. |
| Missing value | Remains null with `MISSING` status. |
| Relative timepoint | Preserved; no absolute timestamp is fabricated. |

---

## 6. Logs and artifacts

| Artifact | Location/purpose |
| --- | --- |
| QA summary | `reports/qa_summary.json` and JSONL check results. |
| NASA bundle manifest | `data/manifests/bundle_manifest.json`. |
| NASA download manifest | `data/manifests/download_manifest.json`. |
| NASA quality report | `data/manifests/data_quality_report.json`. |
| Simulation events | Controller event log; included in checkpoints. |
| Simulation telemetry export | `simulation_exports/`. |

---

## 7. Recommended production hardening

1. Add request IDs to all backend responses.
2. Replace wildcard CORS with an allow-list.
3. Add structured JSON logging with severity and component fields.
4. Add metrics for ingestion errors, Brain processing latency and WebSocket clients.
5. Add explicit authentication before non-local deployment.
6. Add graceful shutdown and liveness/readiness endpoints to the unified service.
