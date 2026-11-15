# Architecture

**Owner:** Unified Integration Agent  
**Status:** Implemented.

---

## 1. Unified data flow

```text
NASA OSDR API / AWS
        |
        v
data_pipeline discovery
        |
        v
metadata inspection + file selection
        |
        v
download + checksum + raw storage
        |
        v
parsing + normalization + quality control
        |
        v
feature extraction + evidence registry
        |
        +--------------------------------+
        |                                |
        v                                v
Data Sources UI             simulation configuration
                                     |
                                     v
                          simulation_engine
                                     |
                                     v
                         SYNTHETIC telemetry
                                     |
                                     v
                       telemetry adapter (µSv/h, ID mapping)
                                     |
                                     v
                              Brain.process()
                                     |
                                     v
                         Brain output / BrainTick
                                     |
                                     v
                         WebSocket + HTTP transport
                                     |
                                     v
                         frontend Digital Twin
```

---

## 2. Component boundaries

| Component | Owner | Responsibility |
| --- | --- | --- |
| `data_pipeline/` | Data integration | NASA discovery, ingestion, validation, processing, provenance. |
| `simulation_engine/` | Simulation Agent | Physiological and environmental dynamics. |
| `backend/src/astro_brain/` | Backend Brain | Scoring, flags, conditions, doctor recommendations, reports. |
| `frontend/` | Frontend Core | 3D Digital Twin, analytics, controls, provenance display. |
| `shared/` | Shared contracts | Pydantic models and JSON Schema. |

No component re-implements another component's medical logic.

---

## 3. Runtime integration

The unified service is:

```text
backend/src/astro_brain/astrocare_service.py
```

It combines:

- existing `Brain`;
- existing HTTP dashboard;
- existing WebSocket broadcaster;
- simulation controller;
- simulation control endpoints;
- NASA data status endpoint.

The service runs in one process for local demonstration. It can be replaced by separate services without changing the contracts.

---

## 4. Transport

| Transport | Endpoint | Payload |
| --- | --- | --- |
| HTTP POST | `/ingest` | Brain input sample |
| HTTP GET | `/state`, `/state/all`, `/history` | Brain output |
| HTTP GET | `/log`, `/report` | mission events and SBAR-style reports |
| GET/POST | `/simulation/*` | simulation status/control |
| GET | `/data/status` | NASA bundle/provenance status |
| WebSocket | `/` on WebSocket port | `BrainTick` for frontend |

---

## 5. Frontend integration

The frontend uses `BrainConnector` to connect to `ws://localhost:8787`.

The active mode is visible:

- `LIVE BACKEND`;
- `DEMO MOCK`.

The frontend never recomputes Brain severity. It reads `alertLevel` directly from the BrainTick.

---

## 6. Offline mode

After setup, the application works without internet:

- cached NASA data remains available;
- simulation runs locally;
- Brain works with rule-based Doctor fallback;
- frontend loads local assets and mock mode only when explicitly disconnected.

---

## 7. Contract flow

1. Simulation emits internal telemetry.
2. Telemetry adapter converts it to Brain input.
3. Brain validates the sample and rejects invalid values.
4. Brain output is converted to frontend BrainTick.
5. WebSocket broadcasts the tick.
6. Frontend renders status, vitals, flags, recommendation and provenance labels.

---

## 8. Failure behavior

| Failure | Behavior |
| --- | --- |
| Simulation unavailable | Frontend stays in explicit mock mode. |
| Ollama unavailable | Brain uses deterministic fallback recommendation. |
| NASA network unavailable | Last verified local bundle is used. |
| Invalid sample | Brain returns 400 and does not guess values. |
