"""Каталог сценариев и движок их жизненного цикла.

Сценарии воздействуют на окружение и физиологию постепенно. Каждый сценарий
содержит документированные эффекты и период восстановления. Сценарии можно
комбинировать, если это безопасно для демонстрации.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .state import EnvironmentState, PhysiologicalState


@dataclass(frozen=True)
class ScenarioEffect:
    """Эффекты сценария на окружение и физиологию."""

    ppco2_delta_mmhg: float = 0.0
    radiation_dose_rate_delta_msv_h: float = 0.0
    stress_delta: float = 0.0
    fatigue_delta: float = 0.0
    sleep_debt_delta_h: float = 0.0
    fluid_shift_delta: float = 0.0
    iop_delta_mmhg: float = 0.0
    hr_delta_bpm: float = 0.0
    hrv_delta_ms: float = 0.0
    pvt_delta_ms: float = 0.0
    sleep_shift_active: bool = False
    missed_ared_today: bool = False


@dataclass(frozen=True)
class ScenarioDefinition:
    """Описание одного сценария."""

    scenario_id: str
    name: str
    description: str
    trigger_condition: str
    duration_seconds: int
    severity: str
    affected_systems: tuple[str, ...]
    effect: ScenarioEffect
    recovery_seconds: int
    event_timeline: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class ScenarioInstance:
    """Активный экземпляр сценария."""

    definition: ScenarioDefinition
    start_seconds: int
    elapsed_seconds: int = 0
    terminated: bool = False
    completed: bool = False

    @property
    def progress(self) -> float:
        """Прогресс сценария от 0 до 1."""
        if self.definition.duration_seconds <= 0:
            return 1.0
        return min(1.0, self.elapsed_seconds / self.definition.duration_seconds)

    @property
    def active(self) -> bool:
        """Возвращает True, пока сценарий активен."""
        return not self.terminated and not self.completed

    def current_effect(self) -> ScenarioEffect:
        """Возвращает текущий эффект сценария с плавным входом и выходом."""
        progress = self.progress
        if self.terminated:
            ramp = max(0.0, 1.0 - self.elapsed_seconds / max(self.definition.recovery_seconds, 1))
            return _scale_effect(self.definition.effect, ramp)
        if progress >= 1.0:
            self.completed = True
            return ScenarioEffect()
        ramp = min(1.0, progress * 2.0)
        return _scale_effect(self.definition.effect, ramp)


def _scale_effect(effect: ScenarioEffect, scale: float) -> ScenarioEffect:
    """Масштабировать эффект сценария."""
    return ScenarioEffect(
        ppco2_delta_mmhg=effect.ppco2_delta_mmhg * scale,
        radiation_dose_rate_delta_msv_h=effect.radiation_dose_rate_delta_msv_h * scale,
        stress_delta=effect.stress_delta * scale,
        fatigue_delta=effect.fatigue_delta * scale,
        sleep_debt_delta_h=effect.sleep_debt_delta_h * scale,
        fluid_shift_delta=effect.fluid_shift_delta * scale,
        iop_delta_mmhg=effect.iop_delta_mmhg * scale,
        hr_delta_bpm=effect.hr_delta_bpm * scale,
        hrv_delta_ms=effect.hrv_delta_ms * scale,
        pvt_delta_ms=effect.pvt_delta_ms * scale,
        sleep_shift_active=effect.sleep_shift_active,
        missed_ared_today=effect.missed_ared_today,
    )


class ScenarioEngine:
    """Управляет активными сценариями и их эффектами."""

    def __init__(self, definitions: list[ScenarioDefinition] | None = None) -> None:
        self._definitions = {definition.scenario_id: definition for definition in definitions or default_scenarios()}
        self._instances: dict[str, ScenarioInstance] = {}

    @property
    def definitions(self) -> list[ScenarioDefinition]:
        """Вернуть каталог сценариев."""
        return list(self._definitions.values())

    def start(self, scenario_id: str, start_seconds: int) -> ScenarioInstance:
        """Запустить сценарий."""
        if scenario_id not in self._definitions:
            raise KeyError(f"Unknown scenario: {scenario_id}")
        if scenario_id in self._instances:
            raise ValueError(f"Scenario already active: {scenario_id}")
        instance = ScenarioInstance(
            definition=self._definitions[scenario_id],
            start_seconds=start_seconds,
        )
        self._instances[scenario_id] = instance
        return instance

    def terminate(self, scenario_id: str) -> ScenarioInstance:
        """Досрочно завершить сценарий и запустить восстановление."""
        instance = self._instances.get(scenario_id)
        if instance is None:
            raise KeyError(f"Scenario not active: {scenario_id}")
        instance.terminated = True
        return instance

    def active_scenarios(self) -> list[ScenarioInstance]:
        """Вернуть активные сценарии."""
        return [instance for instance in self._instances.values() if instance.active]

    def update(self, dt: float) -> None:
        """Продвинуть активные сценарии по времени."""
        for instance in list(self._instances.values()):
            if instance.terminated:
                if instance.elapsed_seconds >= instance.definition.recovery_seconds:
                    del self._instances[instance.definition.scenario_id]
                else:
                    instance.elapsed_seconds += int(dt)
                continue
            instance.elapsed_seconds += int(dt)
            if instance.elapsed_seconds >= instance.definition.duration_seconds:
                instance.completed = True
                del self._instances[instance.definition.scenario_id]

    def apply_effects(
        self,
        environment: EnvironmentState,
        astronaut_states: dict[str, PhysiologicalState],
        *,
        baseline_ppco2_mmhg: float,
        baseline_radiation_dose_rate_msv_h: float,
        dt: float = 1.0,
    ) -> dict[str, ScenarioEffect]:
        """Применить эффекты активных сценариев к окружению и астронавтам."""
        applied: dict[str, ScenarioEffect] = {}
        for instance in self.active_scenarios():
            effect = instance.current_effect()
            applied[instance.definition.scenario_id] = effect
            if effect.ppco2_delta_mmhg:
                environment.ppco2_target_mmhg = baseline_ppco2_mmhg + effect.ppco2_delta_mmhg
            else:
                environment.ppco2_target_mmhg = None
            if effect.radiation_dose_rate_delta_msv_h:
                environment.radiation_dose_rate_target_msv_h = (
                    baseline_radiation_dose_rate_msv_h + effect.radiation_dose_rate_delta_msv_h
                )
            else:
                environment.radiation_dose_rate_target_msv_h = None
            if effect.sleep_shift_active:
                for state in astronaut_states.values():
                    state.sleep_shift_active = True
            duration = max(instance.definition.duration_seconds, 1)
            for astronaut_id, state in astronaut_states.items():
                state.stress = max(0.0, state.stress + effect.stress_delta * dt / duration)
                state.fatigue = max(0.0, state.fatigue + effect.fatigue_delta * dt / duration)
                state.sleep_debt_h = max(0.0, state.sleep_debt_h + effect.sleep_debt_delta_h * dt / duration)
                state.fluid_shift_index = max(0.0, state.fluid_shift_index + effect.fluid_shift_delta * dt / duration)
                state.iop_mmhg = max(0.0, state.iop_mmhg + effect.iop_delta_mmhg * dt / duration)
                state.hr = max(20.0, state.hr + effect.hr_delta_bpm * dt / duration)
                state.hrv_rmssd = max(0.0, state.hrv_rmssd + effect.hrv_delta_ms * dt / duration)
                state.pvt_mean_rt_ms = max(100.0, state.pvt_mean_rt_ms + effect.pvt_delta_ms * dt / duration)
                state.pvt_slowest10_rt_ms = max(
                    100.0,
                    state.pvt_slowest10_rt_ms + effect.pvt_delta_ms * 1.2 * dt / duration,
                )
        return applied

    def export_state(self) -> dict[str, Any]:
        """Сериализовать состояние сценарного движка."""
        return {
            "active": [
                {
                    "scenario_id": instance.definition.scenario_id,
                    "start_seconds": instance.start_seconds,
                    "elapsed_seconds": instance.elapsed_seconds,
                    "terminated": instance.terminated,
                    "completed": instance.completed,
                }
                for instance in self._instances.values()
            ],
        }


def default_scenarios() -> list[ScenarioDefinition]:
    """Вернуть четыре обязательных сценария и дополнительные."""
    return [
        ScenarioDefinition(
            scenario_id="HYPERCAPNIC_CABIN",
            name="Hypercapnic Cabin",
            description="Cabin CO2 rises gradually due to environmental control malfunction.",
            trigger_condition="Manual injection or environmental equipment fault.",
            duration_seconds=1800,
            severity="HIGH",
            affected_systems=("RESPIRATORY_ENV", "NEURO_BEHAVIORAL", "CARDIOVASCULAR"),
            effect=ScenarioEffect(
                ppco2_delta_mmhg=2.2,
                stress_delta=0.25,
                fatigue_delta=0.10,
                hr_delta_bpm=6.0,
                hrv_delta_ms=-8.0,
                pvt_delta_ms=45.0,
            ),
            recovery_seconds=900,
            event_timeline=(
                "CO2 begins rising",
                "Respiratory and cardiovascular response increases",
                "Cognitive performance degrades",
                "Environmental correction triggers recovery",
            ),
        ),
        ScenarioDefinition(
            scenario_id="NEUROCOGNITIVE_FATIGUE",
            name="Neurocognitive and Fatigue Anomaly",
            description="Sleep deprivation and circadian misalignment degrade cognitive performance.",
            trigger_condition="Manual injection or schedule disruption.",
            duration_seconds=86400,
            severity="HIGH",
            affected_systems=("NEURO_BEHAVIORAL", "ENDOCRINE_METABOLIC"),
            effect=ScenarioEffect(
                stress_delta=0.30,
                fatigue_delta=0.45,
                sleep_debt_delta_h=2.5,
                pvt_delta_ms=75.0,
                sleep_shift_active=True,
            ),
            recovery_seconds=86400,
            event_timeline=(
                "Sleep opportunity is reduced",
                "Circadian misalignment increases",
                "PVT performance degrades",
                "Sleep intervention begins recovery",
            ),
        ),
        ScenarioDefinition(
            scenario_id="SANS_FLUID_SHIFT",
            name="SANS / Fluid Shift",
            description="Gradual cephalad fluid redistribution increases SANS-related indicators.",
            trigger_condition="Manual injection or prolonged microgravity exposure.",
            duration_seconds=432000,
            severity="MODERATE",
            affected_systems=("NEURO_OCULAR_SANS", "CARDIOVASCULAR"),
            effect=ScenarioEffect(
                fluid_shift_delta=0.8,
                iop_delta_mmhg=3.5,
                stress_delta=0.15,
            ),
            recovery_seconds=259200,
            event_timeline=(
                "Fluid shift begins",
                "Ocular pressure indicators rise",
                "SANS-related risk increases",
                "Countermeasure support begins recovery",
            ),
        ),
        ScenarioDefinition(
            scenario_id="SOLAR_PARTICLE_EVENT",
            name="Solar Particle Event",
            description="Transient rise in radiation dose rate with daily and cumulative dose accumulation.",
            trigger_condition="Manual injection or mission radiation event.",
            duration_seconds=7200,
            severity="CRITICAL",
            affected_systems=("IMMUNE_MUSCULOSKELETAL", "ENDOCRINE_METABOLIC"),
            effect=ScenarioEffect(
                radiation_dose_rate_delta_msv_h=1.05,
                stress_delta=0.35,
                fatigue_delta=0.15,
            ),
            recovery_seconds=7200,
            event_timeline=(
                "Dose rate rises",
                "Daily dose accumulates",
                "Mission cumulative dose increases",
                "Event decays and exposure tracking continues",
            ),
        ),
        ScenarioDefinition(
            scenario_id="MISSED_ARED",
            name="Missed ARED Schedule",
            description="ARED sessions are missed, accelerating deconditioning.",
            trigger_condition="Manual injection or schedule conflict.",
            duration_seconds=604800,
            severity="MODERATE",
            affected_systems=("IMMUNE_MUSCULOSKELETAL", "CARDIOVASCULAR"),
            effect=ScenarioEffect(
                fatigue_delta=0.10,
                missed_ared_today=True,
            ),
            recovery_seconds=259200,
            event_timeline=(
                "ARED sessions are missed",
                "Musculoskeletal deconditioning increases",
                "Aerobic countermeasure can partially compensate",
            ),
        ),
        ScenarioDefinition(
            scenario_id="ENVIRONMENTAL_EQUIPMENT_MALFUNCTION",
            name="Environmental Equipment Malfunction",
            description="Cabin environmental control becomes less effective.",
            trigger_condition="Manual injection or equipment fault.",
            duration_seconds=3600,
            severity="HIGH",
            affected_systems=("RESPIRATORY_ENV", "NEURO_BEHAVIORAL"),
            effect=ScenarioEffect(
                ppco2_delta_mmhg=1.2,
                stress_delta=0.20,
            ),
            recovery_seconds=1800,
            event_timeline=(
                "Environmental control degrades",
                "Cabin stress rises",
                "Corrective action triggers recovery",
            ),
        ),
    ]


__all__ = [
    "ScenarioDefinition",
    "ScenarioEffect",
    "ScenarioEngine",
    "ScenarioInstance",
    "default_scenarios",
]
