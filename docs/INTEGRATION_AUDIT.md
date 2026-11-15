# AstroCare Integration Audit

**Date:** 2026-11-15  
**Auditor:** Unified Integration Agent  
**Result:** Implementation proceeds with the backend contract as the integration boundary.

---

## 1. Source repositories

| Repository | Role | Baseline state |
| --- | --- | --- |
| `abdyrazakov/AstroCare` | Backend Brain | 649 tests; 648 passed, 1 WebSocket race failure at baseline. |
| `Kwandiye/astrocare` | Frontend Digital Twin | 37 tests passed; Next.js production build passed. |
| `astralis` local workspace | NASA data pipeline + simulation engine | 55 tests passed, 16 skipped. |

Both public repositories were cloned without changing their remotes.

---

## 2. Backend architecture

The backend is a compact, contract-driven Brain:

- strict input validation in `src/astro_brain/contract.py`;
- NEWS2, radiation, lifestyle, environment and cabin CO2 scoring;
- IMM-lite condition ranking;
- Doctor Layer with Ollama, cache and deterministic fallback;
- mission reports and plans;
- HTTP dashboard and dependency-free WebSocket broadcaster.

The Brain's public process interface is:

```python
from astro_brain.pipeline import Brain

Brain().process(raw_dict)
```

The input contract is documented in `backend/AGENTS.md`. It requires one astronaut sample at one timestamp and accepts unknown extra keys for forward compatibility.

The output contract is camelCase and contains `alertLevel`, `news2Score`, `activeFlags`, `flagDetails`, `likelyConditions`, `doctorRecommendation`, `bodySystems`, `plans` and related fields.

---

## 3. Frontend architecture

The frontend is a Next.js App Router application with:

- interactive 3D Digital Twin and anatomical layers;
- Overview, Health Analytics, AI Assistant, Training & Recovery, Mission History;
- Zustand store with a 600-tick live ring buffer;
- WebSocket brain client;
- deterministic in-browser mock fallback;
- zod contract for BrainTick;
- vitest tests for trend and triage behavior.

The existing BrainTick schema is stricter than the Brain output object. The backend already contains a dedicated frontend adapter, `astro_brain/adapters/frontend.py`, to shape Brain output into the frontend contract.

---

## 4. Existing contracts

### Backend input

The authoritative input is the backend input contract. Important fields include:

- `timestamp`
- `astronaut_id`
- `hr`
- `spo2`
- `bp.systolic`
- `bp.diastolic`
- `temp_c`
- `resp_rate`
- `radiation_dose_rate`
- `mission_day`
- `mission_phase`
- `cabin_ppco2_mmhg`
- `iop_mmhg`
- `hrv_rmssd_ms`
- `pvt_slowest10_rt_ms`

Radiation in the Brain contract is **µSv/h**. Simulation radiation is **mSv/h**. The adapter must multiply by 1000.

### Backend output

The Brain output contract is camelCase. The frontend must read `alertLevel` directly and must not recompute severity.

### Frontend BrainTick

The frontend expects a normalized `BrainTick` with:

- `timestamp`
- `alertLevel`
- `activeFlags`
- `rawVitals`
- `doctorRecommendation`
- optional astronaut, mission, steps, plans, conditions and body systems.

### Simulation contracts

The simulation engine emits local contract objects with the same names and units as the ASTRALIS contracts. It does not depend on the AstroCare backend.

---

## 5. Existing features

### Backend

Preserved:

- contract validation;
- NEWS2;
- radiation and lifestyle flags;
- IMM-lite condition ranking;
- Doctor Layer with rule-based fallback;
- HTTP dashboard;
- WebSocket broadcaster;
- reports and mission log;
- Astralis adapter and frontend adapter.

### Frontend

Preserved:

- 3D Digital Twin;
- anatomical layers;
- Overview;
- Health Analytics;
- AI Assistant;
- Training & Recovery;
- Mission History;
- triage visualization;
- medical protocols;
- What-If interface;
- explicit mock badge.

### Data pipeline

Reused from the ASTRALIS workspace:

- OSDR API connector;
- file index connector;
- download manager with checksum and cache fallback;
- format detection;
- normalization;
- quality checks;
- laboratory extraction;
- microbiome diversity derivation;
- provenance registry;
- study catalog and dataset registry;
- NASA evidence and radiation audit.

### Simulation

Reused from the ASTRALIS workspace:

- mission clock;
- simulation controller;
- environment engine;
- coupled physiological engine;
- countermeasure engine;
- scenario engine;
- What-If engine;
- telemetry serialization.

---

## 6. Mock and synthetic data sources

The frontend currently falls back to an in-browser mock when the WebSocket is unavailable. This is useful for offline development but must remain explicit.

The unified application keeps the mock badge and distinguishes:

- `LIVE BACKEND`;
- NASA REAL;
- NASA DERIVED;
- `SYNTHETIC`.

The simulation engine always labels generated telemetry as `SYNTHETIC`.

---

## 7. NASA ingestion status

The workspace already contains verified OSDR ingestion results for:

- OSD-569;
- OSD-570;
- OSD-571;
- OSD-572;
- OSD-573;
- OSD-575;
- OSD-656.

The data includes laboratory values, microbiome diversity summaries, manifests, checksums, quality reports and provenance. These are copied into the unified `data/` directory:

- `data/raw/nasa/`
- `data/manifests/`
- `data/processed/`
- `data/reference/`

The pipeline remains reproducible through `data_pipeline/build_offline_bundle.py`.

---

## 8. Contract incompatibilities

| Issue | Resolution |
| --- | --- |
| Simulation uses A1/A2; Brain examples use ASTRO-01/02. | Public adapter maps A1 → ASTRO-01 and A2 → ASTRO-02. |
| Simulation radiation is mSv/h; Brain expects µSv/h. | Adapter multiplies by 1000. |
| Brain output is not directly the frontend BrainTick schema. | Reuse existing `astro_brain/adapters/frontend.py`. |
| Frontend mock fallback can appear live. | Mock badge remains explicit and live/backend mode is displayed. |
| Provenance is not part of Brain input/output. | Provenance is preserved separately in data artifacts and telemetry records; Brain contract remains unchanged. |

---

## 9. Required adapters

Created or preserved:

- simulation state → backend input contract;
- backend output → frontend BrainTick;
- NASA evidence artifacts → frontend Data Sources view;
- simulation status and controls → unified HTTP service.

---

## 10. Unified architecture

```text
NASA OSDR
  -> data_pipeline
  -> verified NASA evidence
  -> data/manifests + data/processed + data/reference
  -> Data Sources UI

Advanced Hybrid Simulation Engine
  -> SYNTHETIC telemetry
  -> telemetry adapter
  -> Brain.process()
  -> Brain output
  -> WebSocket BrainTick
  -> Frontend Digital Twin
```

The unified backend service combines:

- existing Brain;
- existing HTTP dashboard;
- existing WebSocket broadcaster;
- simulation runtime;
- simulation control endpoints;
- NASA data status endpoint.

---

## 11. Integration risks

| Risk | Mitigation |
| --- | --- |
| Mock data mistaken for live data. | Mode badge and explicit simulation/NASA labels. |
| Radiation unit mismatch. | Explicit ×1000 conversion in the adapter. |
| Frontend recomputing medical logic. | Frontend reads `alertLevel` and Brain output directly. |
| NASA data being interpreted as continuous vitals. | NASA data is shown in Data Sources and used as evidence, not as live vitals. |
| Simulation output unstable. | Bounded states, OU noise, validation tests, checkpoint support. |

---

## 12. Implementation sequence

1. Preserve backend and frontend.
2. Unify repository.
3. Add telemetry adapter and unified service.
4. Add Data Sources and Simulation views.
5. Run backend, frontend, data pipeline and simulation tests.
6. Run end-to-end backend + simulation + frontend flow.
7. Document and finalize demo.

---

## 13. Baseline verification

Backend:

```text
1 failed, 648 passed
```

The single failure was a WebSocket registration race; it was fixed by registering the client before sending the 101 handshake.

Frontend:

```text
37 tests passed
Next.js production build passed
```

Existing ASTRALIS workspace:

```text
55 passed, 16 skipped
```
