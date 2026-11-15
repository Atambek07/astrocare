# Simulation Engine

**Status:** Implemented.  
**Model version:** `astralis-hybrid-physiology-1.0.0`.

---

## 1. Model form

The astronaut state is represented as:

```text
dx/dt = f(x, u, theta, t) + noise(t)
```

Where:

- `x` = physiological state;
- `u` = environment and behavior inputs;
- `theta` = individual astronaut parameters;
- `t` = mission time;
- `noise` = bounded stochastic variation.

---

## 2. State variables

### Fast physiology

- HR;
- HRV RMSSD;
- systolic and diastolic blood pressure;
- SpO2;
- respiratory rate;
- temperature;
- PVT mean and slowest 10% reaction time.

### Slow physiology

- fatigue;
- stress;
- sleep debt;
- circadian misalignment;
- fluid shift index;
- IOP;
- SANS-related risk;
- musculoskeletal condition;
- VO2max.

### Environment

- cabin ppCO2;
- radiation dose rate;
- daily radiation dose;
- cumulative radiation;
- environmental stress;
- exercise load;
- microgravity exposure.

---

## 3. Integration and noise

The engine uses:

- explicit Euler integration;
- exponential relaxation;
- Ornstein-Uhlenbeck noise;
- bounded state clamping;
- daily discrete updates.

General relaxation:

```text
x(t + dt) = x(t) + (target - x(t)) * (1 - exp(-dt / tau))
```

Radiation accumulation:

```text
delta_msv = dose_rate_msv_h * dt_seconds / 3600
daily_radiation += delta_msv
cumulative_radiation += delta_msv
```

---

## 4. Astronaut profiles

`A1` maps to public `ASTRO-01` and `A2` maps to `ASTRO-02`.

They have separate:

- cardiovascular baselines and CO2/stress response;
- respiratory response;
- cognitive baselines;
- sleep need and efficiency;
- adaptation timescales;
- countermeasure adherence;
- stochastic variability.

---

## 5. Multiscale scheduling

| Process | Resolution |
| --- | --- |
| 1-Hz telemetry | configurable output step |
| Fast physiology | internal step |
| Fatigue and cognition | slower relaxation constants |
| Sleep and countermeasures | daily |
| Adaptation | day-scale relaxation |

Supported durations:

- 60 minutes;
- 24 hours;
- 7 days;
- 30 days;
- 90 days;
- 180 days.

---

## 6. Scenarios

Implemented mandatory scenarios:

1. `HYPERCAPNIC_CABIN`
2. `NEUROCOGNITIVE_FATIGUE`
3. `SANS_FLUID_SHIFT`
4. `SOLAR_PARTICLE_EVENT`

Additional scenarios:

- `MISSED_ARED`
- `ENVIRONMENTAL_EQUIPMENT_MALFUNCTION`

---

## 7. Countermeasures

Implemented:

- ARED;
- aerobic exercise;
- sleep intervention;
- environmental correction.

Countermeasures have delayed, partial and individualized effects. They do not instantly reset physiology.

---

## 8. What-If

The What-If engine snapshots the original mission, creates an isolated experiment controller, applies modifications, runs the experiment, compares results, and preserves the baseline mission.

Examples:

- missed ARED for 7 days;
- reduced sleep by 2 h/day;
- elevated ppCO2 to 5 mmHg;
- additional exercise.

What-If outputs are exploratory simulations, not clinical predictions.
