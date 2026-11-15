# Testing and Validation

**Version:** 2026-11-15  
**Quality gate:** `scripts/qa.sh`  
**Machine summary:** `reports/qa_summary.json`.

---

## 1. Test strategy

| Level | Scope |
| --- | --- |
| Unit | Contract parsing, scoring, flags, math utilities, serializers, normalization. |
| Integration | Simulation → Brain adapter, Brain → frontend shape, HTTP and WebSocket. |
| Contract | Shared Pydantic models, JSON Schema freshness, unit and ID conversion. |
| Simulation verification | Determinism, bounds, numerical stability, scenarios, What-If isolation. |
| Data verification | NASA evidence, provenance, normalization, quality controls. |
| End-to-end | Real service startup, HTTP endpoints, WebSocket frame, frontend build/routes. |

---

## 2. Commands

### Complete suite

```bash
scripts/test.sh
```

### Individual gates

```bash
scripts/test_backend.sh
scripts/test_frontend.sh
scripts/test_data_pipeline.sh
scripts/test_simulation.sh
scripts/test_integration.sh
scripts/test_frontend_build.sh
scripts/check_docs.sh
scripts/qa.sh
```

### Shared schema check

```bash
PYTHONPATH=. backend/.venv/bin/python shared/generate_contracts_schema.py --check
```

---

## 3. Current results

| Gate | Command | Result |
| --- | --- | --- |
| Backend | `backend/.venv/bin/python -m pytest -q` | **656 passed** |
| Frontend | `npm test` | **39 passed** |
| Data pipeline | `pytest data_pipeline/tests -q` | **10 passed** |
| Simulation | simulation tests | **30 passed** |
| Integration contracts | unified contract tests | **10 passed** |
| End-to-end service | `scripts/test_e2e.sh` | **15 checks passed** |
| Frontend build | `npm run build` | PASS |
| Shared schema | `--check` | PASS |
| HTTP endpoints | live service checks | PASS |
| WebSocket | live frame check | PASS |

---

## 4. Backend test coverage

The backend suite covers:

- strict input contract;
- NEWS2 components and aggregate risk;
- radiation flags and cumulative limits;
- lifestyle and environment flags;
- IMM-lite condition ranking;
- Doctor Layer cache, timeout and fallback behavior;
- dashboard state, history, reports and ask endpoint;
- WebSocket framing and malformed clients;
- trajectory, phase priors, resources and plans.

---

## 5. Frontend test coverage

Vitest covers:

- BrainTick contract rejection and acceptance behavior;
- trend classification;
- triage rules;
- hard triggers;
- MFI thresholds;
- personal baseline behavior.

Production build additionally verifies TypeScript and static generation.

---

## 6. NASA data tests

Covered:

- original value preservation;
- unknown-unit behavior;
- case-insensitive missing values;
- relative timepoint preservation;
- completeness, unit, range and timestamp checks;
- baseline sufficiency;
- NASA_REAL provenance export;
- rejection of synthetic NASA identity;
- presence and integrity of bundled NASA study/evidence manifests.

---

## 7. Simulation verification

Covered:

- 60-minute 1 Hz generation;
- deterministic reproducibility;
- shared-contract serialization;
- hypercapnic and SPE scenarios;
- scenario termination and recovery;
- checkpoint round trip;
- telemetry export;
- astronaut divergence;
- countermeasure effect;
- mission-time monotonicity;
- event provenance;
- 180-day feasibility;
- finite values across integration steps;
- physiological bounds;
- radiation monotonicity;
- step-size sensitivity;
- What-If sleep and ARED effects.

---

## 8. Contract tests

Covered:

- simulation `StreamTick` and `DailyTelemetryLog`;
- simulation state to strict Brain input;
- Brain output fields;
- Brain output to frontend BrainTick;
- astronaut ID mapping;
- JSON Schema freshness.

---

## 9. End-to-end verification

The following live flow was verified:

1. Start unified backend and frontend with `scripts/run.sh`.
2. Query `/simulation/status`.
3. Query `/state/all`.
4. Confirm frontend `/` and `/crew` return HTTP 200.
5. Confirm unknown frontend route returns intentional 404.
6. Start and terminate a scenario.
7. Apply a valid countermeasure.
8. Reject an invalid countermeasure.
9. Run a What-If experiment.
10. Connect WebSocket and receive a framed BrainTick.

---

## 10. Offline verification

Offline behavior is supported by design and verified structurally:

- NASA artifacts are local;
- simulation has no external dependency;
- Doctor fallback runs without Ollama;
- frontend has local static data and explicit mock fallback.

---

## 11. Test environment

| Item | Value |
| --- | --- |
| OS | Linux |
| Python | 3.12 |
| Node/npm | Node 20-era toolchain from package lock |
| Backend venv | `backend/.venv` |
| Doctor mode in integration tests | Offline deterministic |
| GPU | Not required |

---

## 12. Validation terminology

AstroCare distinguishes:

1. **Software verification** — implementation matches specification.
2. **Model verification** — equations are solved stably and reproducibly.
3. **Model calibration** — parameter estimation from data.
4. **Model validation** — comparison with independent empirical observations.

Only software and model verification are claimed. Clinical validation and NASA validation are not claimed.
