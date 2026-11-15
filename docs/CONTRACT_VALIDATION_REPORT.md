# Contract Validation Report

**Date:** 2026-11-15  
**Shared contracts:** `shared/contracts.py`, `shared/contracts.schema.json`  
**Backend input contract:** `backend/src/astro_brain/contract.py`  
**Frontend BrainTick contract:** `frontend/src/types/brain.ts`

---

## 1. Contract layers

| Layer | Contract | Validation |
| --- | --- | --- |
| Simulation | `StreamTick`, `DailyTelemetryLog`, `SimulationEvent`, `SimulationStatus`. | Pydantic v2. |
| Backend Brain | Strict `VitalsSample` input and camelCase output. | Explicit field/type/range validator. |
| Frontend | zod `BrainTick` schema. | `parseTick` rejects malformed messages. |
| NASA evidence | Shared provenance and catalog records. | Pydantic and registry checks. |

The backend input contract intentionally ignores unknown extra keys for forward compatibility.

---

## 2. Verified conversions

### Simulation → Backend

Verified fields and units:

| Simulation field | Unit | Brain field | Unit | Transformation |
| --- | ---: | --- | ---: | --- |
| `hr` | bpm | `hr` | bpm | integer conversion |
| `spo2` | % | `spo2` | % | integer conversion |
| `sbp` | mmHg | `bp.systolic` | mmHg | integer conversion |
| `dbp` | mmHg | `bp.diastolic` | mmHg | integer conversion |
| `temp_c` | °C | `temp_c` | °C | unchanged |
| `resp_rate` | breaths/min | `resp_rate` | breaths/min | integer conversion |
| `radiation_dose_rate` | mSv/h | `radiation_dose_rate` | µSv/h | ×1000 |
| `cabin_ppco2` | mmHg | `cabin_ppco2_mmhg` | mmHg | rename |
| `iop_mmhg` | mmHg | `iop_mmhg` | mmHg | unchanged |
| `hrv_rmssd` | ms | `hrv_rmssd_ms` | ms | rename |
| `pvt_slowest10_rt` | ms | `pvt_slowest10_rt_ms` | ms | rename |

Astronaut mapping:

```text
A1 → astro-01
A2 → astro-02
```

Automated tests construct a simulation state, convert it, and pass it through `parse_sample`.

---

## 3. Backend → Frontend

The existing adapter `backend/src/astro_brain/adapters/frontend.py` converts Brain output to the frontend `BrainTick` shape.

Verified required fields:

- `timestamp`;
- `alertLevel`;
- `activeFlags`;
- `rawVitals`;
- `doctorRecommendation`.

The frontend zod parser rejects malformed ticks rather than rendering invalid medical output.

---

## 4. Shared schema verification

Command:

```bash
PYTHONPATH=. backend/.venv/bin/python shared/generate_contracts_schema.py --check
```

Result: PASS.

The generator now imports `shared.contracts` and uses AstroCare schema identity.

---

## 5. Provenance contract

| Class | Requirement | Test |
| --- | --- | --- |
| `NASA_REAL` | NASA study/source traceability retained. | Registry export test. |
| `NASA_DERIVED` | Transformation method and parent source retained. | NASA validation report and data tests. |
| `SYNTHETIC` | Generator/version/seed/scenario retained; no NASA study claim. | Registry rejection test. |

---

## 6. WebSocket verification

A live integration check connected to the unified WebSocket, completed the RFC 6455 handshake, received a framed JSON `BrainTick`, and confirmed:

- astronaut ID;
- alert level;
- active flags;
- `rawVitals`;
- doctor recommendation.

Existing backend tests also verify handshake, text frame, large payload and malformed client handling.

---

## 7. Test evidence

```bash
PYTHONPATH=. backend/.venv/bin/python -m pytest backend/tests/test_unified_contracts.py backend/tests/test_astrocare_service.py -q
```

Result: **10 passed**.

Full backend suite: **656 passed**.

---

## 8. Current limitations

1. The frontend does not require provenance fields inside `BrainTick`; provenance remains connected through simulation records and Data Sources artifacts.
2. `SimulationEvent` is an internal contract, not an Architect-approved shared contract.
3. Cross-process streaming tests use real sockets but not a full browser automation run.
