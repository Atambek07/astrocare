# API

The unified service exposes the existing Brain API plus simulation and NASA data status endpoints.

Default backend port: `8765`  
Default WebSocket port: `8787`

---

## 1. Existing Brain endpoints

### POST `/ingest`

Accepts one Brain input sample and returns one Brain output object.

Example:

```bash
curl -s -X POST http://localhost:8765/ingest \
  -H 'Content-Type: application/json' \
  -d @backend/examples/input_nominal.json
```

### GET `/state`

Returns the latest Brain output.

```bash
curl -s http://localhost:8765/state
```

Optional filter:

```bash
curl -s 'http://localhost:8765/state?astronaut_id=ASTRO-01'
```

### GET `/state/all`

Returns latest outputs for all astronauts.

### GET `/history`

Returns the latest Brain outputs.

### GET `/log`

Returns mission episodes.

### GET `/report`

Returns a mission report.

```bash
curl -s 'http://localhost:8765/report?astronaut_id=ASTRO-01&format=text'
```

### POST `/ask`

Asks the Doctor Layer a question using the latest context.

```bash
curl -s -X POST http://localhost:8765/ask \
  -H 'Content-Type: application/json' \
  -d '{"astronaut_id":"ASTRO-01","question":"What should the crew do now?"}'
```

---

## 2. Simulation endpoints

### GET `/simulation/status`

Returns simulation status, astronauts and environment.

### POST `/simulation/control`

Controls lifecycle or speed.

```bash
curl -s -X POST http://localhost:8765/simulation/control \
  -H 'Content-Type: application/json' \
  -d '{"action":"start"}'
```

Supported actions:

- `start`;
- `pause`;
- `resume`;
- `stop`;
- `reset`;
- `set_speed` with `speed`.

### POST `/simulation/scenario`

Starts or terminates a scenario.

```bash
curl -s -X POST http://localhost:8765/simulation/scenario \
  -H 'Content-Type: application/json' \
  -d '{"scenario_id":"HYPERCAPNIC_CABIN","action":"start"}'
```

### POST `/simulation/countermeasure`

Applies a countermeasure.

```bash
curl -s -X POST http://localhost:8765/simulation/countermeasure \
  -H 'Content-Type: application/json' \
  -d '{"type":"ENVIRONMENTAL_CORRECTION"}'
```

### POST `/simulation/what-if`

Runs an isolated What-If experiment.

```bash
curl -s -X POST http://localhost:8765/simulation/what-if \
  -H 'Content-Type: application/json' \
  -d '{"ppco2_target_mmhg":5.0,"duration_seconds":1800}'
```

---

## 3. NASA data endpoints

### GET `/data/status`

Returns NASA bundle status:

- bundle ID;
- generation timestamp;
- fallback status;
- artifact counts.

---

## 4. WebSocket

The WebSocket broadcasts the existing frontend `BrainTick` payload.

URL:

```text
ws://localhost:8787
```

The frontend connects automatically through `NEXT_PUBLIC_BRAIN_WS_URL`.
