"""Внутренние состояния симуляции.

Эти структуры не являются клиническими контрактами; они используются
движком для расчёта динамики. Сериализация в общие контракты выполняется
в telemetry.py.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class EnvironmentState:
    """Состояние кабины и радиационного окружения."""

    cabin_ppco2_mmhg: float = 2.35
    radiation_dose_rate_msv_h: float = 0.020
    daily_radiation_msv: float = 0.0
    cumulative_radiation_msv: float = 0.0
    microgravity_exposure: float = 1.0
    environmental_stress: float = 0.10
    exercise_load: float = 0.0
    active_disturbances: list[str] = field(default_factory=list)
    ppco2_target_mmhg: float | None = None
    radiation_dose_rate_target_msv_h: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Сериализовать состояние в словарь."""
        return asdict(self)


@dataclass
class CountermeasureState:
    """Состояние контрмер и восстановительных процессов."""

    ared_completed_today: bool = False
    aerobic_completed_today: bool = False
    ared_sessions_completed: int = 0
    aerobic_sessions_completed: int = 0
    missed_ared_days: int = 0
    exercise_load: float = 0.0
    recovery_state: float = 1.0
    sleep_intervention_active: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Сериализовать состояние в словарь."""
        return asdict(self)


@dataclass
class PhysiologicalState:
    """Состояние физиологии и адаптации одного астронавта."""

    hr: float = 70.0
    hrv_rmssd: float = 45.0
    sbp: float = 117.0
    dbp: float = 73.0
    spo2: float = 98.0
    resp_rate: float = 14.0
    temp_c: float = 36.55

    pvt_mean_rt_ms: float = 240.0
    pvt_slowest10_rt_ms: float = 295.0
    pvt_lapses_count: int = 0

    fatigue: float = 0.1
    stress: float = 0.1
    mood_stress_vas: float = 10.0
    sleep_debt_h: float = 0.0
    sleep_duration_h: float = 7.5
    sleep_efficiency_pct: float = 90.0
    sleep_shift_active: bool = False
    circadian_misalignment: float = 0.0

    fluid_shift_index: float = 0.2
    sans_risk: float = 0.05
    iop_mmhg: float = 16.0

    cardiovascular_adaptation: float = 0.0
    musculoskeletal_condition: float = 1.0
    vo2max: float = 43.0

    respiratory_exchange_ratio: float = 0.95

    def to_dict(self) -> dict[str, Any]:
        """Сериализовать состояние в словарь."""
        return asdict(self)


@dataclass
class AstronautState:
    """Полное состояние одного астронавта."""

    astronaut_id: str
    physiology: PhysiologicalState = field(default_factory=PhysiologicalState)
    countermeasure: CountermeasureState = field(default_factory=CountermeasureState)
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Сериализовать состояние в словарь."""
        return {
            "astronaut_id": self.astronaut_id,
            "physiology": self.physiology.to_dict(),
            "countermeasure": self.countermeasure.to_dict(),
            "history": self.history[-100:],
        }
