"""Контроллер гибридной симуляции.

Контроллер координирует часы, окружение, физиологию, контрмеры, сценарии,
What-If эксперименты, телеметрию и контрольные точки. Он не реализует
API, MFI, IMPACT или детекторы — эти зоны принадлежат Backend Agent.
"""

from __future__ import annotations

import copy
import json
import random
from pathlib import Path
from typing import Any, Iterator

from .clock import MissionClock
from .config import SimulationConfig
from .countermeasure_engine import CountermeasureEngine
from .environment_engine import EnvironmentEngine
from .events import SimulationEvent, SimulationStatus
from .profiles import default_environment, default_profiles, default_validation
from .scenarios import ScenarioEngine
from .state import AstronautState, CountermeasureState, EnvironmentState, PhysiologicalState
from .telemetry import to_daily_log, to_stream_tick
from .what_if import WhatIfEngine, WhatIfModification, WhatIfResult


class SimulationController:
    """Основной интерфейс управления гибридной симуляцией."""

    def __init__(
        self,
        config: SimulationConfig | None = None,
        *,
        random_seed: int | None = None,
    ) -> None:
        self._config = config or self._default_config()
        seed = random_seed if random_seed is not None else self._config.random_seed
        self._config.random_seed = seed
        self._clock = MissionClock(
            start_utc=self._parse_utc(self._config.mission.start_utc),
            phase_1_end_day=self._config.mission.phase_1_end_day,
            phase_2_start_day=self._config.mission.phase_2_start_day,
        )
        self._environment = EnvironmentState(
            cabin_ppco2_mmhg=self._config.environment.baseline_ppco2_mmhg.value,
            radiation_dose_rate_msv_h=self._config.environment.baseline_radiation_dose_rate_msv_h.value,
            microgravity_exposure=self._config.environment.microgravity_exposure.value,
            environmental_stress=self._config.environment.environmental_stress_baseline.value,
        )
        self._scenario_engine = ScenarioEngine()
        self._events: list[SimulationEvent] = []
        self._stream_ticks: dict[str, list[dict[str, Any]]] = {}
        self._daily_logs: dict[str, list[dict[str, Any]]] = {}
        self._last_output_seconds = -1
        self._last_daily_day = -1
        self._status: str = "CREATED"
        self._build_engines()

    # ------------------------------------------------------------------
    # Инициализация
    # ------------------------------------------------------------------

    def _default_config(self) -> SimulationConfig:
        """Создать конфигурацию по умолчанию."""
        from .config import MissionConfig, NumericalConfig, SimulationConfig

        return SimulationConfig(
            mission=MissionConfig(
                mission_id="ASTRALIS-DEMO-180D",
                mission_name="ASTRALIS Hybrid Simulation Demo",
                start_utc="2026-04-22T08:00:00Z",
                planned_duration_days=180,
            ),
            environment=default_environment(),
            numerical=NumericalConfig(),
            validation=default_validation(),
            profiles=default_profiles(),
        )

    def _build_engines(self) -> None:
        """Создать движки на основе текущей конфигурации."""
        self._environment_engine = EnvironmentEngine(
            self._config.environment,
            self._config.validation,
            random.Random(self._config.random_seed + 17),
        )
        self._astronaut_states: dict[str, AstronautState] = {}
        self._physiology_engines: dict[str, Any] = {}
        self._countermeasure_engines: dict[str, CountermeasureEngine] = {}
        for index, profile in enumerate(self._config.profiles):
            rng = random.Random(self._config.random_seed + 101 + index * 37)
            self._astronaut_states[profile.astronaut_id] = AstronautState(
                astronaut_id=profile.astronaut_id,
                physiology=PhysiologicalState(
                    hr=profile.cardiovascular.baseline_hr.value,
                    hrv_rmssd=profile.cardiovascular.baseline_hrv_rmssd.value,
                    sbp=profile.cardiovascular.baseline_sbp.value,
                    dbp=profile.cardiovascular.baseline_dbp.value,
                    spo2=profile.respiratory.baseline_spo2.value,
                    resp_rate=profile.respiratory.baseline_resp_rate.value,
                    temp_c=profile.respiratory.baseline_temp_c.value,
                    pvt_mean_rt_ms=profile.cognitive.baseline_pvt_mean_rt_ms.value,
                    pvt_slowest10_rt_ms=profile.cognitive.baseline_pvt_slowest10_rt_ms.value,
                    iop_mmhg=profile.adaptation.baseline_iop_mmhg.value,
                    vo2max=43.0,
                ),
                countermeasure=CountermeasureState(),
            )
            from .physiology_engine import PhysiologyEngine

            self._physiology_engines[profile.astronaut_id] = PhysiologyEngine(
                profile,
                self._config.validation,
                rng,
            )
            self._countermeasure_engines[profile.astronaut_id] = CountermeasureEngine(profile)

    @staticmethod
    def _parse_utc(value: str):
        """Разобрать ISO-8601 UTC строку."""
        from datetime import UTC, datetime

        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)

    # ------------------------------------------------------------------
    # Публичные свойства
    # ------------------------------------------------------------------

    @property
    def config(self) -> SimulationConfig:
        """Вернуть текущую конфигурацию."""
        return self._config

    @property
    def clock(self) -> MissionClock:
        """Вернуть миссионные часы."""
        return self._clock

    @property
    def environment_state(self) -> EnvironmentState:
        """Вернуть текущее состояние окружения."""
        return self._environment

    @property
    def astronaut_states(self) -> dict[str, AstronautState]:
        """Вернуть состояния всех астронавтов."""
        return self._astronaut_states

    def events(self) -> list[SimulationEvent]:
        """Вернуть журнал событий симуляции."""
        return list(self._events)

    # ------------------------------------------------------------------
    # Управление миссией
    # ------------------------------------------------------------------

    def create_mission(self) -> SimulationStatus:
        """Создать миссию в начальном состоянии."""
        self.reset()
        self._status = "CREATED"
        return self.get_state()

    def start(self) -> SimulationStatus:
        """Запустить миссию."""
        self._status = "RUNNING"
        self._clock.resume()
        self._register_event("MISSION_START", "Simulation mission started.")
        return self.get_state()

    def pause(self) -> SimulationStatus:
        """Поставить миссию на паузу."""
        self._status = "PAUSED"
        self._clock.pause()
        self._register_event("MISSION_PAUSE", "Simulation mission paused.")
        return self.get_state()

    def resume(self) -> SimulationStatus:
        """Возобновить миссию."""
        self._status = "RUNNING"
        self._clock.resume()
        self._register_event("MISSION_RESUME", "Simulation mission resumed.")
        return self.get_state()

    def stop(self) -> SimulationStatus:
        """Остановить миссию."""
        self._status = "STOPPED"
        self._clock.stop()
        self._register_event("MISSION_STOP", "Simulation mission stopped.")
        return self.get_state()

    def reset(self) -> SimulationStatus:
        """Полностью сбросить миссию."""
        self._clock.reset()
        self._environment = EnvironmentState(
            cabin_ppco2_mmhg=self._config.environment.baseline_ppco2_mmhg.value,
            radiation_dose_rate_msv_h=self._config.environment.baseline_radiation_dose_rate_msv_h.value,
            microgravity_exposure=self._config.environment.microgravity_exposure.value,
            environmental_stress=self._config.environment.environmental_stress_baseline.value,
        )
        self._scenario_engine = ScenarioEngine()
        self._events.clear()
        self._stream_ticks.clear()
        self._daily_logs.clear()
        self._last_output_seconds = -1
        self._last_daily_day = -1
        self._status = "CREATED"
        self._build_engines()
        self._register_event("MISSION_RESET", "Simulation mission reset.")
        return self.get_state()

    def set_speed(self, speed: float) -> SimulationStatus:
        """Установить скорость симуляции."""
        self._clock.set_speed(speed)
        return self.get_state()

    def step(self) -> SimulationStatus:
        """Продвинуть симуляцию на один внутренний шаг."""
        if self._status in {"STOPPED", "COMPLETED"}:
            return self.get_state()
        self._advance_once(self._config.numerical.internal_step_seconds)
        return self.get_state()

    def advance(self, seconds: int) -> SimulationStatus:
        """Продвинуть симуляцию на заданное миссионное время."""
        if seconds <= 0:
            return self.get_state()
        target = self._clock.elapsed_seconds + seconds
        internal_step = self._config.numerical.internal_step_seconds
        while self._clock.elapsed_seconds < target and self._status not in {"STOPPED", "COMPLETED"}:
            self._advance_once(min(internal_step, target - self._clock.elapsed_seconds))
        return self.get_state()

    # ------------------------------------------------------------------
    # Состояния и телеметрия
    # ------------------------------------------------------------------

    def get_state(self) -> SimulationStatus:
        """Вернуть текущий публичный статус симуляции."""
        mission_day = self._clock.mission_day
        planned_seconds = self._config.mission.planned_duration_days * 86400
        if self._clock.elapsed_seconds >= planned_seconds:
            self._status = "COMPLETED"
        return SimulationStatus(
            mission_status=self._status,  # type: ignore[arg-type]
            mission_time_seconds=self._clock.elapsed_seconds,
            mission_day=mission_day,
            mission_phase=self._clock.mission_phase,  # type: ignore[arg-type]
            simulation_speed=self._clock.speed,
            active_scenarios=[
                instance.definition.scenario_id
                for instance in self._scenario_engine.active_scenarios()
            ],
            active_astronauts=list(self._astronaut_states),
            current_model_version=self._config.model_version,
            random_seed=self._config.random_seed,
            internal_step_seconds=self._config.numerical.internal_step_seconds,
            output_step_seconds=self._config.numerical.output_step_seconds,
        )

    def get_astronaut_state(self, astronaut_id: str) -> dict[str, Any]:
        """Вернуть состояние конкретного астронавта."""
        if astronaut_id not in self._astronaut_states:
            raise KeyError(f"Unknown astronaut: {astronaut_id}")
        return self._astronaut_states[astronaut_id].to_dict()

    def get_environment_state(self) -> dict[str, Any]:
        """Вернуть состояние окружения."""
        return self._environment.to_dict()

    def stream_ticks(self, astronaut_id: str | None = None) -> list[dict[str, Any]]:
        """Вернуть накопленные тики телеметрии."""
        if astronaut_id:
            return list(self._stream_ticks.get(astronaut_id, []))
        combined: list[dict[str, Any]] = []
        for astronaut_id in sorted(self._stream_ticks):
            combined.extend(self._stream_ticks[astronaut_id])
        return combined

    def daily_logs(self, astronaut_id: str | None = None) -> list[dict[str, Any]]:
        """Вернуть накопленные суточные записи."""
        if astronaut_id:
            return list(self._daily_logs.get(astronaut_id, []))
        combined: list[dict[str, Any]] = []
        for astronaut_id in sorted(self._daily_logs):
            combined.extend(self._daily_logs[astronaut_id])
        return combined

    def iter_live(self) -> Iterator[dict[str, Any]]:
        """Генератор live-телеметрии с учётом скорости."""
        import time

        while self._status == "RUNNING":
            before = self._clock.elapsed_seconds
            self.step()
            if self._clock.elapsed_seconds == before:
                break
            for astronaut_id in sorted(self._stream_ticks):
                rows = self._stream_ticks.get(astronaut_id, [])
                if rows:
                    yield rows[-1]
            time.sleep(self._config.numerical.output_step_seconds / self._clock.speed)

    # ------------------------------------------------------------------
    # Сценарии и контрмеры
    # ------------------------------------------------------------------

    def inject_scenario(self, scenario_id: str) -> SimulationEvent:
        """Запустить сценарий и записать событие."""
        instance = self._scenario_engine.start(scenario_id, self._clock.elapsed_seconds)
        event = self._register_event(
            "SCENARIO_STARTED",
            f"Scenario started: {instance.definition.name}.",
            scenario_id=scenario_id,
            severity=instance.definition.severity,
            affected_systems=list(instance.definition.affected_systems),
        )
        return event

    def terminate_scenario(self, scenario_id: str) -> SimulationEvent:
        """Досрочно завершить сценарий."""
        self._scenario_engine.terminate(scenario_id)
        return self._register_event(
            "SCENARIO_TERMINATED",
            f"Scenario terminated: {scenario_id}.",
            scenario_id=scenario_id,
            severity="INFO",
        )

    def apply_countermeasure(
        self,
        countermeasure_type: str,
        *,
        astronaut_id: str | None = None,
        effectiveness: float = 1.0,
    ) -> SimulationEvent:
        """Применить контрмеру к одному или всем астронавтам."""
        targets = (
            [astronaut_id]
            if astronaut_id
            else list(self._astronaut_states)
        )
        for target in targets:
            if target not in self._astronaut_states:
                raise KeyError(f"Unknown astronaut: {target}")
            self._countermeasure_engines[target].apply_countermeasure(
                self._astronaut_states[target].physiology,
                self._astronaut_states[target].countermeasure,
                countermeasure_type,  # type: ignore[arg-type]
                effectiveness=effectiveness,
            )
            if countermeasure_type == "ENVIRONMENTAL_CORRECTION":
                self._environment_engine.correct_cabin_co2(self._environment)
        return self._register_event(
            "COUNTERMEASURE_APPLIED",
            f"Countermeasure applied: {countermeasure_type}.",
            affected_systems=["COUNTERMEASURE"],
        )

    # ------------------------------------------------------------------
    # What-If
    # ------------------------------------------------------------------

    def run_what_if(
        self,
        modification: WhatIfModification,
        duration_seconds: int,
        *,
        experiment_id: str = "WHAT_IF_EXPERIMENT",
    ) -> WhatIfResult:
        """Запустить изолированный What-If эксперимент."""
        engine = WhatIfEngine(self)
        return engine.run(
            modification,
            duration_seconds,
            experiment_id=experiment_id,
        )

    # ------------------------------------------------------------------
    # Экспорт и контрольные точки
    # ------------------------------------------------------------------

    def export_telemetry(
        self,
        *,
        format: str = "jsonl",
        directory: str | None = None,
    ) -> dict[str, str]:
        """Экспортировать телеметрию в JSON, JSONL или CSV."""
        export_dir = Path(directory or self._config.export_directory)
        export_dir.mkdir(parents=True, exist_ok=True)
        written: dict[str, str] = {}

        if format in {"json", "jsonl"}:
            stream_path = export_dir / f"telemetry_stream.{format}"
            daily_path = export_dir / f"telemetry_daily.{format}"
            stream_payload = self.stream_ticks()
            daily_payload = self.daily_logs()
            if format == "jsonl":
                stream_path.write_text(
                    "\n".join(json.dumps(row, ensure_ascii=False) for row in stream_payload) + "\n",
                    encoding="utf-8",
                )
                daily_path.write_text(
                    "\n".join(json.dumps(row, ensure_ascii=False) for row in daily_payload) + "\n",
                    encoding="utf-8",
                )
            else:
                stream_path.write_text(json.dumps(stream_payload, ensure_ascii=False, indent=2), encoding="utf-8")
                daily_path.write_text(json.dumps(daily_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            written["stream"] = str(stream_path)
            written["daily"] = str(daily_path)

        if format in {"csv", "all"}:
            csv_path = export_dir / "telemetry_stream.csv"
            rows = self.stream_ticks()
            if rows:
                fieldnames = list(rows[0].keys())
                import csv

                with csv_path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fieldnames)
                    writer.writeheader()
                    for row in rows:
                        writer.writerow(row)
            written["stream_csv"] = str(csv_path)

        if format == "all":
            written.update(self.export_telemetry(format="jsonl", directory=directory))
        return written

    def save_checkpoint(self, path: str | Path) -> Path:
        """Сохранить контрольную точку симуляции."""
        checkpoint_path = Path(path)
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_text(
            json.dumps(self.snapshot_state(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return checkpoint_path

    def load_checkpoint(self, path: str | Path) -> SimulationStatus:
        """Загрузить контрольную точку симуляции."""
        checkpoint_path = Path(path)
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
        payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        self.restore_state(payload)
        return self.get_state()

    def snapshot_state(self) -> dict[str, Any]:
        """Сериализовать текущее состояние симуляции."""
        return {
            "config": self._config.model_dump(mode="json"),
            "clock": {
                "elapsed_seconds": self._clock.elapsed_seconds,
                "speed": self._clock.speed,
                "paused": self._clock.paused,
                "stopped": self._clock.stopped,
            },
            "environment_state": self._environment.to_dict(),
            "astronaut_states": {
                astronaut_id: state.to_dict()
                for astronaut_id, state in self._astronaut_states.items()
            },
            "scenario_state": self._scenario_engine.export_state(),
            "status": self._status,
            "events": [event.model_dump(mode="json") for event in self._events],
        }

    def restore_state(self, payload: dict[str, Any]) -> None:
        """Восстановить состояние симуляции из словаря."""
        from .config import SimulationConfig

        self._config = SimulationConfig.model_validate(payload["config"])
        self._build_engines()
        clock_payload = payload["clock"]
        self._clock.elapsed_seconds = int(clock_payload["elapsed_seconds"])
        self._clock.speed = float(clock_payload["speed"])
        self._clock.paused = bool(clock_payload["paused"])
        self._clock.stopped = bool(clock_payload["stopped"])
        self._environment = EnvironmentState(**payload["environment_state"])
        for astronaut_id, astronaut_payload in payload["astronaut_states"].items():
            if astronaut_id not in self._astronaut_states:
                continue
            physiology = PhysiologicalState(**astronaut_payload["physiology"])
            countermeasure = CountermeasureState(**astronaut_payload["countermeasure"])
            self._astronaut_states[astronaut_id].physiology = physiology
            self._astronaut_states[astronaut_id].countermeasure = countermeasure
        self._status = str(payload.get("status", "CREATED"))
        self._events = [
            SimulationEvent.model_validate(event_payload)
            for event_payload in payload.get("events", [])
        ]
        self._restore_scenario_state(payload.get("scenario_state", {}))

    def _restore_scenario_state(self, payload: dict[str, Any]) -> None:
        """Восстановить активные сценарии из контрольной точки."""
        from .scenarios import ScenarioInstance

        self._scenario_engine = ScenarioEngine()
        for row in payload.get("active", []):
            definition = next(
                (
                    item
                    for item in self._scenario_engine.definitions
                    if item.scenario_id == row["scenario_id"]
                ),
                None,
            )
            if definition is None:
                continue
            instance = ScenarioInstance(
                definition=definition,
                start_seconds=int(row["start_seconds"]),
                elapsed_seconds=int(row["elapsed_seconds"]),
                terminated=bool(row.get("terminated", False)),
                completed=bool(row.get("completed", False)),
            )
            self._scenario_engine._instances[definition.scenario_id] = instance

    # ------------------------------------------------------------------
    # Внутренние методы
    # ------------------------------------------------------------------

    def _advance_once(self, dt: float) -> None:
        """Выполнить один внутренний шаг симуляции."""
        dt_seconds = int(round(dt))
        if dt_seconds <= 0:
            return
        self._clock.advance(dt_seconds)
        self._scenario_engine.update(dt_seconds)
        self._scenario_engine.apply_effects(
            self._environment,
            {
                astronaut_id: state.physiology
                for astronaut_id, state in self._astronaut_states.items()
            },
            baseline_ppco2_mmhg=self._config.environment.baseline_ppco2_mmhg.value,
            baseline_radiation_dose_rate_msv_h=self._config.environment.baseline_radiation_dose_rate_msv_h.value,
            dt=float(dt_seconds),
        )
        self._environment_engine.update(self._environment, float(dt_seconds))
        if not self._scenario_engine.active_scenarios():
            self._environment.ppco2_target_mmhg = None
            self._environment.radiation_dose_rate_target_msv_h = None

        for astronaut_id, state in self._astronaut_states.items():
            physiology_engine = self._physiology_engines[astronaut_id]
            physiology_engine.update_fast(state.physiology, self._environment, float(dt_seconds))
            physiology_engine.update_slow(state.physiology, self._environment, float(dt_seconds))
            physiology_engine.clamp_to_validation(state.physiology)

        if self._clock.mission_day != self._last_daily_day:
            self._handle_daily()
            self._last_daily_day = self._clock.mission_day

        if self._should_emit_output():
            self._collect_telemetry()
            self._last_output_seconds = self._clock.elapsed_seconds

    def _should_emit_output(self) -> bool:
        """Проверить, пора ли emitting телеметрию."""
        output_step = int(round(self._config.numerical.output_step_seconds))
        return self._clock.elapsed_seconds % output_step == 0

    def _collect_telemetry(self) -> None:
        """Собрать текущие тики и суточные записи."""
        for astronaut_id, state in self._astronaut_states.items():
            tick = to_stream_tick(state, self._environment, self._clock)
            self._stream_ticks.setdefault(astronaut_id, []).append(tick.model_dump(mode="json"))

    def _handle_daily(self) -> None:
        """Обработать переход на новые сутки."""
        planned_days = self._config.mission.planned_duration_days
        for astronaut_id, state in self._astronaut_states.items():
            countermeasure_engine = self._countermeasure_engines[astronaut_id]
            missed_ared = any(
                instance.definition.scenario_id == "MISSED_ARED"
                for instance in self._scenario_engine.active_scenarios()
            )
            countermeasure_engine.schedule_daily(
                state.countermeasure,
                random.Random(
                    self._config.random_seed
                    + self._clock.mission_day * 31
                    + int.from_bytes(astronaut_id.encode("utf-8"), "little") % 100000
                ),
                missed_ared_scenario_active=missed_ared,
            )
            self._physiology_engines[astronaut_id].daily_update(
                state.physiology,
                state.countermeasure,
                self._environment,
            )
            countermeasure_engine.update_daily(
                state.physiology,
                state.countermeasure,
                self._environment,
            )
            state.countermeasure.sleep_intervention_active = False
            if self._clock.mission_day <= planned_days:
                daily_log = to_daily_log(state, self._environment, self._clock)
                self._daily_logs.setdefault(astronaut_id, []).append(daily_log.model_dump(mode="json"))
                self._register_event(
                    "DAILY_SLEEP_COMPLETED",
                    f"Daily sleep completed for {astronaut_id}.",
                    astronaut_id=astronaut_id,
                    severity="INFO",
                )
        self._environment_engine.reset_daily_radiation(self._environment)

    def _register_event(
        self,
        event_type: str,
        description: str,
        *,
        scenario_id: str | None = None,
        severity: str = "INFO",
        affected_systems: list[str] | None = None,
        astronaut_id: str | None = None,
    ) -> SimulationEvent:
        """Зарегистрировать событие симуляции."""
        event = SimulationEvent(
            event_id=f"EVT-{self._clock.elapsed_seconds:09d}-{len(self._events) + 1:05d}",
            timestamp=self._clock.timestamp_utc,
            mission_time_seconds=self._clock.elapsed_seconds,
            mission_day=self._clock.mission_day,
            astronaut_id=astronaut_id,
            event_type=event_type,  # type: ignore[arg-type]
            scenario_id=scenario_id,
            severity=severity,  # type: ignore[arg-type]
            description=description,
            affected_systems=affected_systems or [],
            provenance={
                "simulation_engine_version": self._config.simulation_engine_version,
                "model_version": self._config.model_version,
                "random_seed": self._config.random_seed,
                "source_type": "SYNTHETIC",
            },
        )
        self._events.append(event)
        return event

    def set_cabin_ppco2_target(self, target_mmhg: float) -> None:
        """Установить целевой ppCO2 для What-If эксперимента."""
        self._environment.cabin_ppco2_mmhg = target_mmhg

    def add_radiation_dose_rate_delta(self, delta_msv_h: float) -> None:
        """Добавить дельту к текущей дозовой мощности."""
        self._environment.radiation_dose_rate_msv_h = max(
            0.0,
            self._environment.radiation_dose_rate_msv_h + delta_msv_h,
        )

    def reload_config(self, config: SimulationConfig) -> None:
        """Заменить конфигурацию и пересобрать движки."""
        self._config = config
        self._build_engines()


__all__ = ["SimulationController"]
