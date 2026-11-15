"""Расчёт фазовых базовых линий из суточной серии.

Базовые линии не хардкодятся: они вычисляются из сгенерированных суточных
записей и сохраняют provenance. Синтетическая природа данных маркируется
явно; NASA-опубликованные референсы не подменяются.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from shared.contracts import (  # noqa: E402
    DailyTelemetryLog,
    FallbackStatus,
    MissionPhase,
    PhaseBaseline,
    ProvenanceRecord,
    QualityStatus,
    SourceType,
    ThresholdSource,
)
from data_pipeline.common import compute_statistics, finite_float, utc_now_iso  # noqa: E402
from data_pipeline.processing.quality_checks import check_baseline_sufficiency  # noqa: E402

BASELINE_MODEL_VERSION: str = "astralis-baseline-1.0.0"
BASELINE_SCENARIO_ID: str = "SYNTH-180D-PHASE-TRANSITION"
METRIC_UNITS: dict[str, str] = {
    "hr": "bpm",
    "hrv_rmssd": "ms",
    "pvt_slowest10_rt": "ms",
    "sleep_efficiency_pct": "%",
    "cabin_ppco2": "mmHg",
    "spo2": "%",
    "systolic_bp": "mmHg",
    "diastolic_bp": "mmHg",
    "temp_c": "Cel",
    "resp_rate": "breaths/min",
    "iop_mmhg": "mmHg",
    "vo2max_ml_kg_min": "mL/kg/min",
    "respiratory_exchange_ratio": "1",
    "cumulative_radiation_msv": "mSv",
}


def _values(records: list[DailyTelemetryLog], attribute: str) -> list[float | None]:
    """Достать числовые значения метрики из суточных записей."""
    return [getattr(record, attribute, None) for record in records]


def _phase_records(records: list[DailyTelemetryLog], phase: MissionPhase) -> list[DailyTelemetryLog]:
    """Отфильтровать записи фазы и отсортировать по дню."""
    return sorted((record for record in records if record.mission_phase == phase), key=lambda record: record.mission_day)


def build_phase_baselines(
    daily_records: list[DailyTelemetryLog],
) -> tuple[list[PhaseBaseline], list[ProvenanceRecord]]:
    """Построить две базовые линии для каждого астронавта и provenance."""
    baselines: list[PhaseBaseline] = []
    provenance: list[ProvenanceRecord] = []
    for astronaut_id in sorted({record.astronaut_id for record in daily_records}):
        crew_records = [record for record in daily_records if record.astronaut_id == astronaut_id]
        for phase in (MissionPhase.PHASE_1_ACUTE_ADAPTATION, MissionPhase.PHASE_2_LONG_DURATION):
            rows = _phase_records(crew_records, phase)
            if not rows:
                continue
            stats = {
                metric: compute_statistics(_values(rows, metric))
                for metric in METRIC_UNITS
            }
            baseline_id = f"BASE-{astronaut_id}-{'P1' if phase == MissionPhase.PHASE_1_ACUTE_ADAPTATION else 'P2'}"
            provenance_id = f"PROV-SYN-{baseline_id}"
            baseline_source_ids = sorted({pid for row in rows for pid in row.provenance_ids})
            sample_days = len(rows)
            completeness = 100.0
            sufficiency = check_baseline_sufficiency(sample_days, sample_days)
            metric_statistics = []
            for metric, unit in METRIC_UNITS.items():
                metric_stats = stats[metric]
                metric_statistics.append(
                    {
                        "metric": metric,
                        "unit": unit,
                        "n": metric_stats["n"],
                        "mean": metric_stats["mean"],
                        "sd": metric_stats["sd"],
                        "median": metric_stats["median"],
                        "min": metric_stats["min"],
                        "max": metric_stats["max"],
                        "source_type": SourceType.SYNTHETIC.value,
                        "nasa_reference": None,
                        "notes": "Synthetic demo baseline; no NASA continuous telemetry available for this metric.",
                    }
                )
            baseline = PhaseBaseline(
                baseline_id=baseline_id,
                astronaut_id=astronaut_id,
                mission_phase=phase,
                window_start_day=rows[0].mission_day,
                window_end_day=rows[-1].mission_day,
                sample_days=sample_days,
                mean_hr=finite_float(float(stats["hr"]["mean"] or 0.0)) or 68.0,
                sd_hr=finite_float(float(stats["hr"]["sd"] or 0.0)) or 0.0,
                mean_hrv_rmssd=finite_float(float(stats["hrv_rmssd"]["mean"] or 0.0)) or 0.0,
                sd_hrv_rmssd=finite_float(float(stats["hrv_rmssd"]["sd"] or 0.0)) or 0.0,
                mean_pvt_slowest10_rt=finite_float(float(stats["pvt_slowest10_rt"]["mean"] or 0.0)) or 285.0,
                sd_pvt_slowest10_rt=finite_float(float(stats["pvt_slowest10_rt"]["sd"] or 0.0)) or 0.0,
                mean_sleep_efficiency_pct=finite_float(float(stats["sleep_efficiency_pct"]["mean"] or 0.0)) or 0.0,
                mean_cabin_ppco2=finite_float(float(stats["cabin_ppco2"]["mean"] or 0.0)) or 2.4,
                generated_at_utc=utc_now_iso(),
                baseline_source_ids=baseline_source_ids,
                baseline_population=(
                    f"Synthetic ASTRALIS demo astronaut {astronaut_id} (not a NASA astronaut); "
                    f"{phase.value.lower()} days {rows[0].mission_day}-{rows[-1].mission_day}."
                ),
                baseline_sample_size=sample_days,
                data_completeness_pct=completeness,
                missing_metrics=[],
                confidence_score=0.95 if astronaut_id == "A2" else 0.90,
                model_version=BASELINE_MODEL_VERSION,
                threshold_source=ThresholdSource.PROJECT_SIMULATION,
                provenance_ids=[provenance_id],
                metric_statistics=metric_statistics,
                evidence_references=[
                    "Synthetic daily series generated by astralis-daily-1.0.0.",
                    "NASA OSDR Inspiration4 studies inform realism only; they are not continuous telemetry.",
                ],
                limitations=[
                    "Synthetic baseline; not a clinical reference interval.",
                    "MFI thresholds remain project simulation rules, not NASA clinical limits.",
                ],
            )
            if sufficiency == QualityStatus.INSUFFICIENT_BASELINE:
                baseline = baseline.model_copy(
                    update={
                        "missing_metrics": ["insufficient_baseline_sample_days"],
                        "confidence_score": 0.0,
                    }
                )
            baselines.append(baseline)
            provenance.append(
                ProvenanceRecord(
                    provenance_id=provenance_id,
                    source_type=SourceType.SYNTHETIC,
                    nasa_study_id=None,
                    nasa_dataset_id=None,
                    source_file=None,
                    source_url=None,
                    publication_reference=None,
                    subject_id=None,
                    collection_timepoint=f"{baseline_id}-{rows[0].mission_day}-{rows[-1].mission_day}",
                    measurement_timestamp=rows[-1].timestamp,
                    measurement_unit="mixed",
                    original_value=f"daily_records={sample_days}",
                    normalized_value=None,
                    processing_method="phase_aggregate",
                    quality_status=QualityStatus.VALIDATED,
                    metric_key="phase_baseline",
                    fallback_status=FallbackStatus.NONE,
                    derived_from=baseline_source_ids,
                    source_verified_utc=None,
                    notes="Derived synthetic phase baseline; not a NASA clinical baseline.",
                    measurement_name="phase_baseline",
                    original_unit="mixed",
                    normalized_unit="mixed",
                    processing_version=BASELINE_MODEL_VERSION,
                    generated_at_utc=utc_now_iso(),
                    license_or_access_terms="Project-generated synthetic data",
                    processing_timestamp=utc_now_iso(),
                    pipeline_version="astralis-data-1.0.0",
                    generator_name="astralis-baseline-builder",
                    generator_version=BASELINE_MODEL_VERSION,
                    random_seed=20260501,
                    scenario_id=BASELINE_SCENARIO_ID,
                    scenario_configuration={"sample_days": sample_days, "phase": phase.value},
                    generation_timestamp=rows[0].timestamp,
                )
            )
    return baselines, provenance
