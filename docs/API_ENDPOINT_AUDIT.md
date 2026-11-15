# AstroCare API Endpoint Audit

**Date:** 2026-11-15  
**Verified backend port:** `8765`  
**Frontend development port:** `3000`  
**Doctor mode during live checks:** offline rule-based fallback.

---

## 1. Frontend runtime requests

### Simulation and unified service

| Method | Frontend target | Backend route | Purpose | Expected status | Verified status | Result |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `NEXT_PUBLIC_BACKEND_HTTP_URL + /simulation/status` | `/simulation/status` | Return simulation, astronaut and environment state. | 200 | 200 | PASS |
| POST | `NEXT_PUBLIC_BACKEND_HTTP_URL + /simulation/control` | `/simulation/control` | Start, pause, resume, stop, reset or set speed. | 200 valid / 400 invalid | 200 valid / 400 invalid action | PASS |
| POST | `NEXT_PUBLIC_BACKEND_HTTP_URL + /simulation/scenario` | `/simulation/scenario` | Start or terminate a scenario. | 200 valid / 400 invalid | 200 valid / 400 unknown | PASS |
| POST | `NEXT_PUBLIC_BACKEND_HTTP_URL + /simulation/countermeasure` | `/simulation/countermeasure` | Apply a supported countermeasure. | 200 valid / 400 invalid | 200 valid / 400 unknown | PASS |
| POST | `NEXT_PUBLIC_BACKEND_HTTP_URL + /simulation/what-if` | `/simulation/what-if` | Run an isolated experiment. | 200 valid / 400 invalid | 200 valid | PASS |

### Static frontend data

| Method | Path | Purpose | Expected status | Verified status | Result |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/data/manifests/bundle_manifest.json` | NASA bundle and counts. | 200 | 200 | PASS |
| GET | `/data/manifests/data_quality_report.json` | NASA processing quality. | 200 | 200 | PASS |
| GET | `/data/reference/study_catalog.json` | OSDR study catalog and rejections. | 200 | 200 | PASS |
| GET | `/models/astronaut_models.json` | Available and optional 3D assets. | 200 | 200 | PASS |
| GET | `/models/astronaut_anatomy.glb` | Required anatomy model. | 200 | 200 | PASS |
| GET | `/models/astronaut_body.fbx` | Required body mesh. | 200 | 200 | PASS |
| GET | `/models/astronaut_twin.glb` | Optional custom twin model. | 404 is intentional only if absent | Request removed when manifest marks it absent | PASS |

### WebSocket

| Transport | URL | Payload | Verified |
| --- | --- | --- | --- |
| WebSocket | `NEXT_PUBLIC_BRAIN_WS_URL` | `BrainTick` for one astronaut update | PASS |

---

## 2. Backend route inventory

All pre-existing routes were exercised against the unified service. The newer local-AI routes are documented with their verification method below.

| Method | Path | Purpose | Success | Errors | Verified |
| --- | --- | --- | --- | --- | --- |
| POST | `/ingest` | Validate and process one Brain input sample. | 200 + Brain output | 400 invalid JSON/contract; 500 unexpected | Existing backend tests |
| GET | `/state` | Latest Brain output; supports `astronaut_id`. | 200 output or no-data marker | None | Live check |
| GET | `/state/all` | Latest output for every astronaut. | 200 mapping | None | Live check |
| GET | `/history` | Last 50 outputs; supports `astronaut_id`. | 200 list | None | Live check |
| GET | `/` | Plain-text operational snapshot. | 200 text | None | Existing backend tests |
| GET | `/models` | List selectable local Ollama models. | 200 with availability/models/default | 200 with empty list when Ollama is unavailable | Manual browser/API check; no dedicated automated endpoint test |
| POST | `/ask` | Doctor Layer question using latest context; optional `model`. | 200 answer | 400 invalid/missing fields; 400 invalid model name; 404 no data | Existing backend tests; explicit model and invalid-model paths manually checked |
| GET | `/log` | Mission episodes; supports `astronaut_id`. | 200 episodes | None | Live check |
| GET | `/report` | Mission report; supports `format=text`. | 200 report | 400 missing astronaut; 404 no data | Live check |
| GET | `/simulation/status` | Simulation and environment status. | 200 | 503 if runtime absent | Live check |
| GET | `/data/status` | NASA bundle/provenance summary. | 200 | 200 with `manifest_available=false` | Live check |
| POST | `/simulation/control` | Simulation lifecycle/speed. | 200 | 400 invalid action/value | Existing test route contract |
| POST | `/simulation/scenario` | Scenario lifecycle. | 200 | 400 unknown/invalid | Live check |
| POST | `/simulation/countermeasure` | Apply countermeasure. | 200 | 400 unknown/invalid | Live check |
| POST | `/simulation/what-if` | Isolated What-If run. | 200 | 400 invalid | Live check |
| OPTIONS | any | CORS preflight. | 204 | None | Existing backend tests |
| Any | unknown path | Intentional JSON 404. | — | 404 | Live check |

---

## 3. Frontend route inventory

| Route | Purpose | Verified |
| --- | --- | --- |
| `/` | Main AstroCare Digital Twin application. | 200 |
| `/crew` | Crew overview route. | 200 |
| `/analytics`, `/assistant`, `/training`, `/history`, `/radar`, `/routine`, `/learn`, `/data`, `/simulation` | Direct routes to client-side product views. | 200 |
| Any unknown path | Intentional Next.js 404. | 404 |

The primary application uses client-side view state. Known views are also exposed through the `/[view]` route so that direct navigation and refresh work. Unknown view identifiers intentionally return 404.

---

## 4. HTTP status contract

| Status | Use |
| --- | --- |
| 200 | Successful query or accepted command. |
| 204 | CORS preflight. |
| 400 | Malformed JSON, invalid action, unknown scenario/countermeasure, contract violation, invalid local-AI model name. |
| 404 | Intentionally absent route or no report for an astronaut. |
| 500 | Unexpected backend exception; response contains only an error class. |

---

## 5. Cross-origin behavior

The unified service sends:

```http
Access-Control-Allow-Origin: *
Access-Control-Allow-Headers: Content-Type
Access-Control-Allow-Methods: GET, POST, OPTIONS
```

This is appropriate for the local demonstration but should be narrowed before any non-local deployment.

---

## 6. Findings and fixes

1. Frontend simulation endpoints originally targeted port `3000`; verified as HTTP 404 and fixed with `NEXT_PUBLIC_BACKEND_HTTP_URL`.
2. Optional twin model request was removed unless the static manifest advertises the file.
3. Unknown countermeasure returned success with no effect; now returns HTTP 400.
4. Unknown routes still intentionally return 404; no catch-all success route was added.
