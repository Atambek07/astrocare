"""Связанная физиологическая модель гибридной симуляции.

Модель использует целевую релаксацию, OU-шум и медленную адаптацию. Все
связи являются документированными инженерными допущениями, а не клиническими
законами. Никакие значения не выдаются за NASA-измерения.
"""

from __future__ import annotations

import math
import random

from .config import ParameterProfile, ValidationConfig
from .math_utils import OUProcess, clamp, exponential_relaxation
from .profiles import default_validation
from .state import CountermeasureState, EnvironmentState, PhysiologicalState


class PhysiologyEngine:
    """Обновляет физиологическое состояние одного астронавта."""

    def __init__(
        self,
        profile: ParameterProfile,
        validation: ValidationConfig,
        rng: random.Random,
    ) -> None:
        self._profile = profile
        self._validation = validation
        self._rng = rng

    def _co2_excess(self, environment: EnvironmentState) -> float:
        """Превышение ppCO2 над номинальным уровнем."""
        return max(0.0, environment.cabin_ppco2_mmhg - self._environment_baseline_ppco2())

    def _environment_baseline_ppco2(self) -> float:
        """Номинальное значение ppCO2 из окружения."""
        return 2.35

    def update_fast(self, state: PhysiologicalState, environment: EnvironmentState, dt: float) -> None:
        """Обновить быстрые физиологические переменные."""
        co2_excess = self._co2_excess(environment)
        cardio = self._profile.cardiovascular
        respiratory = self._profile.respiratory
        cognitive = self._profile.cognitive
        stochastic = self._profile.stochastic

        target_hr = (
            cardio.baseline_hr.value
            + state.stress * cardio.stress_hr_gain.value
            + co2_excess * cardio.co2_hr_gain.value
            + environment.exercise_load * cardio.exercise_hr_gain.value
            + state.fatigue * 2.0
            + state.fluid_shift_index * 0.5
        )
        target_hrv = (
            cardio.baseline_hrv_rmssd.value
            - state.stress * cardio.stress_hrv_loss.value
            - co2_excess * cardio.co2_hrv_loss.value
            - state.fatigue * 5.0
            - state.fluid_shift_index * 1.0
            + state.cardiovascular_adaptation * 2.0
        )
        target_sbp = cardio.baseline_sbp.value + state.stress * 3.0 + environment.exercise_load * 10.0 + state.fluid_shift_index * 1.0
        target_dbp = cardio.baseline_dbp.value + state.stress * 2.0 + environment.exercise_load * 5.0 + state.fluid_shift_index * 0.5
        target_spo2 = (
            respiratory.baseline_spo2.value
            - co2_excess * respiratory.co2_spo2_loss.value
            - state.fatigue * 0.2
        )
        target_resp_rate = (
            respiratory.baseline_resp_rate.value
            + co2_excess * respiratory.co2_resp_gain.value
            + environment.exercise_load * 3.0
        )
        target_temp = respiratory.baseline_temp_c.value + environment.exercise_load * 0.05 - state.fatigue * 0.05
        target_pvt_mean = (
            cognitive.baseline_pvt_mean_rt_ms.value
            + state.fatigue * cognitive.fatigue_pvt_gain.value
            + state.stress * cognitive.stress_pvt_gain.value
            + co2_excess * cognitive.co2_pvt_gain.value
        )
        target_pvt_slowest = (
            cognitive.baseline_pvt_slowest10_rt_ms.value
            + state.fatigue * cognitive.fatigue_pvt_gain.value * 1.3
            + state.stress * cognitive.stress_pvt_gain.value
            + co2_excess * cognitive.co2_pvt_gain.value * 1.2
        )

        state.hr = exponential_relaxation(state.hr, target_hr, cardio.hr_tau_s.value, dt)
        state.hrv_rmssd = exponential_relaxation(state.hrv_rmssd, target_hrv, cardio.hrv_tau_s.value, dt)
        state.sbp = exponential_relaxation(state.sbp, target_sbp, cardio.hr_tau_s.value, dt)
        state.dbp = exponential_relaxation(state.dbp, target_dbp, cardio.hr_tau_s.value, dt)
        state.spo2 = exponential_relaxation(state.spo2, target_spo2, respiratory.resp_rate_tau_s.value, dt)
        state.resp_rate = exponential_relaxation(state.resp_rate, target_resp_rate, respiratory.resp_rate_tau_s.value, dt)
        state.temp_c = exponential_relaxation(state.temp_c, target_temp, respiratory.temp_tau_s.value, dt)
        state.pvt_mean_rt_ms = exponential_relaxation(state.pvt_mean_rt_ms, target_pvt_mean, cognitive.pvt_tau_s.value, dt)
        state.pvt_slowest10_rt_ms = exponential_relaxation(
            state.pvt_slowest10_rt_ms, target_pvt_slowest, cognitive.pvt_tau_s.value, dt
        )

        self._apply_noise(state, dt)

    def _apply_noise(self, state: PhysiologicalState, dt: float) -> None:
        """Применить OU-шум к физиологическим сигналам."""
        stochastic = self._profile.stochastic
        process = OUProcess(theta=stochastic.ou_mean_reversion.value, sigma=1.0)
        scale = stochastic.individual_variability_scale.value
        state.hr += process.step(0.0, dt, self._rng) * stochastic.hr_noise_sigma.value * scale
        state.hrv_rmssd += process.step(0.0, dt, self._rng) * stochastic.hrv_noise_sigma.value * scale
        state.spo2 += process.step(0.0, dt, self._rng) * stochastic.spo2_noise_sigma.value * scale
        state.temp_c += process.step(0.0, dt, self._rng) * stochastic.temp_noise_sigma.value * scale
        state.resp_rate += process.step(0.0, dt, self._rng) * stochastic.resp_rate_noise_sigma.value * scale
        state.pvt_mean_rt_ms += process.step(0.0, dt, self._rng) * stochastic.pvt_noise_sigma.value * scale
        state.pvt_slowest10_rt_ms += process.step(0.0, dt, self._rng) * stochastic.pvt_noise_sigma.value * scale * 1.2

    def update_slow(self, state: PhysiologicalState, environment: EnvironmentState, dt: float) -> None:
        """Обновить усталость, адаптацию, флюидный сдвиг и SANS-риск."""
        adaptation = self._profile.adaptation
        days_to_seconds = 86400.0

        stress_target = clamp(environment.environmental_stress + state.fatigue * 0.2, (0.0, 1.0))
        state.stress = exponential_relaxation(state.stress, stress_target, 600.0, dt)
        state.fatigue = exponential_relaxation(
            state.fatigue,
            clamp(state.sleep_debt_h * 0.08 + state.stress * 0.2 + environment.environmental_stress * 0.2, (0.0, 1.0)),
            900.0,
            dt,
        )
        state.mood_stress_vas = clamp(state.stress * 80.0 + state.fatigue * 20.0, (0.0, 100.0))

        state.cardiovascular_adaptation = exponential_relaxation(
            state.cardiovascular_adaptation,
            clamp(environment.microgravity_exposure, (0.0, 1.0)),
            adaptation.microgravity_cardio_adaptation_tau_days.value * days_to_seconds,
            dt,
        )
        state.fluid_shift_index = exponential_relaxation(
            state.fluid_shift_index,
            clamp(
                adaptation.fluid_shift_max_index.value * environment.microgravity_exposure,
                self._validation.fluid_shift_index,
            ),
            adaptation.microgravity_fluid_shift_tau_days.value * days_to_seconds,
            dt,
        )
        state.iop_mmhg = exponential_relaxation(
            state.iop_mmhg,
            clamp(
                adaptation.baseline_iop_mmhg.value
                + state.fluid_shift_index * adaptation.iop_fluid_shift_gain.value,
                self._validation.iop_mmhg,
            ),
            3600.0,
            dt,
        )

        fluid_term = state.fluid_shift_index * adaptation.sans_risk_gain_fluid_shift.value
        iop_term = max(0.0, state.iop_mmhg - 20.0) * adaptation.sans_risk_gain_iop.value
        state.sans_risk = clamp(1.0 / (1.0 + math.exp(-(fluid_term + iop_term - 1.0))), self._validation.probability)

        state.musculoskeletal_condition = exponential_relaxation(
            state.musculoskeletal_condition,
            clamp(1.0 - 0.25 * environment.microgravity_exposure, (0.0, 1.0)),
            adaptation.musculoskeletal_tau_days.value * days_to_seconds,
            dt,
        )

        # ПТВ-лапсы зависят от усталости и сна, но не используются как диагноз.
        lapse_probability = clamp(state.fatigue * 0.35 + state.sleep_debt_h * 0.03, (0.0, 1.0))
        if self._rng.random() < lapse_probability * dt / 60.0:
            state.pvt_lapses_count = min(100, state.pvt_lapses_count + 1)

    def daily_update(
        self,
        state: PhysiologicalState,
        countermeasure: CountermeasureState,
        environment: EnvironmentState,
    ) -> None:
        """Обновить суточные сон, усталость и когнитивные метрики."""
        sleep = self._profile.sleep
        sleep_need = sleep.sleep_need_h.value
        sleep_penalty = (
            state.stress * sleep.stress_sleep_penalty.value
            + environment.environmental_stress * sleep.environment_sleep_penalty.value
        )
        if countermeasure.sleep_intervention_active:
            sleep_penalty *= 1.0 - self._profile.countermeasure.sleep_intervention_effectiveness.value

        sleep_duration = clamp(
            sleep_need
            - sleep_penalty
            + sleep.sleep_duration_delta_h.value
            + self._rng.gauss(0.0, 0.35),
            (0.0, 24.0),
        )
        sleep_efficiency = clamp(
            sleep.baseline_sleep_efficiency_pct.value
            - state.stress * 4.0
            - environment.environmental_stress * 2.0
            + countermeasure.sleep_intervention_active * 3.0
            + self._rng.gauss(0.0, 1.2),
            (0.0, 100.0),
        )
        state.sleep_duration_h = sleep_duration
        state.sleep_efficiency_pct = sleep_efficiency
        state.sleep_debt_h = max(0.0, state.sleep_debt_h + sleep_need - sleep_duration)
        state.circadian_misalignment = clamp(
            state.circadian_misalignment * (1.0 - sleep.circadian_recovery_rate.value)
            + sleep_penalty * 0.1,
            (0.0, 1.0),
        )

        cognitive = self._profile.cognitive
        target_mean = (
            cognitive.baseline_pvt_mean_rt_ms.value
            + state.sleep_debt_h * 6.0
            + state.fatigue * cognitive.fatigue_pvt_gain.value
            + state.stress * cognitive.stress_pvt_gain.value
        )
        target_slowest = (
            cognitive.baseline_pvt_slowest10_rt_ms.value
            + state.sleep_debt_h * 8.0
            + state.fatigue * cognitive.fatigue_pvt_gain.value * 1.3
            + state.stress * cognitive.stress_pvt_gain.value
        )
        state.pvt_mean_rt_ms = clamp(target_mean, self._validation.pvt_mean_rt_ms)
        state.pvt_slowest10_rt_ms = clamp(target_slowest, self._validation.pvt_slowest10_rt_ms)
        state.pvt_lapses_count = int(
            clamp(state.sleep_debt_h * 1.5 + state.fatigue * 8.0, (0.0, 100.0))
        )

    def clamp_to_validation(self, state: PhysiologicalState) -> None:
        """Привести состояния к допустимым границам."""
        state.hr = clamp(state.hr, self._validation.hr_bpm)
        state.hrv_rmssd = clamp(state.hrv_rmssd, self._validation.hrv_rmssd_ms)
        state.sbp = clamp(state.sbp, self._validation.sbp_mmhg)
        state.dbp = clamp(state.dbp, self._validation.dbp_mmhg)
        state.spo2 = clamp(state.spo2, self._validation.spo2_pct)
        state.resp_rate = clamp(state.resp_rate, self._validation.resp_rate_per_min)
        state.temp_c = clamp(state.temp_c, self._validation.temp_c)
        state.pvt_mean_rt_ms = clamp(state.pvt_mean_rt_ms, self._validation.pvt_mean_rt_ms)
        state.pvt_slowest10_rt_ms = clamp(state.pvt_slowest10_rt_ms, self._validation.pvt_slowest10_rt_ms)
        state.iop_mmhg = clamp(state.iop_mmhg, self._validation.iop_mmhg)
        state.sans_risk = clamp(state.sans_risk, self._validation.probability)
        state.fluid_shift_index = clamp(state.fluid_shift_index, self._validation.fluid_shift_index)
        state.vo2max = clamp(state.vo2max, self._validation.vo2max_ml_kg_min)
        state.stress = clamp(state.stress, self._validation.probability)
        state.fatigue = clamp(state.fatigue, self._validation.probability)
        state.circadian_misalignment = clamp(state.circadian_misalignment, self._validation.probability)


__all__ = ["PhysiologyEngine"]
