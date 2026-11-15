# Scientific Methods

**Version:** 2026-11-15  
**Status:** engineering model with documented assumptions; no clinical validation claimed.

---

## 1. Scientific objectives

AstroCare models directional responses to spaceflight stressors so that a health-monitoring interface can be exercised end to end. It does not diagnose disease, predict individual clinical outcomes, or replace a flight surgeon.

---

## 2. Evidence sources

| Source type | Use in AstroCare |
| --- | --- |
| NASA OSDR public laboratory data | Reference distributions and evidence lineage. |
| NASA HRP risk descriptions | Direction of spaceflight-associated risks. |
| NASA standards and operational references | Context for cabin CO2, radiation and countermeasures. |
| Peer-reviewed space physiology literature | Plausible ranges and response direction. |
| Engineering assumptions | Exact model coefficients not available from evidence. |

Every coefficient in `simulation_engine/profiles.py` carries one of the following labels:

- `NASA_MEASURED`;
- `PUBLISHED_SCIENTIFIC`;
- `DERIVED_PARAMETER`;
- `MODEL_ASSUMPTION`;
- `SYNTHETIC_DEMONSTRATION`.

---

## 3. Modeling assumptions

### Physiological timescales

| Process | Modeled scale |
| --- | --- |
| Cardiovascular and respiratory response | seconds to minutes |
| Cognitive response | seconds to minutes |
| Fatigue and sleep pressure | minutes to hours |
| Circadian adjustment | hours to days |
| Fluid redistribution | hours to days |
| Musculoskeletal adaptation | weeks to months |

These are model resolutions, not universal physiological constants.

### Coupling assumptions

1. Elevated cabin CO2 may increase respiratory drive and cardiovascular load and may degrade cognitive performance.
2. Sleep debt increases fatigue and slows PVT response.
3. Stress can increase HR, reduce HRV, and impair sleep.
4. Microgravity promotes headward fluid redistribution.
5. Missed exercise contributes to gradual deconditioning.
6. Environmental correction produces gradual, not immediate, recovery.

---

## 4. Mathematical representation

The astronaut state is represented as:

```text
dx/dt = f(x, u, θ, t) + noise(t)
```

where:

- `x` = physiological state vector;
- `u` = environment and behavior inputs;
- `θ` = individual parameters;
- `t` = mission time;
- `noise` = bounded stochastic process.

Fast variables use target relaxation:

```text
dx/dt = (x_target - x) / τ
```

Discrete update:

```text
x(t+Δt) = x(t) + (x_target - x(t)) (1 - exp(-Δt/τ))
```

---

## 5. Key formulations

### Cardiovascular target

```text
HR_target =
    HR₀
    + stress × k_HR,stress
    + max(0, ppCO2 - ppCO2₀) × k_HR,CO2
    + exercise_load × k_HR,exercise
    + fatigue × 2
    + fluid_shift × 0.5
```

```text
HRV_target =
    HRV₀
    - stress × k_HRV,stress
    - max(0, ppCO2 - ppCO2₀) × k_HRV,CO2
    - fatigue × 5
    - fluid_shift × 1
    + cardiovascular_adaptation × 2
```

### Sleep

```text
sleep_duration =
    sleep_need
    - stress × k_sleep,stress
    - environment_stress × k_sleep,environment
    + sleep_duration_delta
    + ε_sleep

sleep_debt(t+1) =
    max(0, sleep_debt(t) + sleep_need - sleep_duration)
```

### Fluid shift and IOP

```text
fluid_shift_target = fluid_shift_max × microgravity_exposure
IOP_target = IOP₀ + fluid_shift × k_IOP,fluid_shift
```

### SANS-related risk

```text
z = fluid_shift × k_SANS,fluid_shift
    + max(0, IOP - 20 mmHg) × k_SANS,IOP
    - 1

SANS_risk = 1 / (1 + exp(-z))
```

### VO2max and musculoskeletal state

Aerobic exercise adds a small training gain. Missed ARED allows gradual detraining. Values are clamped to the model domain.

### Radiation

```text
Δdose_mSv = dose_rate_mSv/h × Δt_h
daily_dose += Δdose_mSv
cumulative_dose += Δdose_mSv
```

Cumulative dose is monotonic nondecreasing.

---

## 6. Parameter classes and examples

| Parameter | Unit | Class |
| --- | --- | --- |
| Baseline HR | bpm | Published scientific evidence / engineering range. |
| Baseline HRV RMSSD | ms | Published scientific evidence / engineering range. |
| CO2 HR/HRV gains | bpm or ms per mmHg | Derived parameter. |
| Stress HR gain | bpm per stress unit | Model assumption. |
| Sleep need | h/day | Published scientific evidence. |
| Stress sleep penalty | h per stress unit | Model assumption. |
| Fluid-shift timescale | day | Derived parameter. |
| Musculoskeletal timescale | day | Derived parameter. |
| VO2max detraining | mL/kg/min per missed ARED day | Model assumption. |
| Radiation biological sensitivity | 1/mSv | Synthetic demonstration parameter. |

---

## 7. Stochastic representation

Physiological noise uses an Ornstein-Uhlenbeck process:

```text
dX = θ(μ - X)dt + σdW
```

Discrete variance:

```text
Var(ε) = σ²(1 - exp(-2θΔt)) / (2θ)
```

This avoids independent white noise on every sample and preserves short-term correlation.

---

## 8. Units

| Variable | Unit |
| --- | --- |
| HR | bpm |
| HRV RMSSD | ms |
| Blood pressure | mmHg |
| SpO2 | % |
| Respiratory rate | breaths/min |
| Temperature | °C |
| PVT | ms |
| ppCO2 | mmHg |
| Dose rate | mSv/h |
| Daily/cumulative dose | mSv |
| VO2max | mL/kg/min |
| Sleep duration/debt | h |

---

## 9. Calibration and validation status

| Activity | Status |
| --- | --- |
| Software verification | Complete through automated tests. |
| Model verification | Complete for boundedness, reproducibility and step-size behavior. |
| Parameter calibration | Limited to evidence-informed ranges; individual calibration not performed. |
| Model validation | Not performed against independent continuous astronaut telemetry. |
| Clinical validation | Not performed. |

---

## 10. Uncertainty and limitations

1. Exact coefficients are not derived by a published calibration procedure.
2. NASA OSDR data are laboratory/timepoint data, not continuous telemetry.
3. The SANS-related risk indicator is not an intracranial-pressure model.
4. Radiation is accumulated exposure, not particle transport or tissue-dose modeling.
5. Individual health status, pharmacology, EVA exposure and mission events beyond the configured scenarios are not modeled.
6. Scenario magnitudes are synthetic and are used to exercise the system, not to reproduce a specific mission.
