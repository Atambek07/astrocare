"""Детерминированный генератор 180-дневной синтетической серии.

Серия не выдаётся за NASA-телеметрию. Она нужна для проверки фазовых
базовых линий, длительных трендов и офлайн-демонстрации.
"""

from __future__ import annotations

import math
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from shared.contracts import DailyTelemetryLog, MissionPhase, SourceType  # noqa: E402
from data_pipeline.common import finite_float  # noqa: E402
DAILY_DURATION_DAYS: int = 180
DAILY_START_UTC: str = "2026-04-22T08:00:00Z"
DAILY_SEED: int = 20260501
DAILY_GENERATOR_NAME: str = "astralis-daily-generator"
DAILY_GENERATOR_VERSION: str = "astralis-daily-1.0.0"
DAILY_SOURCE_TYPE: SourceType = SourceType.SYNTHETIC

DAILY_PROFILES: dict[str, dict[str, float]] = {
    "A1": {
        "hr": 72.0,
        "hrv_rmssd": 39.0,
        "sleep_efficiency_pct": 86.0,
        "pvt_slowest10_rt": 300.0,
        "cabin_ppco2": 2.45,
        "iop_mmhg": 17.2,
        "fluid_shift_index": 1.6,
        "vo2max_ml_kg_min": 44.0,
        "ared_adherence": 0.72,
        "mood_stress_vas": 29.0,
    },
    "A2": {
        "hr": 66.0,
        "hrv_rmssd": 50.0,
        "sleep_efficiency_pct": 91.8,
        "pvt_slowest10_rt": 282.0,
        "cabin_ppco2": 2.35,
        "iop_mmhg": 15.6,
        "fluid_shift_index": 0.45,
        "vo2max_ml_kg_min": 43.0,
        "ared_adherence": 0.96,
        "mood_stress_vas": 18.0,
    },
}


def _phase_for_day(day: int) -> MissionPhase:
    """Фаза 1 — дни 1-14, далее длительная фаза."""
    return MissionPhase.PHASE_1_ACUTE_ADAPTATION if day <= 14 else MissionPhase.PHASE_2_LONG_DURATION


def _daily_timestamp(day: int) -> str:
    """UTC-таймстемп суточного агрегата."""
    start = datetime.fromisoformat(DAILY_START_UTC.replace("Z", "+00:00"))
    return (start + timedelta(days=day - 1)).astimezone(UTC).isoformat().replace("+00:00", "Z")


def generate_daily_series(
    astronaut_id: str,
    *,
    seed: int = DAILY_SEED,
    days: int = DAILY_DURATION_DAYS,
) -> list[DailyTelemetryLog]:
    """Сгенерировать `days` суточных записей с детерминированным seed."""
    if astronaut_id not in DAILY_PROFILES:
        raise ValueError(f"Unknown synthetic astronaut: {astronaut_id}")
    if days < 1:
        raise ValueError("days must be positive")
    profile = DAILY_PROFILES[astronaut_id]
    rng = random.Random(seed + (17 if astronaut_id == "A1" else 29))
    records: list[DailyTelemetryLog] = []
    missed_ared_days = 0
    cumulative_radiation = 0.0
    for day in range(1, days + 1):
        phase = _phase_for_day(day)
        phase1 = phase == MissionPhase.PHASE_1_ACUTE_ADAPTATION
        is_a1 = astronaut_id == "A1"

        adherence = float(profile["ared_adherence"])
        if is_a1 and phase1:
            adherence = 0.80
        ared_completed = rng.random() < adherence
        if not ared_completed:
            missed_ared_days += 1

        # Гемодинамика: ранняя адаптация, затем частичное восстановление.
        hr_base = float(profile["hr"]) + (3.5 if phase1 else 1.0)
        hrv_base = float(profile["hrv_rmssd"]) - (3.5 if phase1 else 0.5)
        sleep_base = float(profile["sleep_efficiency_pct"]) - (2.0 if phase1 else 0.0)
        pvt_base = float(profile["pvt_slowest10_rt"]) + (8.0 if phase1 else 0.0)
        if is_a1 and 28 <= day <= 36:
            sleep_base -= 5.5
            pvt_base += 28.0
            hr_base += 4.0
            hrv_base -= 4.0
        hr = hr_base + rng.gauss(0.0, 2.8) + 2.0 * math.sin(day / 9.0)
        hrv = max(12.0, hrv_base + rng.gauss(0.0, 3.5) + 1.2 * math.sin(day / 7.0))
        sleep_efficiency = min(99.0, max(70.0, sleep_base + rng.gauss(0.0, 1.6)))
        pvt = max(180.0, pvt_base + rng.gauss(0.0, 12.0))
        cabin_ppco2 = max(1.8, float(profile["cabin_ppco2"]) + rng.gauss(0.0, 0.18))
        if is_a1 and day in {44, 45, 61, 62, 107}:
            cabin_ppco2 += 0.65
        iop = float(profile["iop_mmhg"]) + (0.7 if phase1 else 0.0) + rng.gauss(0.0, 0.55)
        fluid_shift = float(profile["fluid_shift_index"]) + (0.35 if phase1 else 0.0) + rng.gauss(0.0, 0.12)
        if is_a1 and 46 <= day <= 49:
            fluid_shift += 0.8
        visual_symptoms = bool(is_a1 and (46 <= day <= 49))
        shift_active = bool(is_a1 and 30 <= day <= 38)
        mood = float(profile["mood_stress_vas"]) - (5.0 if not phase1 else 0.0) + rng.gauss(0.0, 4.0)
        if is_a1 and 28 <= day <= 38:
            mood += 9.0

        daily_radiation = max(0.35, 0.48 + rng.gauss(0.0, 0.035))
        if day == 120:
            daily_radiation = 3.30
        elif day == 121:
            daily_radiation = 1.10
        cumulative_radiation += daily_radiation

        vo2max = max(0.0, float(profile["vo2max_ml_kg_min"]) - 0.18 * missed_ared_days)
        rq = 0.95 + rng.gauss(0.0, 0.018)
        if is_a1 and 118 <= day <= 125:
            rq = 0.895 + rng.gauss(0.0, 0.008)
        if is_a1 and not ared_completed and rq > 0.93:
            rq -= 0.006

        record = DailyTelemetryLog(
            timestamp=_daily_timestamp(day),
            mission_day=day,
            mission_phase=phase,
            astronaut_id=astronaut_id,
            source_type=DAILY_SOURCE_TYPE,
            hr=finite_float(hr) or 68.0,
            hrv_rmssd=finite_float(hrv) or 40.0,
            spo2=finite_float(min(100.0, max(90.0, 98.0 + rng.gauss(0.0, 0.45)))) or 98.0,
            systolic_bp=int(round(118 + rng.gauss(0.0, 5.0))),
            diastolic_bp=int(round(74 + rng.gauss(0.0, 4.0))),
            temp_c=finite_float(36.6 + rng.gauss(0.0, 0.12)) or 36.6,
            resp_rate=finite_float(14.0 + rng.gauss(0.0, 1.0)) or 14.0,
            iop_mmhg=finite_float(iop) or 16.0,
            cabin_ppco2=finite_float(cabin_ppco2) or 2.4,
            radiation_dose_rate=finite_float(daily_radiation / 24.0) or 0.02,
            pvt_slowest10_rt=finite_float(pvt) or 285.0,
            provenance_ids=[f"PROV-SYN-{astronaut_id}-DAY-{day:04d}"],
            sleep_duration_h=finite_float(max(4.5, min(9.5, 7.4 + rng.gauss(0.0, 0.45)))) or 7.4,
            sleep_efficiency_pct=finite_float(sleep_efficiency) or 88.0,
            sleep_shift_active=shift_active,
            mood_stress_vas=finite_float(min(100.0, max(0.0, mood))) or 20.0,
            pvt_mean_rt_ms=finite_float(max(180.0, pvt - 30.0 + rng.gauss(0.0, 8.0))) or 250.0,
            pvt_lapses_count=int(max(0, round((pvt - 280.0) / 40.0 + rng.gauss(0.0, 0.7)))),
            fluid_shift_index=finite_float(max(0.0, min(3.0, fluid_shift))) or 0.5,
            sans_visual_symptoms=visual_symptoms,
            daily_radiation_msv=finite_float(daily_radiation) or 0.48,
            cumulative_radiation_msv=finite_float(cumulative_radiation) or 0.48,
            ared_exercise_completed=ared_completed,
            vo2max_ml_kg_min=finite_float(vo2max) or 40.0,
            respiratory_exchange_ratio=finite_float(max(0.80, min(1.05, rq))) or 0.95,
        )
        records.append(record)
    return records


def build_daily_provenance_records(
    records: list[DailyTelemetryLog],
    *,
    seed: int = DAILY_SEED,
) -> list:
    """Создать provenance для каждой суточной записи."""
    from shared.contracts import FallbackStatus, ProvenanceRecord, QualityStatus
    from data_pipeline.common import utc_now_iso

    output: list[ProvenanceRecord] = []
    for record in records:
        output.append(
            ProvenanceRecord(
                provenance_id=record.provenance_ids[0],
                source_type=SourceType.SYNTHETIC,
                nasa_study_id=None,
                nasa_dataset_id=None,
                source_file=None,
                source_url=None,
                publication_reference=None,
                subject_id=None,
                collection_timepoint=f"MISSION-DAY-{record.mission_day}",
                measurement_timestamp=record.timestamp,
                measurement_unit="mixed",
                original_value="synthetic_daily_aggregate",
                normalized_value=None,
                processing_method="deterministic_daily_aggregate",
                quality_status=QualityStatus.VALIDATED,
                metric_key="daily_telemetry",
                fallback_status=FallbackStatus.NONE,
                derived_from=[],
                source_verified_utc=None,
                notes="Synthetic daily telemetry; not a real astronaut measurement.",
                measurement_name="daily_telemetry",
                original_unit="mixed",
                normalized_unit="mixed",
                processing_version=DAILY_GENERATOR_VERSION,
                generated_at_utc=utc_now_iso(),
                license_or_access_terms="Project-generated synthetic data",
                processing_timestamp=utc_now_iso(),
                pipeline_version="astralis-data-1.0.0",
                generator_name=DAILY_GENERATOR_NAME,
                generator_version=DAILY_GENERATOR_VERSION,
                random_seed=seed,
                scenario_id="SYNTH-180D-PHASE-TRANSITION",
                scenario_configuration={
                    "mission_day": record.mission_day,
                    "phase": record.mission_phase.value,
                },
                generation_timestamp=record.timestamp,
            )
        )
    return output


def generation_config(astronaut_ids: list[str] | None = None) -> dict[str, object]:
    """Полная конфигурация 180-дневной генерации для аудита."""
    return {
        "generator_name": DAILY_GENERATOR_NAME,
        "generator_version": DAILY_GENERATOR_VERSION,
        "seed": DAILY_SEED,
        "start_utc": DAILY_START_UTC,
        "days": DAILY_DURATION_DAYS,
        "astronaut_ids": astronaut_ids or list(DAILY_PROFILES),
        "phase_1_days": [1, 14],
        "phase_2_days": [15, 180],
        "radiation_model": {
            "gcr_daily_msv": 0.48,
            "spe_day": 120,
            "solar_particle_event_msv": 3.30,
            "mission_budget_msv": 600.0,
            "note": "600 mSv is a project demo planning budget, not an individualized NASA career limit.",
        },
        "vo2max_model": {
            "initial_a1": 44.0,
            "initial_a2": 43.0,
            "decline_per_missed_ared_day": 0.18,
            "ared_adherence_a1": 0.72,
            "ared_adherence_a2": 0.96,
            "flight_minimum": 36.5,
        },
        "source_type": DAILY_SOURCE_TYPE.value,
        "scenario_id": "SYNTH-180D-PHASE-TRANSITION",
        "notes": "Synthetic demo crew; not real NASA astronauts and not continuous NASA telemetry.",
    }
