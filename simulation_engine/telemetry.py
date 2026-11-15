"""Сериализация состояний симуляции в общие контракты.

Все записи телеметрии имеют `source_type = SYNTHETIC` и минимум один
provenance ID. Сериализация не выполняет медицинских расчётов.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from .clock import MissionClock  # noqa: E402
from shared.contracts import DailyTelemetryLog, MissionPhase, SourceType, StreamTick  # noqa: E402
from .state import AstronautState, CountermeasureState, EnvironmentState, PhysiologicalState  # noqa: E402


def _phase_enum(phase: str) -> MissionPhase:
    """Преобразовать строку фазы в enum контракта."""
    return MissionPhase(phase)


def make_provenance_id(prefix: str, astronaut_id: str, seconds: int) -> str:
    """Создать стабильный provenance ID."""
    return f"PROV-SIM-{astronaut_id}-{prefix}-{seconds:09d}"


def to_stream_tick(
    state: AstronautState,
    environment: EnvironmentState,
    clock: MissionClock,
    *,
    seconds: int | None = None,
) -> StreamTick:
    """Преобразовать состояние в `StreamTick`."""
    physiology: PhysiologicalState = state.physiology
    countermeasure: CountermeasureState = state.countermeasure
    mission_seconds = clock.elapsed_seconds if seconds is None else int(seconds)
    return StreamTick(
        timestamp=clock.timestamp_utc if seconds is None else _timestamp_at(clock, mission_seconds),
        mission_day=clock.mission_day,
        mission_phase=_phase_enum(clock.mission_phase),
        astronaut_id=state.astronaut_id,
        source_type=SourceType.SYNTHETIC,
        hr=physiology.hr,
        hrv_rmssd=physiology.hrv_rmssd,
        spo2=physiology.spo2,
        systolic_bp=int(round(physiology.sbp)),
        diastolic_bp=int(round(physiology.dbp)),
        temp_c=physiology.temp_c,
        resp_rate=physiology.resp_rate,
        iop_mmhg=physiology.iop_mmhg,
        cabin_ppco2=environment.cabin_ppco2_mmhg,
        radiation_dose_rate=environment.radiation_dose_rate_msv_h,
        pvt_slowest10_rt=physiology.pvt_slowest10_rt_ms,
        provenance_ids=[
            make_provenance_id("STREAM", state.astronaut_id, mission_seconds),
        ],
    )


def to_daily_log(
    state: AstronautState,
    environment: EnvironmentState,
    clock: MissionClock,
    *,
    seconds: int | None = None,
) -> DailyTelemetryLog:
    """Преобразовать состояние в `DailyTelemetryLog`."""
    physiology: PhysiologicalState = state.physiology
    countermeasure: CountermeasureState = state.countermeasure
    mission_seconds = clock.elapsed_seconds if seconds is None else int(seconds)
    return DailyTelemetryLog(
        timestamp=_timestamp_at(clock, mission_seconds),
        mission_day=clock.mission_day,
        mission_phase=_phase_enum(clock.mission_phase),
        astronaut_id=state.astronaut_id,
        source_type=SourceType.SYNTHETIC,
        hr=physiology.hr,
        hrv_rmssd=physiology.hrv_rmssd,
        spo2=physiology.spo2,
        systolic_bp=int(round(physiology.sbp)),
        diastolic_bp=int(round(physiology.dbp)),
        temp_c=physiology.temp_c,
        resp_rate=physiology.resp_rate,
        cabin_ppco2=environment.cabin_ppco2_mmhg,
        radiation_dose_rate=environment.radiation_dose_rate_msv_h,
        iop_mmhg=physiology.iop_mmhg,
        pvt_slowest10_rt=physiology.pvt_slowest10_rt_ms,
        sleep_duration_h=physiology.sleep_duration_h,
        sleep_efficiency_pct=physiology.sleep_efficiency_pct,
        sleep_shift_active=physiology.sleep_shift_active,
        mood_stress_vas=physiology.mood_stress_vas,
        pvt_mean_rt_ms=physiology.pvt_mean_rt_ms,
        pvt_lapses_count=physiology.pvt_lapses_count,
        fluid_shift_index=physiology.fluid_shift_index,
        sans_visual_symptoms=physiology.sans_risk >= 0.6,
        daily_radiation_msv=environment.daily_radiation_msv,
        cumulative_radiation_msv=environment.cumulative_radiation_msv,
        ared_exercise_completed=countermeasure.ared_completed_today,
        vo2max_ml_kg_min=physiology.vo2max,
        respiratory_exchange_ratio=physiology.respiratory_exchange_ratio,
        provenance_ids=[
            make_provenance_id("DAILY", state.astronaut_id, mission_seconds),
        ],
    )


def _timestamp_at(clock: MissionClock, seconds: int) -> str:
    """Получить UTC-таймстемп для произвольного миссионного времени."""
    from datetime import UTC, datetime

    return datetime.fromtimestamp(clock.start_utc.timestamp() + seconds, tz=UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "make_provenance_id",
    "to_daily_log",
    "to_stream_tick",
]
