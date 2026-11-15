"""Параметры и конфигурация гибридного симулятора.

Все ключевые коэффициенты описаны через `Coefficient`, чтобы сохранить единицы,
источник/обоснование и уровень доказательности. Это не клинические нормы:
значения помечаются как NASA evidence, derived parameter, model assumption
или synthetic demonstration parameter.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EvidenceLevel(str, Enum):
    """Классификация происхождения параметра симуляции."""

    NASA_MEASURED = "NASA_MEASURED"
    PUBLISHED_SCIENTIFIC = "PUBLISHED_SCIENTIFIC"
    DERIVED_PARAMETER = "DERIVED_PARAMETER"
    MODEL_ASSUMPTION = "MODEL_ASSUMPTION"
    SYNTHETIC_DEMONSTRATION = "SYNTHETIC_DEMONSTRATION"


class Coefficient(BaseModel):
    """Один коэффициент модели с полной документацией."""

    model_config = ConfigDict(extra="forbid")

    name: str
    value: float
    unit: str
    description: str
    source: str
    evidence_level: EvidenceLevel
    adjustable: bool = True


def coefficient(
    name: str,
    value: float,
    unit: str,
    description: str,
    source: str,
    evidence_level: EvidenceLevel,
    *,
    adjustable: bool = True,
) -> Coefficient:
    """Создать документированный коэффициент."""
    return Coefficient(
        name=name,
        value=value,
        unit=unit,
        description=description,
        source=source,
        evidence_level=evidence_level,
        adjustable=adjustable,
    )


class CardiovascularParameters(BaseModel):
    """Кардиоваскулярные параметры отдельного астронавта."""

    model_config = ConfigDict(extra="forbid")

    baseline_hr: Coefficient
    baseline_hrv_rmssd: Coefficient
    baseline_sbp: Coefficient
    baseline_dbp: Coefficient
    stress_hr_gain: Coefficient
    stress_hrv_loss: Coefficient
    co2_hr_gain: Coefficient
    co2_hrv_loss: Coefficient
    exercise_hr_gain: Coefficient
    hr_tau_s: Coefficient
    hrv_tau_s: Coefficient


class RespiratoryParameters(BaseModel):
    """Респираторные и терморегуляторные параметры."""

    model_config = ConfigDict(extra="forbid")

    baseline_spo2: Coefficient
    baseline_resp_rate: Coefficient
    baseline_temp_c: Coefficient
    co2_resp_gain: Coefficient
    co2_spo2_loss: Coefficient
    resp_rate_tau_s: Coefficient
    temp_tau_s: Coefficient


class CognitiveParameters(BaseModel):
    """Когнитивные параметры и реакция на нагрузку."""

    model_config = ConfigDict(extra="forbid")

    baseline_pvt_mean_rt_ms: Coefficient
    baseline_pvt_slowest10_rt_ms: Coefficient
    fatigue_pvt_gain: Coefficient
    stress_pvt_gain: Coefficient
    co2_pvt_gain: Coefficient
    pvt_tau_s: Coefficient


class SleepParameters(BaseModel):
    """Сон, циркадный ритм и накопление долгов сна."""

    model_config = ConfigDict(extra="forbid")

    sleep_need_h: Coefficient
    baseline_sleep_efficiency_pct: Coefficient
    circadian_recovery_rate: Coefficient
    sleep_debt_decay_rate: Coefficient
    stress_sleep_penalty: Coefficient
    environment_sleep_penalty: Coefficient
    sleep_duration_delta_h: Coefficient


class AdaptationParameters(BaseModel):
    """Долгосрочная адаптация к микрогравитации."""

    model_config = ConfigDict(extra="forbid")

    microgravity_cardio_adaptation_tau_days: Coefficient
    microgravity_fluid_shift_tau_days: Coefficient
    musculoskeletal_tau_days: Coefficient
    vo2max_training_gain: Coefficient
    vo2max_detraining_rate: Coefficient
    fluid_shift_max_index: Coefficient
    baseline_iop_mmhg: Coefficient
    iop_fluid_shift_gain: Coefficient
    sans_risk_gain_fluid_shift: Coefficient
    sans_risk_gain_iop: Coefficient
    radiation_biological_sensitivity: Coefficient


class CountermeasureParameters(BaseModel):
    """Индивидуальная реакция на контрмеры."""

    model_config = ConfigDict(extra="forbid")

    ared_adherence: Coefficient
    aerobic_adherence: Coefficient
    ared_minutes_per_session: Coefficient
    aerobic_minutes_per_session: Coefficient
    ared_musculoskeletal_gain: Coefficient
    aerobic_vo2max_gain: Coefficient
    recovery_rate: Coefficient
    sleep_intervention_effectiveness: Coefficient


class StochasticParameters(BaseModel):
    """Параметры контролируемого шума и индивидуальной вариабельности."""

    model_config = ConfigDict(extra="forbid")

    hr_noise_sigma: Coefficient
    hrv_noise_sigma: Coefficient
    spo2_noise_sigma: Coefficient
    temp_noise_sigma: Coefficient
    resp_rate_noise_sigma: Coefficient
    pvt_noise_sigma: Coefficient
    ou_mean_reversion: Coefficient
    individual_variability_scale: Coefficient


class ParameterProfile(BaseModel):
    """Полный индивидуальный профиль астронавта."""

    model_config = ConfigDict(extra="forbid")

    astronaut_id: str = Field(..., min_length=1)
    display_name: str
    role: str
    is_control: bool = False
    cardiovascular: CardiovascularParameters
    respiratory: RespiratoryParameters
    cognitive: CognitiveParameters
    sleep: SleepParameters
    adaptation: AdaptationParameters
    countermeasure: CountermeasureParameters
    stochastic: StochasticParameters


class EnvironmentConfig(BaseModel):
    """Конфигурация кабины и радиационного фона."""

    model_config = ConfigDict(extra="forbid")

    baseline_ppco2_mmhg: Coefficient
    ppco2_noise_sigma: Coefficient
    ppco2_tau_s: Coefficient
    baseline_radiation_dose_rate_msv_h: Coefficient
    radiation_noise_sigma: Coefficient
    radiation_tau_s: Coefficient
    microgravity_exposure: Coefficient
    environmental_stress_baseline: Coefficient
    co2_correction_tau_s: Coefficient
    radiation_event_decay_tau_s: Coefficient


class NumericalConfig(BaseModel):
    """Настройки численного интегрирования и вывода."""

    model_config = ConfigDict(extra="forbid")

    integrator: Literal["euler", "rk4"] = "euler"
    internal_step_seconds: float = Field(default=1.0, gt=0.0)
    output_step_seconds: float = Field(default=1.0, gt=0.0)
    max_output_records_per_astronaut: int = Field(default=200000, ge=1)
    clamp_states: bool = True
    stability_epsilon: float = Field(default=1e-9, gt=0.0)


class ValidationConfig(BaseModel):
    """Физиологические и численные границы состояний."""

    model_config = ConfigDict(extra="forbid")

    hr_bpm: tuple[float, float] = (20.0, 250.0)
    hrv_rmssd_ms: tuple[float, float] = (0.0, 300.0)
    sbp_mmhg: tuple[float, float] = (50.0, 260.0)
    dbp_mmhg: tuple[float, float] = (20.0, 160.0)
    spo2_pct: tuple[float, float] = (50.0, 100.0)
    resp_rate_per_min: tuple[float, float] = (4.0, 60.0)
    temp_c: tuple[float, float] = (30.0, 45.0)
    pvt_mean_rt_ms: tuple[float, float] = (100.0, 2000.0)
    pvt_slowest10_rt_ms: tuple[float, float] = (100.0, 1000.0)
    iop_mmhg: tuple[float, float] = (0.0, 60.0)
    cabin_ppco2_mmhg: tuple[float, float] = (0.0, 20.0)
    radiation_dose_rate_msv_h: tuple[float, float] = (0.0, 1000.0)
    fluid_shift_index: tuple[float, float] = (0.0, 3.0)
    probability: tuple[float, float] = (0.0, 1.0)
    vo2max_ml_kg_min: tuple[float, float] = (0.0, 100.0)
    cumulative_radiation_msv: tuple[float, float] = (0.0, 5000.0)


class MissionConfig(BaseModel):
    """Параметры миссии и экипажа."""

    model_config = ConfigDict(extra="forbid")

    mission_id: str = Field(..., min_length=1)
    mission_name: str
    start_utc: str = Field(..., description="ISO-8601 UTC, e.g. 2026-04-22T08:00:00Z")
    planned_duration_days: int = Field(default=180, ge=1, le=3650)
    phase_1_end_day: int = Field(default=14, ge=1)
    phase_2_start_day: int = Field(default=15, ge=2)
    source_type: Literal["SYNTHETIC"] = "SYNTHETIC"


class SimulationConfig(BaseModel):
    """Полная конфигурация гибридной симуляции."""

    model_config = ConfigDict(extra="forbid")

    simulation_engine_version: str = "astralis-simulation-1.0.0"
    model_version: str = "astralis-hybrid-physiology-1.0.0"
    random_seed: int = Field(default=20260501, ge=0)
    mission: MissionConfig
    environment: EnvironmentConfig
    numerical: NumericalConfig
    validation: ValidationConfig
    profiles: list[ParameterProfile] = Field(..., min_length=1)
    scenario_catalog_path: str | None = None
    export_directory: str = "simulation_exports"
    checkpoint_directory: str = "simulation_checkpoints"
