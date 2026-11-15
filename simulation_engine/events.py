"""Контракты симуляции, специфичные для Simulation Agent.

Эти модели не изменяют общие контракты Architect. `SimulationEvent` является
аддитивным и может быть отображён Backend Agent в собственную таблицу событий.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SimulationEvent(BaseModel):
    """Одно событие симуляции."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(..., min_length=1)
    timestamp: str = Field(..., description="ISO-8601 UTC, e.g. 2026-04-22T08:00:00Z")
    mission_time_seconds: int = Field(..., ge=0)
    mission_day: int = Field(..., ge=1)
    astronaut_id: str | None = None
    event_type: Literal[
        "MISSION_START",
        "MISSION_PAUSE",
        "MISSION_RESUME",
        "MISSION_STOP",
        "MISSION_RESET",
        "SCENARIO_STARTED",
        "SCENARIO_PROGRESS",
        "SCENARIO_TERMINATED",
        "SCENARIO_COMPLETED",
        "COUNTERMEASURE_APPLIED",
        "DAILY_SLEEP_COMPLETED",
        "STATE_LIMIT_REACHED",
        "WHAT_IF_COMPLETED",
    ]
    scenario_id: str | None = None
    severity: Literal["INFO", "LOW", "MODERATE", "HIGH", "CRITICAL"] = "INFO"
    description: str
    affected_systems: list[str] = Field(default_factory=list)
    provenance: dict[str, object] = Field(default_factory=dict)


class SimulationStatus(BaseModel):
    """Публичный статус симуляции."""

    model_config = ConfigDict(extra="forbid")

    mission_status: Literal["CREATED", "RUNNING", "PAUSED", "STOPPED", "COMPLETED"]
    mission_time_seconds: int = Field(..., ge=0)
    mission_day: int = Field(..., ge=1)
    mission_phase: Literal["PHASE_1_ACUTE_ADAPTATION", "PHASE_2_LONG_DURATION"]
    simulation_speed: float = Field(..., gt=0.0)
    active_scenarios: list[str] = Field(default_factory=list)
    active_astronauts: list[str] = Field(default_factory=list)
    current_model_version: str
    random_seed: int = Field(..., ge=0)
    internal_step_seconds: float = Field(..., gt=0.0)
    output_step_seconds: float = Field(..., gt=0.0)
    source_type: Literal["SYNTHETIC"] = "SYNTHETIC"


__all__ = ["SimulationEvent", "SimulationStatus"]
