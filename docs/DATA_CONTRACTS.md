# Data Contracts

AstroCare keeps the existing Backend Brain contract as the integration boundary.

---

## 1. Backend input contract

The authoritative input contract is:

```text
backend/AGENTS.md
backend/src/astro_brain/contract.py
```

Required fields:

- `timestamp`
- `astronaut_id`
- `hr`
- `spo2`
- `bp.systolic`
- `bp.diastolic`
- `temp_c`
- `resp_rate`
- `radiation_dose_rate`

Common optional fields:

- `exercise_minutes_today`
- `required_exercise_minutes`
- `caloric_intake`
- `caloric_target`
- `sleep_hours`
- `mood_score`
- `noaa_s_scale`
- `bfo_dose_30day_mgy_eq`
- `radiation_dose_career_msv`
- `mission_day`
- `mission_phase`
- `cabin_ppco2_mmhg`
- `iop_mmhg`
- `hrv_rmssd_ms`
- `pvt_slowest10_rt_ms`

Important unit:

- Brain radiation dose rate is **µSv/h**.
- Simulation radiation is **mSv/h**.
- The adapter multiplies by 1000.

---

## 2. Backend output contract

Brain output is camelCase and includes:

- `timestamp`;
- `astronautId`;
- `alertLevel`;
- `news2Score`;
- `activeFlags`;
- `flagDetails`;
- `likelyConditions`;
- `doctorRecommendation`;
- `doctorSource`;
- `bodySystems`;
- `medicalKit`;
- `plans`.

The frontend reads `alertLevel` directly and does not recompute severity.

---

## 3. Frontend BrainTick contract

The frontend expects a zod-validated `BrainTick`:

- `timestamp`;
- `alertLevel`;
- `activeFlags`;
- `rawVitals`;
- `doctorRecommendation`;
- optional astronaut, mission, steps, plans and conditions.

The adapter is:

```text
backend/src/astro_brain/adapters/frontend.py
```

---

## 4. Simulation contract

The simulation engine emits shared Pydantic contracts in:

```text
shared/contracts.py
```

Main records:

- `StreamTick`;
- `DailyTelemetryLog`;
- `SimulationEvent`;
- `SimulationStatus`.

Simulation telemetry always has `source_type = SYNTHETIC`.

---

## 5. Provenance contract

Provenance is preserved outside the Brain input contract.

The backend input contract ignores unknown extra keys, but AstroCare still keeps provenance in:

- simulation telemetry records;
- NASA manifests;
- processed evidence files;
- frontend Data Sources view.

This preserves traceability without changing the existing Brain contract.

---

## 6. Adapter responsibilities

| Adapter | Direction | Responsibility |
| --- | --- | --- |
| `astrocare_service.simulation_state_to_input` | simulation → Brain | unit conversion, ID mapping, required-field construction. |
| `adapters.astralis.stream_tick_to_input` | telemetry → Brain | direct tick mapping. |
| `adapters.frontend.to_brain_tick` | Brain → frontend | output shaping for Digital Twin. |

The adapter never fabricates missing medical measurements.
