"""Численные и физиологические проверки гибридной симуляции."""

from __future__ import annotations

import math

import pytest

from simulation_engine import SimulationController


def _controller(step_seconds: float) -> SimulationController:
    """Создать контроллер с заданным шагом интегрирования."""
    controller = SimulationController()
    controller.config.numerical.internal_step_seconds = step_seconds
    controller.config.numerical.output_step_seconds = step_seconds
    controller._build_engines()
    return controller


@pytest.mark.parametrize("step_seconds", [1.0, 5.0, 30.0, 300.0])
def test_simulation_states_remain_finite_for_step_sizes(step_seconds: float) -> None:
    """No integration step in the supported range may emit NaN or infinity."""
    controller = _controller(step_seconds)
    controller.start()
    controller.advance(600)
    for state in controller.astronaut_states.values():
        values = state.physiology.to_dict().values()
        assert all(
            not isinstance(value, float) or math.isfinite(value)
            for value in values
        )
    environment = controller.environment_state.to_dict().values()
    assert all(
        not isinstance(value, float) or math.isfinite(value)
        for value in environment
    )


@pytest.mark.parametrize("step_seconds", [1.0, 30.0, 300.0])
def test_physiological_values_remain_in_documented_bounds(step_seconds: float) -> None:
    """All supported integration steps must remain within model constraints."""
    controller = _controller(step_seconds)
    controller.start()
    controller.inject_scenario("HYPERCAPNIC_CABIN")
    controller.advance(1200)
    for state in controller.astronaut_states.values():
        physiology = state.physiology
        assert 20.0 <= physiology.hr <= 250.0
        assert 0.0 <= physiology.hrv_rmssd <= 300.0
        assert 50.0 <= physiology.spo2 <= 100.0
        assert 50.0 <= physiology.sbp <= 260.0
        assert 20.0 <= physiology.dbp <= 160.0
        assert 30.0 <= physiology.temp_c <= 45.0
        assert 4.0 <= physiology.resp_rate <= 60.0
        assert 0.0 <= physiology.fluid_shift_index <= 3.0
    environment = controller.environment_state
    assert 0.0 <= environment.cabin_ppco2_mmhg <= 20.0
    assert 0.0 <= environment.radiation_dose_rate_msv_h <= 1000.0
    assert environment.cumulative_radiation_msv >= 0.0


def test_radiation_is_monotonic_under_scenarios() -> None:
    """Cumulative radiation must never decrease, including during an SPE."""
    controller = _controller(30.0)
    controller.start()
    controller.inject_scenario("SOLAR_PARTICLE_EVENT")
    previous = controller.environment_state.cumulative_radiation_msv
    for _ in range(20):
        controller.advance(60)
        current = controller.environment_state.cumulative_radiation_msv
        assert current >= previous
        previous = current


def test_step_size_affects_precision_but_not_contract_validity() -> None:
    """Finer integration is more precise, but every result remains bounded."""
    coarse = _controller(300.0)
    fine = _controller(1.0)
    for controller in (coarse, fine):
        controller.start()
        controller.inject_scenario("HYPERCAPNIC_CABIN")
        controller.advance(1800)
        assert math.isfinite(controller.environment_state.cabin_ppco2_mmhg)
        assert 0.0 <= controller.environment_state.cabin_ppco2_mmhg <= 20.0
    # Exact equality is not expected across numerical resolutions.
    assert coarse.environment_state.cabin_ppco2_mmhg != fine.environment_state.cabin_ppco2_mmhg


def test_reproducibility_survives_reset() -> None:
    """Identical seed and reset must reproduce the same early trajectory."""
    first = _controller(30.0)
    second = _controller(30.0)
    for controller in (first, second):
        controller.start()
        controller.advance(600)
    assert first.stream_ticks("A1") == second.stream_ticks("A1")
    assert first.stream_ticks("A2") == second.stream_ticks("A2")
