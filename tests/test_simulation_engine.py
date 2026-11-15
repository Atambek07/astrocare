"""Тесты жизненного цикла симуляции AstroCare."""

from __future__ import annotations

from simulation_engine import SimulationController
from simulation_engine.what_if import WhatIfModification


def test_astrocare_simulation_ids_and_telemetry() -> None:
    """Two astronauts must run independently and produce telemetry."""
    controller = SimulationController()
    controller.start()
    controller.advance(120)
    assert set(controller.astronaut_states) == {"A1", "A2"}
    assert len(controller.stream_ticks("A1")) == 120
    assert len(controller.stream_ticks("A2")) == 120


def test_hypercapnic_scenario_changes_environment() -> None:
    """The hypercapnic scenario must raise cabin ppCO2 gradually."""
    controller = SimulationController()
    controller.start()
    controller.inject_scenario("HYPERCAPNIC_CABIN")
    before = controller.environment_state.cabin_ppco2_mmhg
    controller.advance(600)
    assert controller.environment_state.cabin_ppco2_mmhg > before


def test_what_if_does_not_mutate_baseline() -> None:
    """What-If experiments must preserve the original mission state."""
    controller = SimulationController()
    controller.start()
    controller.advance(120)
    snapshot = controller.snapshot_state()
    controller.run_what_if(WhatIfModification(ppco2_target_mmhg=5.0), 600)
    assert controller.snapshot_state() == snapshot
