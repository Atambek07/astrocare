"""Извлечение признаков из разнородных NASA-датасетов.

Омиксные, лабораторные и environmental наборы не обязаны содержать временные
ряды. Извлечение признаков сохраняет provenance каждого значения.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from shared.contracts import (  # noqa: E402
    DailyTelemetryLog,
    LaboratoryPanel,
    ProvenanceRecord,
    QualityStatus,
)
from data_pipeline.common import compute_statistics, utc_now_iso  # noqa: E402

FEATURE_SCHEMA_VERSION: str = "1.0.0"


def extract_daily_features(
    normalized_rows: list[dict[str, object]],
    *,
    subject_id: str,
    study_id: str,
) -> list[DailyTelemetryLog]:
    """Построить суточные признаки только там, где есть подтверждённые измерения."""
    output: list[DailyTelemetryLog] = []
    for row in normalized_rows:
        try:
            output.append(DailyTelemetryLog.model_validate(row))
        except Exception as exc:
            raise ValueError(f"Invalid daily feature for {subject_id}/{study_id}: {exc}") from exc
    return output


def extract_lab_features(
    normalized_rows: list[dict[str, object]],
    *,
    subject_id: str,
    study_id: str,
    panel_type: str,
) -> list[LaboratoryPanel]:
    """Извлечь лабораторные панели из CBC/CMP/cytokine наборов OSDR.

    Ожидаемая форма строки: `panel_id`, `collected_at_utc`, `mission_day`,
    `results` (analyte -> float), `interpretation`, `data_completeness_pct`,
    `provenance_ids`. Отсутствующие значения не заполняются.
    """
    panels: list[LaboratoryPanel] = []
    for row in normalized_rows:
        payload = dict(row)
        payload.setdefault("astronaut_id", subject_id)
        payload.setdefault("panel_type", panel_type)
        payload.setdefault("source_type", "NASA_REAL")
        panels.append(LaboratoryPanel.model_validate(payload))
    return panels


def extract_baseline_features(
    daily_rows: Sequence[DailyTelemetryLog],
    *,
    mission_phase: str,
) -> dict[str, float]:
    """Рассчитать фазовые статистики только по валидным наблюдениям."""
    rows = [row for row in daily_rows if row.mission_phase.value == mission_phase]
    metrics = {
        "mean_hr": [row.hr for row in rows],
        "mean_hrv_rmssd": [row.hrv_rmssd for row in rows],
        "mean_pvt_slowest10_rt": [row.pvt_slowest10_rt for row in rows],
        "mean_sleep_efficiency_pct": [row.sleep_efficiency_pct for row in rows],
        "mean_cabin_ppco2": [row.cabin_ppco2 for row in rows],
    }
    output: dict[str, float] = {}
    for name, values in metrics.items():
        stats = compute_statistics(values)
        if stats["mean"] is not None:
            output[name] = float(stats["mean"])
    return output


def derive_mfi_inputs(
    daily: DailyTelemetryLog,
    baseline: dict[str, float],
) -> dict[str, float | None]:
    """Подготовить входы MFI; отсутствующие значения остаются None."""
    return {
        "hr": daily.hr,
        "hrv_rmssd": daily.hrv_rmssd,
        "pvt_slowest10_rt": daily.pvt_slowest10_rt,
        "sleep_efficiency_pct": daily.sleep_efficiency_pct,
        "cabin_ppco2": daily.cabin_ppco2,
        "baseline_hr": baseline.get("mean_hr"),
        "baseline_hrv_rmssd": baseline.get("mean_hrv_rmssd"),
        "baseline_pvt_slowest10_rt": baseline.get("mean_pvt_slowest10_rt"),
    }


def build_feature_provenance(
    metric_key: str,
    original: ProvenanceRecord,
    *,
    normalized_value: float | None,
    method: str,
    quality_status: QualityStatus,
) -> ProvenanceRecord:
    """Создать NASA_DERIVED provenance-запись с ссылкой derived_from."""
    child_id = f"{original.provenance_id}-DERIVED-{metric_key}"
    return original.model_copy(
        update={
            "provenance_id": child_id,
            "source_type": original.source_type,
            "metric_key": metric_key,
            "normalized_value": normalized_value,
            "processing_method": method,
            "quality_status": quality_status,
            "derived_from": [original.provenance_id],
            "processing_version": FEATURE_SCHEMA_VERSION,
            "processing_timestamp": utc_now_iso(),
        }
    )


def assert_no_fabricated_values(records: Sequence[ProvenanceRecord]) -> None:
    """Проверить, что отсутствующие поля не заполнены выдуманными значениями."""
    for record in records:
        if record.source_type.value == "SYNTHETIC":
            if record.nasa_study_id or record.subject_id:
                raise ValueError(f"Synthetic record claims NASA identity: {record.provenance_id}")
            continue
        if record.quality_status == QualityStatus.MISSING and record.normalized_value is not None:
            raise ValueError(f"MISSING record contains a normalized value: {record.provenance_id}")
        if record.measurement_timestamp is None and record.collection_timepoint is None:
            # Для относительных timepoint это нормально; для абсолютной телеметрии — нет.
            if record.metric_key in {"hr", "hrv_rmssd", "spo2", "cabin_ppco2"}:
                raise ValueError(f"Physiological record lacks a time reference: {record.provenance_id}")
