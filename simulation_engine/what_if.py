"""Движок What-If экспериментов.

Эксперименты выполняются на изолированной копии состояния и не изменяют
исходную миссию. Сравнение носит исследовательский, а не клинический характер.
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from typing import Any

from .state import AstronautState, EnvironmentState


@dataclass
class WhatIfModification:
    """Конфигурация одного What-If эксперимента."""

    ared_adherence_delta: float = 0.0
    aerobic_adherence_delta: float = 0.0
    sleep_duration_delta_h: float = 0.0
    sleep_need_delta_h: float = 0.0
    ppco2_target_mmhg: float | None = None
    radiation_dose_rate_delta_msv_h: float = 0.0
    missed_ared_days: int = 0
    sleep_intervention_effectiveness: float | None = None
    scenario_id: str | None = None


@dataclass
class WhatIfResult:
    """Результат изолированного What-If эксперимента."""

    experiment_id: str
    baseline_configuration: dict[str, Any]
    modified_configuration: dict[str, Any]
    simulation_duration_seconds: int
    random_seed: int
    model_version: str
    baseline_results: dict[str, Any]
    experiment_results: dict[str, Any]
    difference_metrics: dict[str, float]
    relevant_events: list[dict[str, Any]] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Сериализовать результат эксперимента."""
        return asdict(self)


class WhatIfEngine:
    """Выполняет изолированные What-If эксперименты."""

    def __init__(self, base_controller: "SimulationController") -> None:
        self._base_controller = base_controller

    def run(
        self,
        modification: WhatIfModification,
        duration_seconds: int,
        *,
        experiment_id: str = "WHAT_IF_EXPERIMENT",
    ) -> WhatIfResult:
        """Запустить эксперимент и сравнить с исходной миссией."""
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")

        baseline_state = copy.deepcopy(self._base_controller.snapshot_state())
        from .controller import SimulationController

        experiment_controller = SimulationController(
            copy.deepcopy(self._base_controller.config),
            random_seed=self._base_controller.config.random_seed,
        )
        experiment_controller.restore_state(copy.deepcopy(baseline_state))
        experiment_controller = self._apply_modification(experiment_controller, modification)
        experiment_controller.advance(duration_seconds)

        baseline_metrics = self._extract_metrics(baseline_state)
        experiment_metrics = self._extract_metrics(experiment_controller.snapshot_state())
        differences = {
            key: experiment_metrics.get(key, 0.0) - baseline_metrics.get(key, 0.0)
            for key in sorted(set(baseline_metrics) | set(experiment_metrics))
        }

        return WhatIfResult(
            experiment_id=experiment_id,
            baseline_configuration=self._base_controller.config.model_dump(mode="json"),
            modified_configuration=experiment_controller.config.model_dump(mode="json"),
            simulation_duration_seconds=duration_seconds,
            random_seed=self._base_controller.config.random_seed,
            model_version=self._base_controller.config.model_version,
            baseline_results=baseline_metrics,
            experiment_results=experiment_metrics,
            difference_metrics=differences,
            relevant_events=[
                event.model_dump(mode="json") for event in experiment_controller.events()[-10:]
            ],
            limitations=[
                "What-If results are exploratory simulations, not clinical predictions.",
                "The experiment uses the same deterministic seed as the baseline for paired comparison.",
                "Only the modeled state variables are compared; unmodeled mission effects are ignored.",
            ],
        )

    def _apply_modification(
        self,
        controller: "SimulationController",
        modification: WhatIfModification,
    ) -> "SimulationController":
        """Применить модификации к изолированному контроллеру."""
        config = controller.config
        if modification.ppco2_target_mmhg is not None:
            controller.set_cabin_ppco2_target(modification.ppco2_target_mmhg)
        if modification.radiation_dose_rate_delta_msv_h:
            controller.add_radiation_dose_rate_delta(modification.radiation_dose_rate_delta_msv_h)
        if modification.ared_adherence_delta:
            for profile in config.profiles:
                profile.countermeasure.ared_adherence.value = max(
                    0.0,
                    profile.countermeasure.ared_adherence.value + modification.ared_adherence_delta,
                )
        if modification.aerobic_adherence_delta:
            for profile in config.profiles:
                profile.countermeasure.aerobic_adherence.value = max(
                    0.0,
                    profile.countermeasure.aerobic_adherence.value + modification.aerobic_adherence_delta,
                )
        if modification.sleep_need_delta_h:
            for profile in config.profiles:
                profile.sleep.sleep_need_h.value = max(
                    0.0,
                    profile.sleep.sleep_need_h.value + modification.sleep_need_delta_h,
                )
        if modification.sleep_intervention_effectiveness is not None:
            for profile in config.profiles:
                profile.countermeasure.sleep_intervention_effectiveness.value = max(
                    0.0,
                    modification.sleep_intervention_effectiveness,
                )
        if modification.scenario_id:
            controller.inject_scenario(modification.scenario_id)
        controller.reload_config(config)
        return controller

    def _extract_metrics(self, state: dict[str, Any]) -> dict[str, float]:
        """Извлечь ключевые метрики из состояния миссии."""
        metrics: dict[str, float] = {}
        for astronaut_id, astronaut_state in state.get("astronaut_states", {}).items():
            physiology = astronaut_state.get("physiology", {})
            for key in (
                "hr",
                "hrv_rmssd",
                "spo2",
                "pvt_mean_rt_ms",
                "pvt_slowest10_rt_ms",
                "sleep_debt_h",
                "fluid_shift_index",
                "sans_risk",
                "vo2max",
                "musculoskeletal_condition",
            ):
                metrics[f"{astronaut_id}.{key}"] = float(physiology.get(key, 0.0))
        environment = state.get("environment_state", {})
        for key in ("cabin_ppco2_mmhg", "radiation_dose_rate_msv_h", "daily_radiation_msv", "cumulative_radiation_msv"):
            metrics[f"environment.{key}"] = float(environment.get(key, 0.0))
        return metrics


__all__ = ["WhatIfEngine", "WhatIfModification", "WhatIfResult"]
