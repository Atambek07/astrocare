# Simulation Validation Report

**Model version:** `astralis-hybrid-physiology-1.0.0`  
**Engine version:** `astralis-simulation-1.0.0`  
**Date:** 2026-11-15  
**Status:** software and model verification complete; clinical validation not claimed.

---

## 1. Verification terminology

| Term | Meaning in AstroCare |
| --- | --- |
| Software verification | Implementation satisfies the specified interfaces and behavior. |
| Model verification | Numerical implementation solves the specified equations in a stable, bounded way. |
| Model calibration | Parameter estimation from evidence. |
| Model validation | Comparison with independent empirical observations. |

AstroCare has completed software and model verification. It has **not** performed clinical model validation and does not claim NASA validation.

---

## 2. State variables

### Fast physiology

- HR, bpm.
- HRV RMSSD, ms.
- Systolic/diastolic pressure, mmHg.
- SpO2, %.
- Respiratory rate, breaths/min.
- Temperature, °C.
- PVT mean and slowest 10%, ms.

### Slow physiology

- Fatigue, stress, probability [0,1].
- Sleep debt, h.
- Circadian misalignment, [0,1].
- Fluid shift index, [0,3].
- IOP, mmHg.
- SANS-related risk, [0,1].
- Musculoskeletal condition, [0,1].
- VO2max, mL/kg/min.

### Environment

- Cabin ppCO2, mmHg.
- Radiation dose rate, mSv/h.
- Daily and cumulative radiation, mSv.
- Environmental stress and exercise load, [0,1].

---

## 3. Equations

### Relaxation

Fast variables use target relaxation:

```text
x(t + Δt) = x(t) + (x_target(t) - x(t)) * (1 - exp(-Δt / τ))
```

Example HR target:

```text
HR_target =
    HR_baseline
    + stress × stress_hr_gain
    + max(0, ppCO2 - ppCO2_baseline) × co2_hr_gain
    + exercise_load × exercise_hr_gain
    + fatigue × 2
    + fluid_shift × 0.5
```

### Sleep

```text
sleep_duration =
    sleep_need
    - stress × stress_sleep_penalty
    - environmental_stress × environment_sleep_penalty
    + sleep_duration_delta
    + N(0, 0.35²)

sleep_debt(t+1) = max(0, sleep_debt(t) + sleep_need - sleep_duration)
```

### Fluid shift and IOP

```text
fluid_shift_target = fluid_shift_max × microgravity_exposure
IOP_target = IOP_baseline + fluid_shift × iop_fluid_shift_gain
```

### SANS-related risk

```text
z = fluid_shift × gain_fluid_shift
    + max(0, IOP - 20) × gain_iop
    - 1

SANS_risk = 1 / (1 + exp(-z))
```

### Radiation

```text
ΔmSv = dose_rate_msv/h × Δt_s / 3600
daily_radiation += ΔmSv
cumulative_radiation += ΔmSv
```

---

## 4. Stochastic model

Physiological noise uses bounded Ornstein-Uhlenbeck increments:

```text
dX = θ(μ - X)dt + σdW
```

Discrete update:

```text
X(t+Δt) = μ + (X(t)-μ)exp(-θΔt) + ε
Var(ε) = σ²(1-exp(-2θΔt)) / (2θ)
```

Each astronaut has a separate deterministic random generator and variability scale.

---

## 5. Parameter origin classification

| Class | Examples |
| --- | --- |
| Published scientific evidence | Resting HR, HRV, SpO2, sleep need, IOP order of magnitude. |
| Derived from evidence | Direction and approximate scale of CO2 response, fluid shift, and deconditioning. |
| Engineering assumption | Exact relaxation timescales, stress gains, exercise gain coefficients. |
| Synthetic configuration | Random seed, scenario magnitudes, A1/A2 profiles. |

Exact values are documented in `simulation_engine/profiles.py` with units, descriptions, sources and evidence levels.

---

## 6. Multiscale scheduling

| Process | Schedule |
| --- | --- |
| Telemetry output | configurable output step |
| HR/HRV/BP/SpO2/respiration | internal step |
| PVT and fatigue | internal step with slower relaxation |
| Sleep and countermeasures | mission-day boundary |
| Fluid shift and musculoskeletal adaptation | day-scale relaxation |

Supported internal steps verified: 1 s, 5 s, 30 s and 300 s.

---

## 7. Numerical verification

| Test | Result |
| --- | --- |
| Finite values at 1, 5, 30 and 300 s | PASS |
| State bounds during hypercapnia | PASS |
| Cumulative radiation monotonicity | PASS |
| Different step sizes produce different but bounded results | PASS |
| Same seed reproduces telemetry | PASS |
| 60-minute 1 Hz run | PASS |
| 180-day run | PASS |

---

## 8. Individual verification

A1 and A2 have separate baselines, adaptation coefficients and noise scales. Under the same environment, their HR and HRV trajectories differ. Same-seed reproducibility is preserved.

---

## 9. Scenario verification

| Scenario | Environment/physiology effect | Event | Recovery | Result |
| --- | --- | --- | --- | --- |
| `HYPERCAPNIC_CABIN` | ppCO2 target rises; HR/HRV/PVT respond. | Started/terminated event recorded. | Gradual ppCO2 and physiology relaxation. | PASS |
| `NEUROCOGNITIVE_FATIGUE` | Sleep debt, fatigue and PVT rise. | Scenario events recorded. | Sleep intervention and circadian recovery. | PASS |
| `SANS_FLUID_SHIFT` | Fluid shift and IOP rise; SANS risk indicator increases. | Scenario events recorded. | Countermeasure/relaxation. | PASS |
| `SOLAR_PARTICLE_EVENT` | Radiation dose rate rises; dose accumulates monotonically. | Scenario events recorded. | Dose-rate decays; cumulative dose remains. | PASS |
| `MISSED_ARED` | ARED adherence suppressed. | Scenario event recorded. | Exercise schedule can resume. | PASS |
| `ENVIRONMENTAL_EQUIPMENT_MALFUNCTION` | ppCO2/environmental stress rise. | Scenario event recorded. | Environmental correction. | PASS |

---

## 10. Countermeasure verification

| Countermeasure | Verified behavior |
| --- | --- |
| ARED | Increases musculoskeletal condition; missed ARED allows decline. |
| Aerobic exercise | Increases modeled VO2max. |
| Sleep intervention | Reduces sleep debt and later sleep penalty. |
| Environmental correction | Reduces stress/fatigue; ppCO2 target returns to nominal. |

Unknown countermeasures are rejected.

---

## 11. What-If verification

The What-If engine snapshots the original mission, creates an isolated controller, restores the baseline state, applies modifications, advances only the clone, compares metrics, and leaves the original mission unchanged.

Verified modifications:

- ppCO2 target;
- sleep duration delta;
- missed ARED;
- ARED/aerobic adherence;
- sleep intervention effectiveness;
- radiation dose-rate delta;
- explicit scenario.

Regression tests confirm that sleep reduction changes sleep debt, missed ARED changes VO2max, and the baseline snapshot remains unchanged.

---

## 12. Performance

| Test | Internal/output step | Runtime | Memory |
| --- | ---: | ---: | ---: |
| 60 min, 2 astronauts | 1 s | 0.93 s | ~39 MiB |
| 180 days, 2 astronauts | 300 s | 6.81 s | ~128 MiB |

---

## 13. Limitations

1. Equations are engineering approximations, not validated physiological laws.
2. Parameters are not individually calibrated to NASA astronaut data.
3. Continuous telemetry is synthetic.
4. SANS-related risk is not an intracranial-pressure model.
5. Radiation is accumulated dose, not a biophysical transport model.
6. Long-term predictions should be treated as sensitivity demonstrations.
