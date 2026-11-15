# API Reference

**Base URL:** `http://localhost:8765`  
**WebSocket base URL:** `ws://localhost:8787`  
**Service:** unified AstroCare Brain + simulation runtime.

---

## 1. Conventions

- JSON request and response bodies.
- Timestamps are ISO-8601 UTC with `Z`.
- Brain input uses snake_case.
- Brain output and WebSocket `BrainTick` use camelCase.
- Unknown route returns HTTP 404 with JSON error.
- CORS currently permits local browser access.

---

## 2. Brain endpoints

### POST `/ingest`

**Purpose:** validate one sample and return one Brain assessment.

**Request body:** Brain input contract.

Example:

```bash
curl -s -X POST http://localhost:8765/ingest \
  -H 'Content-Type: application/json' \
  -d @backend/examples/input_nominal.json
```

**Success response:** `200 OK`

```json
{
  "timestamp": "2026-11-14T10:00:00Z",
  "astronautId": "ASTRO-01",
  "alertLevel": "green",
  "news2Score": 0,
  "activeFlags": [],
  "flagDetails": [],
  "likelyConditions": [],
  "bodySystems": {},
  "plans": {},
  "doctorRecommendation": "All monitored parameters nominal.",
  "doctorSource": "fallback"
}
```

**Errors:**

| Status | Reason |
| --- | --- |
| 400 | malformed JSON or input contract violation. |
| 500 | unexpected processing error. |

---

### GET `/state`

Returns latest output.

Query:

| Name | Required | Description |
| --- | --- | --- |
| `astronaut_id` | no | Filter by astronaut. |

Empty response:

```json
{"status":"no data yet"}
```

---

### GET `/state/all`

Returns:

```json
{
  "astronauts": {
    "astro-01": {"timestamp":"...","alertLevel":"green"}
  },
  "count": 1
}
```

---

### GET `/history`

Returns up to 50 recent outputs in arrival order.

Query:

| Name | Required |
| --- | --- |
| `astronaut_id` | no |

---

### GET `/log`

Returns mission episodes.

Optional query: `astronaut_id`.

---

### GET `/report`

Returns a mission report.

Query:

| Name | Required | Values |
| --- | --- | --- |
| `astronaut_id` | yes | e.g. `astro-01` |
| `format` | no | `json` or `text` |

Errors:

- `400` if astronaut ID is missing;
- `404` if no data exists.

---

### GET `/models`

Returns local Ollama models available to the AI Assistant.

```json
{
  "available": true,
  "models": ["qwen2.5:7b-instruct"],
  "default": "qwen2.5:7b-instruct"
}
```

When Ollama is unreachable:

```json
{
  "available": false,
  "models": [],
  "default": null
}
```

Model names containing `embed` are excluded.

---

### POST `/ask`

Asks the Doctor Layer a contextual question.

Request:

```json
{
  "astronaut_id": "astro-01",
  "question": "What should the crew monitor next?",
  "model": "qwen2.5:3b-instruct"
}
```

`model` is optional. It must match `[A-Za-z0-9._:/-]{1,100}`.

Without `model`, `/ask` uses the configured default model and respects `ASTRO_DOCTOR_OFFLINE`. With an explicit `model`, the selected chat model is used even when `ASTRO_DOCTOR_OFFLINE=1`, because that variable disables only the background recommendation layer.

Success response:

```json
{
  "answer": "...",
  "source": "llm",
  "disclaimer": "...",
  "contextTimestamp": "..."
}
```

`source` is `llm` for a successful model answer or `fallback` when the model is unavailable or fails.

Backend astronaut IDs are lowercase, for example `astro-01`; other casing returns `404`.

Errors:

- `400` missing/invalid fields;
- `400 invalid model name` for an invalid `model` value;
- `404` no context for astronaut.

---

## 3. Simulation endpoints

### GET `/simulation/status`

Returns:

```json
{
  "status": {
    "mission_status": "RUNNING",
    "mission_time_seconds": 12,
    "mission_day": 1,
    "mission_phase": "PHASE_1_ACUTE_ADAPTATION",
    "simulation_speed": 1.0,
    "active_scenarios": [],
    "active_astronauts": ["A1", "A2"],
    "current_model_version": "astralis-hybrid-physiology-1.0.0",
    "random_seed": 20260501,
    "internal_step_seconds": 1.0,
    "output_step_seconds": 1.0,
    "source_type": "SYNTHETIC"
  },
  "astronauts": ["astro-01", "astro-02"],
  "environment": {},
  "mode": "simulation"
}
```

---

### POST `/simulation/control`

Request:

```json
{"action":"start"}
```

Supported actions:

- `start`;
- `pause`;
- `resume`;
- `stop`;
- `reset`;
- `set_speed` plus numeric `speed`.

Success:

```json
{"status":"ok","simulation":{}}
```

Error: `400` for invalid action or speed.

---

### POST `/simulation/scenario`

Request:

```json
{"scenario_id":"HYPERCAPNIC_CABIN","action":"start"}
```

Actions: `start`, `terminate`.

Success: `200` with simulation event.

Errors: `400` for missing ID, unknown scenario or invalid action.

---

### POST `/simulation/countermeasure`

Request:

```json
{"type":"ENVIRONMENTAL_CORRECTION"}
```

Optional:

- `astronaut_id`;
- `effectiveness`.

Supported types:

- `ARED`;
- `AEROBIC_EXERCISE`;
- `SLEEP_INTERVENTION`;
- `ENVIRONMENTAL_CORRECTION`.

Success: `200` with event.  
Error: `400` for unknown type.

---

### POST `/simulation/what-if`

Request:

```json
{
  "ppco2_target_mmhg": 5.0,
  "sleep_duration_delta_h": -2.0,
  "missed_ared_days": 7,
  "duration_seconds": 604800,
  "experiment_id": "MISSED_ARED_7D"
}
```

Success: `200` with baseline results, experiment results, difference metrics, events and limitations.  
Error: `400` for invalid duration or fields.

---

## 4. NASA data endpoint

### GET `/data/status`

Returns:

```json
{
  "manifest_available": true,
  "bundle_id": "...",
  "generated_at_utc": "...",
  "fallback_status": "NONE",
  "counts": {}
}
```

---

## 5. WebSocket

**URL:** `ws://localhost:8787`

The server broadcasts a `BrainTick` after each successful simulation tick processed by the Brain.

Required BrainTick fields:

- `timestamp`;
- `alertLevel`;
- `activeFlags`;
- `rawVitals`;
- `doctorRecommendation`.

Common optional fields:

- `astronautId`;
- `missionDay`;
- `steps`;
- `likelyConditions`;
- `bodySystems`;
- `plans`;
- `news2Score`;
- `flagDetails`;
- `doctorSource`.

Malformed ticks are rejected by the frontend zod parser.

---

## 6. Intentional 404s

The following return 404 by design:

- unknown HTTP route;
- report for an astronaut with no data;
- unknown frontend route;
- absent optional static asset.
