"""Движок контрмер: ARED, аэробная нагрузка, сон и восстановление.

Контрмеры влияют на те же состояния, которые использует физиология.
Эффекты отложенные и частичные; отсутствует мгновенное полное восстановление.
"""

from __future__ import annotations

import random
from typing import Literal

from .config import ParameterProfile
from .state import CountermeasureState, EnvironmentState, PhysiologicalState

CountermeasureType = Literal["ARED", "AEROBIC_EXERCISE", "SLEEP_INTERVENTION", "ENVIRONMENTAL_CORRECTION"]


class CountermeasureEngine:
    """Управляет суточными и мгновенными контрмерами."""

    def __init__(self, profile: ParameterProfile) -> None:
        self._profile = profile

    def schedule_daily(
        self,
        countermeasure: CountermeasureState,
        rng: random.Random,
        *,
        missed_ared_scenario_active: bool = False,
    ) -> None:
        """Определить выполнение ARED и аэробной нагрузки на сутки."""
        countermeasure.exercise_load = 0.0
        countermeasure.ared_completed_today = (
            not missed_ared_scenario_active
            and rng.random() < self._profile.countermeasure.ared_adherence.value
        )
        countermeasure.aerobic_completed_today = (
            rng.random() < self._profile.countermeasure.aerobic_adherence.value
        )
        if countermeasure.ared_completed_today:
            countermeasure.ared_sessions_completed += 1
        else:
            countermeasure.missed_ared_days += 1
        if countermeasure.aerobic_completed_today:
            countermeasure.aerobic_sessions_completed += 1
        countermeasure.exercise_load = (
            (0.7 if countermeasure.ared_completed_today else 0.0)
            + (0.5 if countermeasure.aerobic_completed_today else 0.0)
        )

    def apply_countermeasure(
        self,
        state: PhysiologicalState,
        countermeasure: CountermeasureState,
        countermeasure_type: CountermeasureType,
        *,
        effectiveness: float = 1.0,
    ) -> None:
        """Применить контрмеру к текущему состоянию."""
        params = self._profile.countermeasure
        if countermeasure_type == "ARED":
            state.musculoskeletal_condition += params.ared_musculoskeletal_gain.value * effectiveness
            state.vo2max += params.aerobic_vo2max_gain.value * 0.35 * effectiveness
            countermeasure.ared_completed_today = True
            countermeasure.ared_sessions_completed += 1
            countermeasure.exercise_load += 0.7
        elif countermeasure_type == "AEROBIC_EXERCISE":
            state.vo2max += params.aerobic_vo2max_gain.value * effectiveness
            countermeasure.aerobic_completed_today = True
            countermeasure.aerobic_sessions_completed += 1
            countermeasure.exercise_load += 0.5
        elif countermeasure_type == "SLEEP_INTERVENTION":
            countermeasure.sleep_intervention_active = True
            state.sleep_debt_h = max(
                0.0,
                state.sleep_debt_h - params.sleep_intervention_effectiveness.value * 1.5,
            )
        elif countermeasure_type == "ENVIRONMENTAL_CORRECTION":
            state.stress = max(0.0, state.stress - 0.15 * effectiveness)
            state.fatigue = max(0.0, state.fatigue - 0.05 * effectiveness)

    def update_daily(
        self,
        state: PhysiologicalState,
        countermeasure: CountermeasureState,
        environment: EnvironmentState,
    ) -> None:
        """Обновить долгосрочные эффекты контрмер за сутки."""
        params = self._profile.countermeasure

        if countermeasure.ared_completed_today:
            state.musculoskeletal_condition = min(
                1.0,
                state.musculoskeletal_condition + params.ared_musculoskeletal_gain.value,
            )

        if countermeasure.aerobic_completed_today:
            state.vo2max += params.aerobic_vo2max_gain.value

        countermeasure.recovery_state = min(
            1.0,
            countermeasure.recovery_state + params.recovery_rate.value * (0.5 + countermeasure.exercise_load),
        )
        countermeasure.sleep_intervention_active = False


__all__ = ["CountermeasureEngine"]
