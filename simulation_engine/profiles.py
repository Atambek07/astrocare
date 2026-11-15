"""Индивидуальные профили A1 и A2 для гибридной симуляции.

Профили являются демонстрационными и не представляют реальные медицинские
записи астронавтов. Значения — информированные инженерные допущения, а не
клинические нормы.
"""

from __future__ import annotations

from .config import (
    AdaptationParameters,
    CardiovascularParameters,
    CognitiveParameters,
    CountermeasureParameters,
    Coefficient,
    EnvironmentConfig,
    EvidenceLevel,
    ParameterProfile,
    RespiratoryParameters,
    SleepParameters,
    StochasticParameters,
    ValidationConfig,
    coefficient,
)


def _c(
    name: str,
    value: float,
    unit: str,
    description: str,
    source: str,
    evidence_level: EvidenceLevel = EvidenceLevel.MODEL_ASSUMPTION,
    *,
    adjustable: bool = True,
) -> Coefficient:
    """Сокращённый конструктор коэффициента."""
    return coefficient(name, value, unit, description, source, evidence_level, adjustable=adjustable)


def _cardiovascular(
    baseline_hr: float,
    baseline_hrv: float,
    baseline_sbp: float,
    baseline_dbp: float,
    *,
    stress_hr_gain: float = 8.0,
    stress_hrv_loss: float = 4.0,
    co2_hr_gain: float = 2.2,
    co2_hrv_loss: float = 3.5,
    exercise_hr_gain: float = 12.0,
    hr_tau_s: float = 8.0,
    hrv_tau_s: float = 25.0,
) -> CardiovascularParameters:
    """Создать кардиоваскулярный блок профиля."""
    return CardiovascularParameters(
        baseline_hr=_c("baseline_hr", baseline_hr, "bpm", "Resting heart rate baseline.", "Engineering default informed by published spaceflight deconditioning ranges.", EvidenceLevel.PUBLISHED_SCIENTIFIC),
        baseline_hrv_rmssd=_c("baseline_hrv_rmssd", baseline_hrv, "ms", "Resting HRV RMSSD baseline.", "Engineering default informed by spaceflight HRV literature.", EvidenceLevel.PUBLISHED_SCIENTIFIC),
        baseline_sbp=_c("baseline_sbp", baseline_sbp, "mmHg", "Resting systolic pressure baseline.", "Engineering default.", EvidenceLevel.MODEL_ASSUMPTION),
        baseline_dbp=_c("baseline_dbp", baseline_dbp, "mmHg", "Resting diastolic pressure baseline.", "Engineering default.", EvidenceLevel.MODEL_ASSUMPTION),
        stress_hr_gain=_c("stress_hr_gain", stress_hr_gain, "bpm per VAS unit", "Heart-rate gain per stress unit.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        stress_hrv_loss=_c("stress_hrv_loss", stress_hrv_loss, "ms per VAS unit", "HRV reduction per stress unit.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        co2_hr_gain=_c("co2_hr_gain", co2_hr_gain, "bpm per mmHg", "Heart-rate gain per elevated cabin ppCO2.", "Derived from documented CO2/HRV relationship direction.", EvidenceLevel.DERIVED_PARAMETER),
        co2_hrv_loss=_c("co2_hrv_loss", co2_hrv_loss, "ms per mmHg", "HRV reduction per elevated cabin ppCO2.", "Derived from documented CO2/HRV relationship direction.", EvidenceLevel.DERIVED_PARAMETER),
        exercise_hr_gain=_c("exercise_hr_gain", exercise_hr_gain, "bpm", "Transient heart-rate gain during exercise.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        hr_tau_s=_c("hr_tau_s", hr_tau_s, "s", "Heart-rate relaxation timescale.", "Model assumption for fast cardiovascular dynamics.", EvidenceLevel.MODEL_ASSUMPTION),
        hrv_tau_s=_c("hrv_tau_s", hrv_tau_s, "s", "HRV relaxation timescale.", "Model assumption for fast autonomic dynamics.", EvidenceLevel.MODEL_ASSUMPTION),
    )


def _respiratory(
    baseline_spo2: float,
    baseline_resp_rate: float,
    baseline_temp_c: float,
    *,
    co2_resp_gain: float = 0.8,
    co2_spo2_loss: float = 0.15,
    resp_rate_tau_s: float = 6.0,
    temp_tau_s: float = 600.0,
) -> RespiratoryParameters:
    """Создать респираторный блок профиля."""
    return RespiratoryParameters(
        baseline_spo2=_c("baseline_spo2", baseline_spo2, "%", "Resting peripheral oxygen saturation baseline.", "Engineering default.", EvidenceLevel.PUBLISHED_SCIENTIFIC),
        baseline_resp_rate=_c("baseline_resp_rate", baseline_resp_rate, "breaths/min", "Resting respiratory rate baseline.", "Engineering default.", EvidenceLevel.PUBLISHED_SCIENTIFIC),
        baseline_temp_c=_c("baseline_temp_c", baseline_temp_c, "Celsius", "Resting core/skin temperature baseline.", "Engineering default.", EvidenceLevel.PUBLISHED_SCIENTIFIC),
        co2_resp_gain=_c("co2_resp_gain", co2_resp_gain, "breaths/min per mmHg", "Respiratory-rate gain per elevated ppCO2.", "Derived from CO2 ventilatory response direction.", EvidenceLevel.DERIVED_PARAMETER),
        co2_spo2_loss=_c("co2_spo2_loss", co2_spo2_loss, "% per mmHg", "SpO2 reduction per elevated ppCO2.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        resp_rate_tau_s=_c("resp_rate_tau_s", resp_rate_tau_s, "s", "Respiratory-rate relaxation timescale.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        temp_tau_s=_c("temp_tau_s", temp_tau_s, "s", "Body-temperature relaxation timescale.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
    )


def _cognitive(
    baseline_mean_rt: float,
    baseline_slowest_rt: float,
    *,
    fatigue_pvt_gain: float = 60.0,
    stress_pvt_gain: float = 25.0,
    co2_pvt_gain: float = 18.0,
    pvt_tau_s: float = 60.0,
) -> CognitiveParameters:
    """Создать когнитивный блок профиля."""
    return CognitiveParameters(
        baseline_pvt_mean_rt_ms=_c("baseline_pvt_mean_rt_ms", baseline_mean_rt, "ms", "Resting PVT-B mean reaction time baseline.", "Engineering default.", EvidenceLevel.PUBLISHED_SCIENTIFIC),
        baseline_pvt_slowest10_rt_ms=_c("baseline_pvt_slowest10_rt_ms", baseline_slowest_rt, "ms", "Resting PVT-B slowest 10% reaction time baseline.", "Engineering default.", EvidenceLevel.PUBLISHED_SCIENTIFIC),
        fatigue_pvt_gain=_c("fatigue_pvt_gain", fatigue_pvt_gain, "ms per fatigue unit", "PVT slowing per fatigue unit.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        stress_pvt_gain=_c("stress_pvt_gain", stress_pvt_gain, "ms per stress unit", "PVT slowing per stress unit.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        co2_pvt_gain=_c("co2_pvt_gain", co2_pvt_gain, "ms per mmHg", "PVT slowing per elevated ppCO2.", "Derived from documented CO2/cognitive-performance direction.", EvidenceLevel.DERIVED_PARAMETER),
        pvt_tau_s=_c("pvt_tau_s", pvt_tau_s, "s", "PVT relaxation timescale.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
    )


def _sleep(
    sleep_need_h: float,
    baseline_sleep_efficiency: float,
    *,
    circadian_recovery_rate: float = 0.08,
    sleep_debt_decay_rate: float = 0.10,
    stress_sleep_penalty: float = 1.2,
    environment_sleep_penalty: float = 0.8,
) -> SleepParameters:
    """Создать блок сна и циркадного ритма."""
    return SleepParameters(
        sleep_need_h=_c("sleep_need_h", sleep_need_h, "h/day", "Individual sleep need per mission day.", "Engineering default.", EvidenceLevel.PUBLISHED_SCIENTIFIC),
        baseline_sleep_efficiency_pct=_c("baseline_sleep_efficiency_pct", baseline_sleep_efficiency, "%", "Baseline sleep efficiency.", "Engineering default.", EvidenceLevel.PUBLISHED_SCIENTIFIC),
        circadian_recovery_rate=_c("circadian_recovery_rate", circadian_recovery_rate, "1/day", "Circadian realignment rate.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        sleep_debt_decay_rate=_c("sleep_debt_decay_rate", sleep_debt_decay_rate, "1/day", "Sleep-debt repayment rate.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        stress_sleep_penalty=_c("stress_sleep_penalty", stress_sleep_penalty, "h per stress unit", "Sleep-duration reduction per stress unit.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        environment_sleep_penalty=_c("environment_sleep_penalty", environment_sleep_penalty, "h per environment-stress unit", "Sleep-duration reduction per environmental stress.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
    )


def _adaptation(
    fluid_shift_max: float,
    baseline_iop: float,
    *,
    cardio_tau_days: float = 12.0,
    fluid_tau_days: float = 4.0,
    musculoskeletal_tau_days: float = 45.0,
    vo2max_training_gain: float = 0.06,
    vo2max_detraining_rate: float = 0.18,
    iop_fluid_shift_gain: float = 2.0,
    sans_risk_gain_fluid_shift: float = 0.9,
    sans_risk_gain_iop: float = 0.10,
    radiation_biological_sensitivity: float = 0.05,
) -> AdaptationParameters:
    """Создать блок долгосрочной адаптации."""
    return AdaptationParameters(
        microgravity_cardio_adaptation_tau_days=_c("microgravity_cardio_adaptation_tau_days", cardio_tau_days, "day", "Cardiovascular adaptation timescale.", "Model assumption informed by deconditioning literature.", EvidenceLevel.DERIVED_PARAMETER),
        microgravity_fluid_shift_tau_days=_c("microgravity_fluid_shift_tau_days", fluid_tau_days, "day", "Fluid-redistribution timescale.", "Model assumption informed by headward fluid-shift literature.", EvidenceLevel.DERIVED_PARAMETER),
        musculoskeletal_tau_days=_c("musculoskeletal_tau_days", musculoskeletal_tau_days, "day", "Musculoskeletal deconditioning timescale.", "Model assumption informed by unloading literature.", EvidenceLevel.DERIVED_PARAMETER),
        vo2max_training_gain=_c("vo2max_training_gain", vo2max_training_gain, "mL/kg/min per completed session", "VO2max gain per completed aerobic session.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        vo2max_detraining_rate=_c("vo2max_detraining_rate", vo2max_detraining_rate, "mL/kg/min per missed ARED day", "VO2max decline per missed ARED day.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        fluid_shift_max_index=_c("fluid_shift_max_index", fluid_shift_max, "index 0-3", "Maximum modeled cephalad fluid-shift index.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        baseline_iop_mmhg=_c("baseline_iop_mmhg", baseline_iop, "mmHg", "Baseline intraocular pressure.", "Engineering default.", EvidenceLevel.PUBLISHED_SCIENTIFIC),
        iop_fluid_shift_gain=_c("iop_fluid_shift_gain", iop_fluid_shift_gain, "mmHg per fluid-shift unit", "IOP gain per fluid-shift index unit.", "Model assumption informed by SANS risk direction.", EvidenceLevel.DERIVED_PARAMETER),
        sans_risk_gain_fluid_shift=_c("sans_risk_gain_fluid_shift", sans_risk_gain_fluid_shift, "probability per fluid-shift unit", "SANS-risk gain per fluid-shift unit.", "Model assumption informed by SANS risk direction.", EvidenceLevel.DERIVED_PARAMETER),
        sans_risk_gain_iop=_c("sans_risk_gain_iop", sans_risk_gain_iop, "probability per mmHg", "SANS-risk gain per IOP unit above 20 mmHg.", "Model assumption informed by SANS risk direction.", EvidenceLevel.DERIVED_PARAMETER),
        radiation_biological_sensitivity=_c("radiation_biological_sensitivity", radiation_biological_sensitivity, "1/mSv", "Individual biological sensitivity to cumulative radiation.", "Synthetic demonstration parameter.", EvidenceLevel.SYNTHETIC_DEMONSTRATION),
    )


def _countermeasure(
    ared_adherence: float,
    aerobic_adherence: float,
    *,
    ared_minutes: float = 45.0,
    aerobic_minutes: float = 30.0,
    ared_musculoskeletal_gain: float = 0.02,
    aerobic_vo2max_gain: float = 0.04,
    recovery_rate: float = 0.20,
    sleep_intervention_effectiveness: float = 0.65,
) -> CountermeasureParameters:
    """Создать блок контрмер."""
    return CountermeasureParameters(
        ared_adherence=_c("ared_adherence", ared_adherence, "fraction 0-1", "Expected ARED adherence.", "Synthetic demonstration parameter.", EvidenceLevel.SYNTHETIC_DEMONSTRATION),
        aerobic_adherence=_c("aerobic_adherence", aerobic_adherence, "fraction 0-1", "Expected aerobic-exercise adherence.", "Synthetic demonstration parameter.", EvidenceLevel.SYNTHETIC_DEMONSTRATION),
        ared_minutes_per_session=_c("ared_minutes_per_session", ared_minutes, "min", "Planned ARED session duration.", "Engineering default.", EvidenceLevel.MODEL_ASSUMPTION),
        aerobic_minutes_per_session=_c("aerobic_minutes_per_session", aerobic_minutes, "min", "Planned aerobic session duration.", "Engineering default.", EvidenceLevel.MODEL_ASSUMPTION),
        ared_musculoskeletal_gain=_c("ared_musculoskeletal_gain", ared_musculoskeletal_gain, "condition per session", "Musculoskeletal-condition gain per ARED session.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        aerobic_vo2max_gain=_c("aerobic_vo2max_gain", aerobic_vo2max_gain, "mL/kg/min per session", "VO2max gain per aerobic session.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        recovery_rate=_c("recovery_rate", recovery_rate, "1/day", "General recovery rate after countermeasure.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        sleep_intervention_effectiveness=_c("sleep_intervention_effectiveness", sleep_intervention_effectiveness, "fraction 0-1", "Effectiveness of sleep intervention.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
    )


def _stochastic(
    hr_sigma: float,
    hrv_sigma: float,
    spo2_sigma: float,
    temp_sigma: float,
    resp_rate_sigma: float,
    pvt_sigma: float,
    *,
    ou_mean_reversion: float = 0.08,
    individual_variability_scale: float = 1.0,
) -> StochasticParameters:
    """Создать блок стохастики."""
    return StochasticParameters(
        hr_noise_sigma=_c("hr_noise_sigma", hr_sigma, "bpm", "Gaussian heart-rate noise standard deviation.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        hrv_noise_sigma=_c("hrv_noise_sigma", hrv_sigma, "ms", "Gaussian HRV noise standard deviation.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        spo2_noise_sigma=_c("spo2_noise_sigma", spo2_sigma, "%", "Gaussian SpO2 noise standard deviation.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        temp_noise_sigma=_c("temp_noise_sigma", temp_sigma, "Celsius", "Gaussian temperature noise standard deviation.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        resp_rate_noise_sigma=_c("resp_rate_noise_sigma", resp_rate_sigma, "breaths/min", "Gaussian respiratory-rate noise standard deviation.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        pvt_noise_sigma=_c("pvt_noise_sigma", pvt_sigma, "ms", "Gaussian PVT noise standard deviation.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        ou_mean_reversion=_c("ou_mean_reversion", ou_mean_reversion, "1/s", "Ornstein-Uhlenbeck mean-reversion strength.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        individual_variability_scale=_c("individual_variability_scale", individual_variability_scale, "multiplier", "Individual stochastic-variability multiplier.", "Synthetic demonstration parameter.", EvidenceLevel.SYNTHETIC_DEMONSTRATION),
    )


def default_profiles() -> list[ParameterProfile]:
    """Вернуть профили A1 и A2 с разными индивидуальными параметрами."""
    a1 = ParameterProfile(
        astronaut_id="A1",
        display_name="Commander A1",
        role="Commander",
        is_control=False,
        cardiovascular=_cardiovascular(72.0, 42.0, 118.0, 74.0, stress_hr_gain=9.0, stress_hrv_loss=5.0, co2_hr_gain=2.6, co2_hrv_loss=4.0),
        respiratory=_respiratory(98.0, 14.0, 36.6, co2_resp_gain=0.9, co2_spo2_loss=0.18),
        cognitive=_cognitive(250.0, 305.0, fatigue_pvt_gain=70.0, stress_pvt_gain=28.0, co2_pvt_gain=20.0),
        sleep=_sleep(7.5, 88.0, stress_sleep_penalty=1.4, environment_sleep_penalty=1.0),
        adaptation=_adaptation(2.4, 16.5, cardio_tau_days=11.0, fluid_tau_days=3.5, musculoskeletal_tau_days=40.0),
        countermeasure=_countermeasure(0.72, 0.88),
        stochastic=_stochastic(0.8, 1.2, 0.18, 0.035, 0.35, 6.0, individual_variability_scale=1.15),
    )
    a2 = ParameterProfile(
        astronaut_id="A2",
        display_name="Mission Specialist A2",
        role="Mission Specialist",
        is_control=True,
        cardiovascular=_cardiovascular(66.0, 52.0, 116.0, 72.0, stress_hr_gain=7.0, stress_hrv_loss=3.5, co2_hr_gain=2.0, co2_hrv_loss=3.0),
        respiratory=_respiratory(98.5, 13.5, 36.5, co2_resp_gain=0.7, co2_spo2_loss=0.12),
        cognitive=_cognitive(235.0, 285.0, fatigue_pvt_gain=55.0, stress_pvt_gain=22.0, co2_pvt_gain=16.0),
        sleep=_sleep(7.2, 91.5, stress_sleep_penalty=1.0, environment_sleep_penalty=0.7),
        adaptation=_adaptation(1.9, 15.8, cardio_tau_days=13.0, fluid_tau_days=4.5, musculoskeletal_tau_days=50.0),
        countermeasure=_countermeasure(0.93, 0.96),
        stochastic=_stochastic(0.65, 1.0, 0.15, 0.03, 0.3, 5.0, individual_variability_scale=0.9),
    )
    return [a1, a2]


def default_environment() -> EnvironmentConfig:
    """Вернуть конфигурацию кабины и радиационного фона."""
    return EnvironmentConfig(
        baseline_ppco2_mmhg=_c("baseline_ppco2_mmhg", 2.35, "mmHg", "Nominal cabin ppCO2.", "Engineering default informed by ISS cabin guidance.", EvidenceLevel.PUBLISHED_SCIENTIFIC),
        ppco2_noise_sigma=_c("ppco2_noise_sigma", 0.025, "mmHg", "Cabin ppCO2 noise standard deviation.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        ppco2_tau_s=_c("ppco2_tau_s", 180.0, "s", "Cabin ppCO2 relaxation timescale.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        baseline_radiation_dose_rate_msv_h=_c("baseline_radiation_dose_rate_msv_h", 0.020, "mSv/h", "Nominal GCR dose rate.", "Derived from approximate 0.48 mSv/day mission scenario.", EvidenceLevel.DERIVED_PARAMETER),
        radiation_noise_sigma=_c("radiation_noise_sigma", 0.0015, "mSv/h", "Radiation dose-rate noise standard deviation.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        radiation_tau_s=_c("radiation_tau_s", 300.0, "s", "Radiation dose-rate relaxation timescale.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        microgravity_exposure=_c("microgravity_exposure", 1.0, "fraction 0-1", "Microgravity exposure level.", "Model assumption for LEO mission.", EvidenceLevel.MODEL_ASSUMPTION),
        environmental_stress_baseline=_c("environmental_stress_baseline", 0.10, "index 0-1", "Baseline environmental stress.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        co2_correction_tau_s=_c("co2_correction_tau_s", 180.0, "s", "Cabin ppCO2 correction timescale.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
        radiation_event_decay_tau_s=_c("radiation_event_decay_tau_s", 1800.0, "s", "Radiation event decay timescale.", "Model assumption.", EvidenceLevel.MODEL_ASSUMPTION),
    )


def default_validation() -> ValidationConfig:
    """Вернуть конфигурацию валидации состояний."""
    return ValidationConfig()


__all__ = [
    "default_environment",
    "default_profiles",
    "default_validation",
]
