# AstroCare Final Report

**Date:** 2026-11-15  
**Final status:** `READY_WITH_LIMITATIONS`  
**Repositories integrated:** `abdyrazakov/AstroCare`, `Kwandiye/astrocare`, local AstroCare data pipeline and simulation engine.

---

## A. Integration summary

### Repositories integrated

- Backend Brain: `abdyrazakov/AstroCare`
- Frontend Core: `Kwandiye/astrocare`
- NASA data pipeline: local AstroCare `data_pipeline`
- Advanced Hybrid Simulation Engine: local AstroCare `simulation_engine`

### Final architecture

The unified repository combines:

- `backend/` — existing Brain, scoring, Doctor Layer, HTTP/WebSocket;
- `frontend/` — existing Next.js 3D Digital Twin;
- `data_pipeline/` — NASA OSDR ingestion and evidence extraction;
- `simulation_engine/` — Advanced Hybrid Simulation Engine;
- `shared/` — shared Pydantic contracts;
- `data/` — verified NASA evidence, manifests, processed data;
- `docs/` — integration, architecture, data, simulation, API, demo and final reports;
- `scripts/` — setup, run, test and demo automation.

### Components reused

Backend:

- strict input contract;
- NEWS2;
- radiation, lifestyle, environment and cabin CO2 scoring;
- IMM-lite condition ranking;
- Doctor Layer with Ollama, cache and rule-based fallback;
- HTTP dashboard;
- WebSocket broadcaster;
- reports and mission log;
- existing AstroCare simulation and frontend adapters.

Frontend:

- 3D Digital Twin;
- Overview, Health Analytics, AI Assistant, Training & Recovery, Mission History;
- Zustand live ring buffer;
- WebSocket brain client;
- zod BrainTick contract;
- explicit mock mode.

Data:

- NASA OSDR API connector;
- download manager;
- checksum verification;
- format detection;
- normalization;
- quality control;
- laboratory extraction;
- microbiome diversity derivation;
- study and dataset catalogs.

Simulation:

- mission clock;
- controller;
- environment engine;
- physiological engine;
- countermeasure engine;
- scenario engine;
- What-If engine;
- telemetry serializer.

### Components created

- `backend/src/astro_brain/astrocare_service.py` — unified runtime and simulation control endpoints.
- `frontend/src/components/views/DataSourcesView.tsx` — NASA provenance view.
- `frontend/src/components/views/SimulationView.tsx` — simulation control view.
- `data_pipeline/tests/test_nasa_bundle.py` — NASA evidence checks.
- `tests/test_simulation_engine.py` and `tests/test_simulation_engine_full.py` — unified simulation tests.
- `scripts/setup.sh`, `scripts/run.sh`, `scripts/test.sh`, `scripts/demo.sh`.

---

## B. NASA data acquisition

The unified bundle includes verified public OSDR studies:

| Study | Role in evidence |
| --- | --- |
| OSD-569 | CBC and whole-blood omics. |
| OSD-570 | PBMC single-nucleus omics and immune repertoire. |
| OSD-571 | Plasma proteomics, metabolomics, EVPs, cfDNA/cfRNA. |
| OSD-572 | Crew oral/nasal/skin microbiome. |
| OSD-573 | Dragon capsule microbiome swabs. |
| OSD-575 | CMP and serum immune/cardiac multiplex panels. |
| OSD-656 | Urine inflammation panel. |

Current bundled counts:

- 79 catalogued studies;
- 71 accepted;
- 8 rejected with explicit reasons;
- 23,174 real laboratory values;
- 133 real laboratory panel groupings;
- 329 microbiome samples, 327 valid Shannon-diversity values;
- 31,339 provenance records;
- fallback status `NONE`.

Important limitations:

- NASA evidence is laboratory/biospecimen data;
- NASA data is not continuous vitals telemetry;
- no NASA dataset was converted into fabricated continuous HR/HRV/SpO2/BP;
- restricted data was not accessed.

---

## C. Simulation

Implemented models:

- HR, HRV RMSSD, SBP/DBP;
- SpO2, respiratory rate, temperature;
- fatigue, stress, sleep debt;
- PVT mean and slowest 10%;
- fluid shift, IOP, SANS-related risk;
- musculoskeletal condition;
- VO2max;
- cabin ppCO2;
- radiation dose rate, daily dose and cumulative dose;
- ARED, aerobic exercise, sleep and environmental countermeasures.

Mathematical methods:

- explicit Euler;
- exponential relaxation;
- Ornstein-Uhlenbeck noise;
- bounded state clamping;
- daily discrete updates.

Astronaut profiles:

- A1 / public `ASTRO-01`;
- A2 / public `ASTRO-02`.

Supported durations:

- 60 minutes;
- 24 hours;
- 7 days;
- 30 days;
- 90 days;
- 180 days.

Scenarios:

- `HYPERCAPNIC_CABIN`;
- `NEUROCOGNITIVE_FATIGUE`;
- `SANS_FLUID_SHIFT`;
- `SOLAR_PARTICLE_EVENT`;
- `MISSED_ARED`;
- `ENVIRONMENTAL_EQUIPMENT_MALFUNCTION`.

---

## D. Backend

Preserved:

- strict input validation;
- NEWS2;
- radiation, lifestyle, cabin CO2 and environment flags;
- IMM-lite condition ranking;
- Doctor Layer;
- HTTP dashboard;
- WebSocket broadcaster;
- reports and mission log.

Added:

- unified runtime `astrocare_service`;
- simulation-to-Brain adapter;
- simulation status/control endpoints;
- scenario endpoints;
- countermeasure endpoint;
- What-If endpoint;
- NASA data status endpoint;
- stable mapping from A1/A2 to ASTRO-01/ASTRO-02;
- explicit mSv/h → µSv/h conversion.

Fixed:

- WebSocket client registration race.

---

## E. Frontend

Preserved:

- 3D Digital Twin;
- anatomical layers;
- Overview;
- Health Analytics;
- AI Assistant;
- Training & Recovery;
- Mission History;
- What-If interface;
- explicit mock mode.

Added:

- **Data Sources** view;
- **Simulation** view;
- simulation lifecycle controls;
- speed controls;
- scenario controls;
- countermeasure controls;
- What-If buttons;
- NASA manifest/provenance display;
- clear `SYNTHETIC` labeling.

---

## F. Verification

Commands and results:

### Backend tests

```bash
cd backend && .venv/bin/python -m pytest -q
```

Result:

```text
651 passed
```

### Frontend tests

```bash
cd frontend && npm test
```

Result:

```text
37 passed
```

### Frontend production build

```bash
cd frontend && npm run build
```

Result:

```text
Compiled successfully
```

### NASA data tests

```bash
cd astrocare
PYTHONPATH=. backend/.venv/bin/python -m pytest data_pipeline/tests -q
```

Result:

```text
3 passed
```

### Simulation tests

```bash
cd astrocare
PYTHONPATH=. backend/.venv/bin/python -m pytest tests/test_simulation_engine_full.py tests/test_simulation_engine.py -q
```

Result:

```text
17 passed
```

### End-to-end service

```bash
scripts/run.sh HYPERCAPNIC_CABIN
```

Verified with:

```bash
curl http://localhost:8765/simulation/status
curl http://localhost:8765/state/all
curl -I http://localhost:3000
curl -X POST http://localhost:8765/simulation/scenario \
  -H 'Content-Type: application/json' \
  -d '{"scenario_id":"HYPERCAPNIC_CABIN","action":"start"}'
```

Observed:

- simulation status returned;
- Brain outputs present for `ASTRO-01` and `ASTRO-02`;
- frontend responded with HTTP 200;
- scenario event was created successfully.

### Performance

| Simulation | Internal step | Output step | Runtime |
| --- | ---: | ---: | ---: |
| 60 minutes, 2 astronauts | 1 s | 1 s | 0.39 s |
| 180 days, 2 astronauts | 300 s | 300 s | 6.13 s |

---

## G. Known limitations

### Scientific limitations

- The simulation is not clinically validated.
- NASA data is biospecimen/laboratory evidence, not continuous vitals.
- SANS-related risk is an indicator, not a diagnosis or intracranial-pressure model.
- Radiation biology is simplified to accumulated exposure.
- NEWS2 was not validated for astronauts or microgravity.

### NASA data limitations

- No continuous NASA astronaut vitals stream was available.
- NASA records are sparse and timepoint-based.
- Large raw omics files were not downloaded by default.
- OSD-977, OSD-968, OSD-898 and OSD-989 were rejected as radiation evidence after inspection.

### Technical limitations

- `SimulationEvent` is an internal contract, not an Architect-approved shared contract.
- Live wall-clock pacing exists but is not covered by automated tests.
- Only a few scenario-composition combinations are explicitly tested.
- Docker Compose was not made the primary runtime; native scripts are verified instead.

---

## H. How to run

Install:

```bash
scripts/setup.sh
```

Run all tests:

```bash
scripts/test.sh
```

Run NASA data build:

```bash
python -m data_pipeline.build_offline_bundle
```

Offline NASA rebuild:

```bash
ASTRALIS_OFFLINE_DATA=1 python -m data_pipeline.build_offline_bundle
```

Generate 60-minute simulation:

```bash
python -m simulation_engine.cli \
  --duration-seconds 3600 \
  --internal-step 1.0 \
  --output-step 1.0 \
  --export-dir simulation_exports \
  --format jsonl \
  --summary
```

Generate 180-day simulation:

```bash
python -m simulation_engine.cli \
  --duration-seconds 15552000 \
  --internal-step 300 \
  --output-step 300 \
  --format jsonl \
  --summary
```

Run full application:

```bash
scripts/run.sh
```

Run demo:

```bash
scripts/demo.sh
```

---

## I. Final status

`READY_WITH_LIMITATIONS`

The unified application runs end to end, NASA evidence is bundled and traceable, the simulation generates synthetic telemetry, the Brain analyzes it, and the frontend displays it.

It is not marked `READY_FOR_DEMO` because the demonstration requires the judge to run local services, and the current integration has documented scientific and technical limitations.
