# AstroCare QA Final Report

**Date:** 2026-11-15  
**Commit:** latest `main` commit at report generation  
**Final status:** `READY_WITH_LIMITATIONS`

---

## 1. Executive summary

The unified AstroCare system was audited, debugged, tested, stabilized and documented. The original Brain, 3D Digital Twin, NASA evidence pipeline and Advanced Hybrid Simulation Engine were preserved and integrated into a single application.

The audit confirmed that component-level tests were already healthy, while several integration seams were not covered by tests. The most important defects were incorrect frontend-to-backend URL routing, an unavoidable optional-asset 404, astronaut identifier mismatch, What-If state reset, and incomplete What-If controls. These were fixed at the correct architectural layer and covered by regression tests.

The application starts, generates telemetry, passes it through the Brain, broadcasts frontend-compatible updates, exposes NASA provenance, and supports simulation and What-If controls. End-to-end HTTP and WebSocket checks passed.

The system is ready for a local technical demonstration with documented limitations. It is not clinically validated and is not a medical device.

---

## 2. System under test

| Component | Description |
| --- | --- |
| Backend Brain | Python scoring, IMM-lite condition ranking, Doctor Layer, HTTP/WebSocket. |
| Frontend | Next.js 14 3D Digital Twin, analytics, controls and provenance views. |
| NASA pipeline | OSDR discovery, ingestion, checksums, normalization, QC and provenance. |
| Simulation engine | Hybrid physiological, environmental, cognitive and adaptation simulation. |
| Integration layer | Shared contracts, telemetry adapter, HTTP and WebSocket transport. |

Key versions:

- backend contract: `astro-brain 0.6.0`;
- simulation engine: `astralis-simulation-1.0.0`;
- simulation model: `astralis-hybrid-physiology-1.0.0`.

---

## 3. Initial quality assessment

Baseline command:

```bash
scripts/test.sh
```

Initial result before fixes:

| Suite | Result |
| --- | --- |
| Backend | 656 passed |
| Frontend | 37 passed |
| Initial data tests | 3 passed |
| Initial simulation tests | 3 passed |
| Frontend production build | PASS |

Aggregate: **694 passed, 0 failed**, with known untested integration gaps.

---

## 4. Defect analysis

The complete register is in `docs/BUG_REGISTER.md`.

High-value defects found:

| ID | Defect | Root cause | Fix |
| --- | --- | --- | --- |
| QA-001 | Simulation API requests returned 404 from frontend. | Same-origin paths used instead of backend base URL. | Added backend client helper and `NEXT_PUBLIC_BACKEND_HTTP_URL`. |
| QA-002 | Optional 3D asset request returned 404. | Code probed absent `astronaut_twin.glb` directly. | Added asset manifest; request only advertised optional assets. |
| QA-003 | Astronaut IDs mismatched frontend selector. | Brain emitted `ASTRO-01`; frontend used `astro-01`. | Canonical public mapping to frontend IDs. |
| QA-004 | Live tick could show the other astronaut. | Last element of interleaved list used without filtering. | Filter by selected astronaut. |
| QA-006 | What-If experiment reset cloned state. | `reload_config` rebuilt engines and astronaut states. | Mutate cloned configuration without rebuilding engines. |
| QA-007/QA-008 | What-If controls were incomplete. | Declared fields were not applied. | Implemented sleep-duration delta and missed-ARED behavior. |
| QA-009 | Unknown countermeasure silently succeeded. | Missing else branch. | Raise validation error; service returns 400. |
| QA-011 | Shared schema generator failed. | Imported ASTRALIS-only backend module. | Import unified shared contracts. |
| QA-012 | `N/A` treated as suspect. | Missing-token case comparison error. | Case-insensitive missing-token handling. |

---

## 5. HTTP and navigation validation

### Verified frontend routes

| Route | Status |
| --- | --- |
| `/` | 200 |
| `/crew` | 200 |
| unknown route | intentional 404 |

### Verified backend routes

| Route | Status |
| --- | --- |
| `/simulation/status` | 200 |
| `/data/status` | 200 |
| `/state` | 200 |
| `/state/all` | 200 |
| `/history` | 200 |
| `/log` | 200 |
| `/report?astronaut_id=astro-01` | 200 |
| unknown backend route | intentional 404 |

### Escape-key investigation

All keyboard listeners were audited. Escape handlers exist only for:

1. clearing Digital Twin zone selection;
2. closing metric/zone drawers;
3. closing TopBar dropdowns.

No Escape handler performs navigation, router replacement, form submission or an API request. The reported 404s were traced to independent simulation endpoint and optional-model requests.

Fixes:

1. Drawer Escape handling now uses capture-phase priority.
2. What-If drawer Escape closes only that surface.
3. Simulation endpoint and optional-model 404s were removed.

---

## 6. Backend verification

Final command:

```bash
cd backend && .venv/bin/python -m pytest -q
```

Result: **656 passed**.

Verified:

- strict input validation;
- NEWS2;
- radiation and cumulative limits;
- lifestyle/environment flags;
- IMM-lite ranking;
- Doctor fallback;
- reports and logs;
- WebSocket;
- unified simulation endpoints;
- contract conversion.

---

## 7. Frontend verification

Final commands:

```bash
cd frontend && npm test
cd frontend && npm run build
```

Results:

- **39 tests passed**;
- production build passed.

Verified:

- existing Digital Twin and views preserved;
- explicit mock mode;
- Data Sources view;
- Simulation view;
- selected-astronaut telemetry filtering;
- safe optional-model handling;
- TypeScript build.

---

## 8. NASA data pipeline verification

Final command:

```bash
PYTHONPATH=. backend/.venv/bin/python -m pytest data_pipeline/tests -q
```

Result: **10 passed**.

Bundled evidence:

| Metric | Value |
| --- | --- |
| Cataloged OSDR studies | 79 |
| Accepted studies | 71 |
| Rejected with reason | 8 |
| Real laboratory values | 23,174 |
| Real panel groupings | 133 |
| Microbiome samples | 329 |
| Valid Shannon-diversity values | 327 |
| Provenance records in source bundle | 31,339 |
| Download fallback | `NONE` |

Verified studies include OSD-569, OSD-570, OSD-571, OSD-572, OSD-573, OSD-575 and OSD-656.

NASA data is classified as `NASA_REAL` or `NASA_DERIVED` and is not presented as continuous astronaut telemetry.

---

## 9. Simulation verification

Final command:

```bash
PYTHONPATH=. backend/.venv/bin/python -m pytest tests/test_simulation_engine_full.py tests/test_simulation_engine.py tests/test_simulation_numerics.py -q
```

Result: **30 passed**.

Verified:

- 60-minute 1-Hz generation;
- 180-day mission;
- deterministic reproducibility;
- A1/A2 divergence;
- numerical stability at 1, 5, 30 and 300 s;
- physiological bounds;
- radiation monotonicity;
- scenarios;
- countermeasures;
- checkpointing;
- What-If isolation and effect.

---

## 10. Integration verification

### Contract tests

```bash
PYTHONPATH=. backend/.venv/bin/python -m pytest backend/tests/test_unified_contracts.py backend/tests/test_astrocare_service.py -q
```

Result: **10 passed**.

Verified:

- simulation shared contracts;
- simulation state to Brain input;
- Brain output fields;
- Brain output to frontend BrainTick;
- astronaut ID mapping;
- JSON Schema freshness.

### Live end-to-end checks

Command:

```bash
scripts/test_e2e.sh
```

Result: **15 checks passed**.

Verified with the unified service:

1. simulation status;
2. NASA data status;
3. Brain state/all;
4. history;
5. log;
6. report;
7. scenario start;
8. pause;
9. resume;
10. valid countermeasure;
11. scenario terminate;
12. What-If request;
13. intentional unknown-route 404;
14. WebSocket handshake;
15. WebSocket framed BrainTick.

---

## 11. Performance assessment

Measured on CPU-only local environment:

| Test | Runtime | Max RSS |
| --- | ---: | ---: |
| 60-minute simulation, 2 astronauts, 1 Hz | 0.93 s | ~39 MiB |
| 180-day simulation, 2 astronauts, 300 s step | 6.81 s | ~128 MiB |
| Next.js production build | 27.74 s | ~720 MiB |

See `docs/PERFORMANCE_REPORT.md`.

---

## 12. Documentation assessment

Created or updated:

- `README.md`;
- `docs/INDEX.md`;
- `docs/SYSTEM_ARCHITECTURE.md`;
- `docs/NASA_DATA_ACQUISITION_AND_PROCESSING.md`;
- `docs/DATA_PROVENANCE_AND_LINEAGE.md`;
- `docs/SCIENTIFIC_METHODS.md`;
- `docs/ADVANCED_HYBRID_SIMULATION.md`;
- `docs/BACKEND_REFERENCE.md`;
- `docs/FRONTEND_REFERENCE.md`;
- `docs/API_REFERENCE.md`;
- `docs/TESTING_AND_VALIDATION.md`;
- `docs/INSTALLATION_AND_DEPLOYMENT.md`;
- `docs/KNOWN_LIMITATIONS.md`;
- `docs/CHANGELOG.md`;
- QA reports.

Formal documentation is in English. Python and TypeScript comments remain in Russian.

---

## 13. Remaining limitations

1. The system is not clinically validated.
2. Continuous NASA vitals do not exist in the bundled evidence.
3. Simulation coefficients include engineering assumptions and synthetic scenario values.
4. `SimulationEvent` is not yet a shared Architect-approved contract.
5. Browser automation tests are not installed.
6. Docker Compose is provided but native startup remains the verified primary path.
7. CORS, authentication and structured production telemetry require hardening before non-local deployment.

---

## 14. Final readiness assessment

`READY_WITH_LIMITATIONS`

Objective basis:

- all mandatory automated quality gates pass;
- no known critical defect remains open;
- live backend, simulation, WebSocket and frontend route checks pass;
- NASA evidence is bundled, verified and traceable;
- complete documentation and limitations are disclosed.

`READY_FOR_DEMO` is not used because full browser automation was not run and local-demo deployment still requires the documented native execution steps.
