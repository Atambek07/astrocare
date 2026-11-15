"""Тесты адаптера между симуляцией и Backend Brain."""

from __future__ import annotations

from astro_brain.astrocare_service import public_astronaut_id, simulation_state_to_input
from simulation_engine import SimulationController


def test_simulation_state_maps_to_brain_contract() -> None:
    """Simulation state must convert into a valid Brain input dict."""
    controller = SimulationController()
    payload = simulation_state_to_input(controller, "A1")
    assert payload["astronaut_id"] == "ASTRO-01"
    assert isinstance(payload["hr"], int)
    assert isinstance(payload["spo2"], int)
    assert isinstance(payload["resp_rate"], int)
    assert isinstance(payload["bp"]["systolic"], int)
    assert isinstance(payload["bp"]["diastolic"], int)
    assert payload["radiation_dose_rate"] >= 0


def test_public_astronaut_mapping_is_stable() -> None:
    """Internal simulation IDs map to the public AstroCare IDs."""
    assert public_astronaut_id("A1") == "ASTRO-01"
    assert public_astronaut_id("A2") == "ASTRO-02"
    assert public_astronaut_id("UNKNOWN") == "UNKNOWN"
