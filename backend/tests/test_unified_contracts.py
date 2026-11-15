"""Контрактные проверки между симуляцией, Brain и frontend-адаптером."""

from __future__ import annotations

import pytest

from astro_brain.adapters.frontend import to_brain_tick
from astro_brain.astrocare_service import public_astronaut_id, simulation_state_to_input
from astro_brain.contract import parse_sample
from astro_brain.pipeline import Brain
from shared.contracts import DailyTelemetryLog, SourceType, StreamTick
from simulation_engine import SimulationController, to_daily_log, to_stream_tick


def test_simulation_stream_and_daily_match_shared_contracts() -> None:
    """Simulation serializers must produce valid shared StreamTick and DailyTelemetryLog records."""
    controller = SimulationController()
    controller.start()
    controller.advance(2)
    state = controller.astronaut_states["A1"]
    tick = to_stream_tick(state, controller.environment_state, controller.clock)
    daily = to_daily_log(state, controller.environment_state, controller.clock)

    assert isinstance(tick, StreamTick)
    assert tick.source_type == SourceType.SYNTHETIC
    assert tick.provenance_ids
    assert isinstance(daily, DailyTelemetryLog)
    assert daily.source_type == SourceType.SYNTHETIC
    assert daily.provenance_ids


def test_simulation_state_parses_as_exact_brain_input() -> None:
    """Every generated Brain input sample must pass the strict backend contract."""
    controller = SimulationController()
    raw = simulation_state_to_input(controller, "A1")
    assert raw["astronaut_id"] == "astro-01"
    sample = parse_sample(raw)
    assert sample.astronaut_id == "astro-01"
    assert sample.radiation_dose_rate == raw["radiation_dose_rate"]


def test_brain_output_contains_frontend_contract_fields() -> None:
    """Brain output must contain the fields consumed by the frontend adapter."""
    raw = {
        "timestamp": "2026-04-22T08:00:00Z",
        "astronaut_id": "astro-01",
        "hr": 72,
        "spo2": 98,
        "bp": {"systolic": 118, "diastolic": 74},
        "temp_c": 36.6,
        "resp_rate": 14,
        "radiation_dose_rate": 20.0,
        "mission_day": 1,
        "mission_phase": "PHASE_1_ACUTE_ADAPTATION",
        "cabin_ppco2_mmhg": 2.3,
        "iop_mmhg": 16.0,
        "hrv_rmssd_ms": 42.0,
        "pvt_slowest10_rt_ms": 300.0,
      }
    output = Brain().process(raw)
    for key in (
        "timestamp", "astronautId", "alertLevel", "news2Score", "activeFlags",
        "flagDetails", "likelyConditions", "doctorRecommendation", "doctorSource",
        "bodySystems", "plans",
    ):
        assert key in output


def test_frontend_brain_tick_has_required_fields() -> None:
    """The existing frontend adapter must emit the zod contract's required fields."""
    raw = {
        "timestamp": "2026-04-22T08:00:00Z",
        "astronaut_id": "astro-01",
        "hr": 118,
        "spo2": 91,
        "bp": {"systolic": 88, "diastolic": 56},
        "temp_c": 38.2,
        "resp_rate": 25,
        "radiation_dose_rate": 1450.0,
        "mission_day": 12,
        "mission_phase": "PHASE_1_ACUTE_ADAPTATION",
      }
    output = Brain().process(raw)
    tick = to_brain_tick(output, raw, seq=1)
    assert tick["timestamp"] == output["timestamp"]
    assert tick["alertLevel"] == output["alertLevel"]
    assert tick["activeFlags"]
    assert tick["rawVitals"]["hr"] == 118
    assert tick["rawVitals"]["radiation_dose_rate"] == 1450.0
    assert tick["doctorRecommendation"] == output["doctorRecommendation"]


def test_public_astronaut_mapping_is_stable() -> None:
    """Simulation IDs map deterministically to frontend astronaut IDs."""
    assert public_astronaut_id("A1") == "astro-01"
    assert public_astronaut_id("A2") == "astro-02"
