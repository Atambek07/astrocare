"""Тесты гибридного симуляционного движка ASTRALIS.

Сообщения тестов — на английском, комментарии и docstrings — на русском.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shared.contracts import DailyTelemetryLog, StreamTick
from simulation_engine import (
    SimulationController,
    SimulationEvent,
    SimulationStatus,
    to_daily_log,
    to_stream_tick,
)
from simulation_engine.what_if import WhatIfModification


def _short_controller(output_step: float = 60.0) -> SimulationController:
    """Создать контроллер с крупным внутренним шагом для быстрых тестов."""
    controller = SimulationController()
    controller.config.numerical.internal_step_seconds = output_step
    controller.config.numerical.output_step_seconds = output_step
    controller._build_engines()
    return controller


def test_sixty_minute_simulation_generates_one_hz_stream() -> None:
    """60 minutes must generate exactly 3,600 telemetry ticks per astronaut."""
    controller = SimulationController()
    controller.start()
    controller.advance(3600)
    assert controller.clock.elapsed_seconds == 3600
    assert len(controller._stream_ticks["A1"]) == 3600
    assert len(controller._stream_ticks["A2"]) == 3600
    assert len(controller._daily_logs["A1"]) >= 1
    assert len(controller._daily_logs["A2"]) >= 1


def test_simulation_is_deterministic_for_same_seed() -> None:
    """Identical seeds and configuration must produce identical telemetry."""
    controller_a = SimulationController()
    controller_b = SimulationController()
    controller_a.start()
    controller_b.start()
    controller_a.advance(120)
    controller_b.advance(120)
    assert controller_a.stream_ticks("A1") == controller_b.stream_ticks("A1")
    assert controller_a.stream_ticks("A2") == controller_b.stream_ticks("A2")


def test_stream_and_daily_records_validate_against_contracts() -> None:
    """Generated telemetry must satisfy the shared Pydantic contracts."""
    controller = SimulationController()
    controller.start()
    controller.advance(120)
    stream_rows = controller.stream_ticks("A1")
    daily_rows = controller.daily_logs("A1")
    assert stream_rows
    assert daily_rows
    StreamTick.model_validate(stream_rows[-1])
    DailyTelemetryLog.model_validate(daily_rows[-1])


def test_hypercapnic_scenario_raises_cabin_co2_gradually() -> None:
    """The hypercapnic scenario must raise cabin CO2 without an instant jump."""
    controller = _short_controller(output_step=30.0)
    controller.start()
    controller.inject_scenario("HYPERCAPNIC_CABIN")
    initial_ppco2 = controller.environment_state.cabin_ppco2_mmhg
    controller.advance(900)
    later_ppco2 = controller.environment_state.cabin_ppco2_mmhg
    assert later_ppco2 > initial_ppco2
    assert later_ppco2 <= 20.0
    assert "HYPERCAPNIC_CABIN" in controller.get_state().active_scenarios


def test_solar_particle_event_increases_radiation_and_stays_monotonic() -> None:
    """Cumulative radiation must never decrease during a radiation event."""
    controller = _short_controller(output_step=60.0)
    controller.start()
    controller.inject_scenario("SOLAR_PARTICLE_EVENT")
    previous_cumulative = controller.environment_state.cumulative_radiation_msv
    for _ in range(20):
        controller.advance(60)
        current_cumulative = controller.environment_state.cumulative_radiation_msv
        assert current_cumulative >= previous_cumulative
        previous_cumulative = current_cumulative
    assert "SOLAR_PARTICLE_EVENT" in controller.get_state().active_scenarios


def test_what_if_experiment_is_isolated() -> None:
    """A What-If experiment must not mutate the original mission state."""
    controller = SimulationController()
    controller.config.numerical.internal_step_seconds = 300
    controller.config.numerical.output_step_seconds = 300
    controller._build_engines()
    controller.start()
    controller.advance(600)
    baseline_snapshot = controller.snapshot_state()
    result = controller.run_what_if(
        WhatIfModification(
            ppco2_target_mmhg=5.0,
            sleep_duration_delta_h=-2.0,
        ),
        duration_seconds=3600,
        experiment_id="TEST_WHAT_IF",
    )
    assert isinstance(result, object)
    assert result.experiment_id == "TEST_WHAT_IF"
    assert result.baseline_results
    assert result.experiment_results
    assert result.difference_metrics
    assert controller.snapshot_state() == baseline_snapshot


def test_what_if_sleep_delta_actually_changes_sleep_debt() -> None:
    """A negative sleep-opportunity experiment must increase modeled sleep debt."""
    controller = SimulationController()
    controller.config.numerical.internal_step_seconds = 86400
    controller.config.numerical.output_step_seconds = 86400
    controller._build_engines()
    controller.start()
    baseline = controller.run_what_if(WhatIfModification(), 5 * 86400, experiment_id="SLEEP_BASELINE")
    experiment = controller.run_what_if(
        WhatIfModification(sleep_duration_delta_h=-2.0),
        5 * 86400,
        experiment_id="SLEEP_REDUCED",
    )
    baseline_debt = sum(value for key, value in baseline.difference_metrics.items() if key.endswith(".sleep_debt_h"))
    reduced_debt = sum(value for key, value in experiment.difference_metrics.items() if key.endswith(".sleep_debt_h"))
    assert reduced_debt > baseline_debt


def test_what_if_missed_ared_actually_reduces_vo2max() -> None:
    """A missed-ARED experiment must degrade modeled VO2max relative to baseline."""
    controller = SimulationController()
    controller.config.numerical.internal_step_seconds = 86400
    controller.config.numerical.output_step_seconds = 86400
    controller._build_engines()
    controller.start()
    baseline = controller.run_what_if(WhatIfModification(), 7 * 86400, experiment_id="ARED_BASELINE")
    experiment = controller.run_what_if(
        WhatIfModification(missed_ared_days=7),
        7 * 86400,
        experiment_id="ARED_MISSED",
    )
    baseline_vo2 = baseline.experiment_results["A1.vo2max"]
    missed_vo2 = experiment.experiment_results["A1.vo2max"]
    assert missed_vo2 < baseline_vo2


def test_checkpoint_round_trip_restores_mission_time_and_state() -> None:
    """Checkpoint save/load must restore mission time and astronaut state."""
    controller = _short_controller(output_step=300.0)
    controller.start()
    controller.advance(1800)
    checkpoint_path = Path("/tmp/opencode/simulation_checkpoint.json")
    controller.save_checkpoint(checkpoint_path)
    restored_controller = SimulationController()
    restored_controller.load_checkpoint(checkpoint_path)
    assert restored_controller.clock.elapsed_seconds == controller.clock.elapsed_seconds
    assert restored_controller.get_astronaut_state("A1") == controller.get_astronaut_state("A1")
    assert restored_controller.get_environment_state() == controller.get_environment_state()


def test_export_telemetry_writes_jsonl_and_csv() -> None:
    """Telemetry export must write JSONL and CSV artifacts."""
    controller = SimulationController()
    controller.config.numerical.internal_step_seconds = 60
    controller.config.numerical.output_step_seconds = 60
    controller._build_engines()
    controller.start()
    controller.advance(600)
    export_dir = Path("/tmp/opencode/simulation_export_test")
    written = controller.export_telemetry(format="all", directory=str(export_dir))
    assert Path(written["stream"]).exists()
    assert Path(written["stream_csv"]).exists()
    assert Path(written["daily"]).exists()


def test_individual_astroaut_states_are_not_identical() -> None:
    """A1 and A2 must have separate trajectories under the same environment."""
    controller = SimulationController()
    controller.start()
    controller.advance(600)
    a1 = controller.get_astronaut_state("A1")["physiology"]
    a2 = controller.get_astronaut_state("A2")["physiology"]
    assert a1["hr"] != a2["hr"]
    assert a1["hrv_rmssd"] != a2["hrv_rmssd"]


def test_countermeasure_can_improve_vo2max() -> None:
    """A countermeasure must affect the actual physiological state."""
    controller = SimulationController()
    controller.start()
    state = controller.astronaut_states["A1"]
    before = state.physiology.vo2max
    controller.apply_countermeasure("AEROBIC_EXERCISE", astronaut_id="A1")
    after = state.physiology.vo2max
    assert after > before


def test_mission_time_cannot_move_backward() -> None:
    """Mission time must never decrease during normal operation."""
    controller = SimulationController()
    controller.start()
    controller.advance(600)
    before = controller.clock.elapsed_seconds
    with pytest.raises(ValueError):
        controller.clock.advance(-1)
    with pytest.raises(ValueError):
        controller.clock.advance(-100)
    assert controller.clock.elapsed_seconds == before


def test_unknown_countermeasure_is_rejected() -> None:
    """Unknown countermeasures must fail instead of silently doing nothing."""
    controller = SimulationController()
    state = controller.astronaut_states["A1"]
    before = state.physiology.vo2max
    with pytest.raises(ValueError):
        controller.apply_countermeasure("UNKNOWN_COUNTERMEASURE", astronaut_id="A1")
    assert state.physiology.vo2max == before


def test_scenario_termination_and_recovery() -> None:
    """Scenario termination must remove it from active scenarios after recovery."""
    controller = _short_controller(output_step=300.0)
    controller.start()
    controller.inject_scenario("HYPERCAPNIC_CABIN")
    controller.terminate_scenario("HYPERCAPNIC_CABIN")
    controller.advance(1200)
    assert "HYPERCAPNIC_CABIN" not in controller.get_state().active_scenarios


def test_events_have_provenance_metadata() -> None:
    """Every simulation event must carry provenance metadata."""
    controller = SimulationController()
    controller.start()
    controller.inject_scenario("HYPERCAPNIC_CABIN")
    for event in controller.events():
        assert event.provenance
        assert event.provenance["source_type"] == "SYNTHETIC"
        assert event.provenance["simulation_engine_version"]
        assert event.provenance["model_version"]


def test_180_day_mission_is_feasible_and_bounded() -> None:
    """The engine must simulate 180 days efficiently with bounded states."""
    controller = SimulationController()
    controller.config.numerical.internal_step_seconds = 300
    controller.config.numerical.output_step_seconds = 300
    controller._build_engines()
    controller.start()
    controller.advance(180 * 86400)
    assert controller.get_state().mission_status == "COMPLETED"
    assert len(controller._stream_ticks["A1"]) >= 50000
    assert len(controller._daily_logs["A1"]) == 180
    assert len(controller._daily_logs["A2"]) == 180
    assert controller.environment_state.cumulative_radiation_msv > 0.0
    assert controller.environment_state.cumulative_radiation_msv <= 5000.0
