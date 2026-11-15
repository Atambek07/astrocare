# AstroCare Demonstration Guide

This guide produces a reproducible judge demonstration.

---

## 1. Setup

From the repository root:

```bash
scripts/setup.sh
scripts/test.sh
```

---

## 2. Start the unified application

```bash
scripts/run.sh
```

Optional scenario startup:

```bash
scripts/run.sh HYPERCAPNIC_CABIN
```

Default URLs:

- frontend: `http://localhost:3000`;
- backend: `http://localhost:8765`;
- WebSocket: `ws://localhost:8787`.

---

## 3. Stage 1 — NASA evidence

Open:

```text
http://localhost:3000
```

Go to **Data Sources**.

Explain:

1. NASA OSDR source.
2. Verified study IDs.
3. Accepted and rejected studies.
4. Processing pipeline.
5. Quality status.
6. Provenance classes.

Point out that NASA data is laboratory/biospecimen evidence, not continuous vitals.

---

## 4. Stage 2 — Simulation initialization

Open **Simulation**.

Confirm:

- `ASTRO-01` and `ASTRO-02`;
- mission day and phase;
- speed;
- environment state.

Press **Start** if the mission is paused.

---

## 5. Stage 3 — Live telemetry

Return to **Overview**.

Show:

- active mode `LIVE BACKEND`;
- HR, BP, SpO2, respiration and temperature;
- Brain recommendation;
- active flags;
- Digital Twin zones.

All telemetry is labeled `SYNTHETIC`.

---

## 6. Stage 4 — Hypercapnic cabin

In **Simulation**, start:

```text
HYPERCAPNIC_CABIN
```

Observe:

1. ppCO2 rising;
2. HR and respiration changing;
3. Brain flags appearing;
4. Digital Twin zone status changing;
5. Doctor recommendation updating.

---

## 7. Stage 5 — Countermeasure and recovery

Apply:

```text
ENVIRONMENTAL_CORRECTION
```

Then optionally apply:

```text
SLEEP_INTERVENTION
```

Explain that recovery is gradual, not instant.

---

## 8. Stage 6 — Solar particle event

Start:

```text
SOLAR_PARTICLE_EVENT
```

Show:

- rising radiation dose rate;
- increasing daily dose;
- increasing cumulative dose;
- Brain radiation flags;
- mission history event.

---

## 9. Stage 7 — What-If

Use the **What-If** buttons in Simulation view, for example:

- Missed ARED 7 days;
- Sleep −2 h/day;
- ppCO2 5 mmHg.

Explain that the experiment is isolated and the baseline mission is unchanged.

---

## 10. Stop the demo

Press `Ctrl+C` in the terminal running `scripts/run.sh`.
