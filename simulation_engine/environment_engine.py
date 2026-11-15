"""Движок окружения: ppCO2, радиация и средовые возмущения.

Окружение моделируется независимо и влияет на физиологию через состояния
`EnvironmentState`. Радиация является накопительным процессом и не может
уменьшаться.
"""

from __future__ import annotations

import math
import random

from .config import EnvironmentConfig, ValidationConfig
from .math_utils import OUProcess, clamp
from .state import EnvironmentState


class EnvironmentEngine:
    """Обновляет состояние окружения на каждом внутреннем шаге."""

    def __init__(
        self,
        config: EnvironmentConfig,
        validation: ValidationConfig,
        rng: random.Random,
    ) -> None:
        self._config = config
        self._validation = validation
        self._rng = rng

    def update(self, state: EnvironmentState, dt: float) -> None:
        """Обновить ppCO2, радиацию и средовый стресс."""
        ppco2_target = (
            state.ppco2_target_mmhg
            if state.ppco2_target_mmhg is not None
            else self._config.baseline_ppco2_mmhg.value
        )
        ppco2_process = OUProcess(
            theta=1.0 / self._config.ppco2_tau_s.value,
            sigma=self._config.ppco2_noise_sigma.value,
        )
        state.cabin_ppco2_mmhg = clamp(
            ppco2_process.step_to(state.cabin_ppco2_mmhg, ppco2_target, dt, self._rng),
            self._validation.cabin_ppco2_mmhg,
        )

        radiation_target = (
            state.radiation_dose_rate_target_msv_h
            if state.radiation_dose_rate_target_msv_h is not None
            else self._config.baseline_radiation_dose_rate_msv_h.value
        )
        radiation_process = OUProcess(
            theta=1.0 / self._config.radiation_tau_s.value,
            sigma=self._config.radiation_noise_sigma.value,
        )
        state.radiation_dose_rate_msv_h = clamp(
            radiation_process.step_to(
                state.radiation_dose_rate_msv_h,
                radiation_target,
                dt,
                self._rng,
            ),
            self._validation.radiation_dose_rate_msv_h,
        )

        radiation_delta_msv = state.radiation_dose_rate_msv_h * dt / 3600.0
        state.daily_radiation_msv += radiation_delta_msv
        state.cumulative_radiation_msv += radiation_delta_msv
        state.daily_radiation_msv = clamp(state.daily_radiation_msv, (0.0, 1000.0))
        state.cumulative_radiation_msv = clamp(
            state.cumulative_radiation_msv,
            self._validation.cumulative_radiation_msv,
        )

        stress_target = self._config.environmental_stress_baseline.value
        state.environmental_stress += (stress_target - state.environmental_stress) * (
            1.0 - math.exp(-dt / self._config.ppco2_tau_s.value)
        )
        state.environmental_stress = clamp(state.environmental_stress, (0.0, 1.0))

    def apply_ppco2_disturbance(self, state: EnvironmentState, target_ppco2_mmhg: float) -> None:
        """Установить целевой ppCO2 при возмущении."""
        state.cabin_ppco2_mmhg = clamp(
            target_ppco2_mmhg,
            self._validation.cabin_ppco2_mmhg,
        )

    def apply_radiation_event(self, state: EnvironmentState, dose_rate_msv_h: float) -> None:
        """Установить мгновенную дозовую мощность при событии."""
        state.radiation_dose_rate_msv_h = clamp(
            dose_rate_msv_h,
            self._validation.radiation_dose_rate_msv_h,
        )

    def correct_cabin_co2(self, state: EnvironmentState) -> None:
        """Запустить коррекцию ppCO2 к номинальному уровню."""
        state.active_disturbances = [
            item for item in state.active_disturbances if item != "HYPERCAPNIC_CABIN"
        ]
        state.cabin_ppco2_mmhg = self._config.baseline_ppco2_mmhg.value

    def reset_daily_radiation(self, state: EnvironmentState) -> float:
        """Завершить сутки и вернуть накопленную суточную дозу."""
        daily = state.daily_radiation_msv
        state.daily_radiation_msv = 0.0
        return daily


__all__ = ["EnvironmentEngine"]
