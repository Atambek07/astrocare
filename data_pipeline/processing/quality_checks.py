"""Контроль качества: пропуски, единицы, диапазоны, время, полнота.

Ключевое правило медицинской безопасности: неполные данные не могут быть
автоматически классифицированы как GREEN.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from shared.contracts import QualityStatus  # noqa: E402
from data_pipeline.processing.normalization import normalize_timestamp  # noqa: E402

MIN_DATA_COMPLETENESS_PCT: float = 70.0
MIN_BASELINE_SAMPLE_DAYS: int = 7
MAX_PLAUSIBLE_GAP_SECONDS: int = 300
PHYSIOLOGICAL_RANGES: dict[str, tuple[float, float]] = {
    "hr": (20.0, 250.0),
    "hrv_rmssd": (0.0, 300.0),
    "spo2": (50.0, 100.0),
    "systolic_bp": (50.0, 260.0),
    "diastolic_bp": (20.0, 160.0),
    "temp_c": (30.0, 45.0),
    "resp_rate": (4.0, 60.0),
    "cabin_ppco2": (0.0, 20.0),
    "radiation_dose_rate": (0.0, 1000.0),
    "iop_mmhg": (0.0, 60.0),
    "pvt_slowest10_rt": (100.0, 1000.0),
}


@dataclass(frozen=True)
class QualityReport:
    """Результат проверки качества одного набора или записи."""

    completeness_pct: float
    missing_metrics: list[str] = field(default_factory=list)
    invalid_units: list[str] = field(default_factory=list)
    out_of_range_metrics: list[str] = field(default_factory=list)
    quality_status: QualityStatus = QualityStatus.NOT_ASSESSED
    messages: list[str] = field(default_factory=list)


def check_completeness(required: list[str], observed: dict[str, object]) -> QualityReport:
    """Рассчитать полноту и список отсутствующих метрик."""
    if not required:
        return QualityReport(0.0, [], [], [], QualityStatus.NOT_ASSESSED, ["No required metrics."])
    missing = [
        metric
        for metric in required
        if observed.get(metric) is None
        or (isinstance(observed.get(metric), str) and not str(observed.get(metric)).strip())
    ]
    completeness = 100.0 * (len(required) - len(missing)) / len(required)
    status = QualityStatus.VALID if not missing else QualityStatus.MISSING
    messages = [] if not missing else [f"Missing required metrics: {', '.join(missing)}."]
    return QualityReport(completeness, missing, [], [], status, messages)


def check_units(metrics: dict[str, str | None]) -> QualityReport:
    """Проверить единицы и пометить INVALID_UNIT без попыток угадать масштаб."""
    invalid = [name for name, unit in metrics.items() if unit is None or not str(unit).strip()]
    status = QualityStatus.VALID if not invalid else QualityStatus.INVALID_UNIT
    messages = [] if not invalid else [f"Missing or invalid units: {', '.join(invalid)}."]
    return QualityReport(100.0 if not metrics else 100.0 * (len(metrics) - len(invalid)) / len(metrics), [], invalid, [], status, messages)


def check_ranges(values: dict[str, float | None]) -> QualityReport:
    """Проверить физиологические диапазоны, не исправляя значения автоматически."""
    out_of_range: list[str] = []
    checked = 0
    for metric, value in values.items():
        if value is None or metric not in PHYSIOLOGICAL_RANGES:
            continue
        checked += 1
        lower, upper = PHYSIOLOGICAL_RANGES[metric]
        if not math.isfinite(value) or value < lower or value > upper:
            out_of_range.append(metric)
    status = QualityStatus.VALID if not out_of_range else QualityStatus.SUSPECT
    messages = [] if not out_of_range else [f"Values outside plausible range: {', '.join(out_of_range)}."]
    total = checked or 1
    return QualityReport(100.0 * (checked - len(out_of_range)) / total, [], [], out_of_range, status, messages)


def check_timestamps(timestamps: list[str | None]) -> QualityReport:
    """Проверить монотонность и разрывы; отсутствие времени — MISSING, не now()."""
    if not timestamps:
        return QualityReport(0.0, ["timestamp"], [], [], QualityStatus.MISSING, ["No timestamps supplied."])
    parsed = [normalize_timestamp(value) for value in timestamps]
    missing = sum(1 for value in parsed if value is None)
    if missing:
        return QualityReport(
            100.0 * (len(parsed) - missing) / len(parsed),
            ["timestamp"],
            [],
            [],
            QualityStatus.MISSING,
            [f"{missing} timestamp(s) are missing or not absolute."],
        )
    from datetime import datetime

    dates = [datetime.fromisoformat(str(value).replace("Z", "+00:00")) for value in parsed]
    non_monotonic = sum(1 for left, right in zip(dates, dates[1:]) if right < left)
    gaps = [
        int((right - left).total_seconds())
        for left, right in zip(dates, dates[1:])
        if (right - left).total_seconds() > MAX_PLAUSIBLE_GAP_SECONDS
    ]
    if non_monotonic or gaps:
        return QualityReport(
            100.0,
            [],
            [],
            [],
            QualityStatus.VALID_WITH_WARNINGS,
            [
                f"Non-monotonic steps: {non_monotonic}.",
                f"Gaps above {MAX_PLAUSIBLE_GAP_SECONDS}s: {len(gaps)}.",
            ],
        )
    return QualityReport(100.0, [], [], [], QualityStatus.VALID, [])


def check_baseline_sufficiency(sample_days: int, sample_size: int) -> QualityStatus:
    """Вернуть INSUFFICIENT_BASELINE, если наблюдений мало для расчёта."""
    if sample_days < MIN_BASELINE_SAMPLE_DAYS or sample_size < MIN_BASELINE_SAMPLE_DAYS:
        return QualityStatus.INSUFFICIENT_BASELINE
    return QualityStatus.VALID


def assess_quality(reports: list[QualityReport]) -> QualityReport:
    """Свести проверки в единый QualityStatus по худшему результату."""
    if not reports:
        return QualityReport(0.0, [], [], [], QualityStatus.NOT_ASSESSED, ["No quality reports."])
    severity = {
        QualityStatus.VALID: 0,
        QualityStatus.VALID_WITH_WARNINGS: 1,
        QualityStatus.ACCEPTED: 2,
        QualityStatus.VALIDATED: 3,
        QualityStatus.NOT_ASSESSED: 4,
        QualityStatus.INSUFFICIENT_BASELINE: 5,
        QualityStatus.MISSING: 6,
        QualityStatus.SUSPECT: 7,
        QualityStatus.INVALID_UNIT: 8,
    }
    worst = max(reports, key=lambda report: severity.get(report.quality_status, 99))
    completeness = min(report.completeness_pct for report in reports)
    missing = sorted({metric for report in reports for metric in report.missing_metrics})
    invalid_units = sorted({metric for report in reports for metric in report.invalid_units})
    out_of_range = sorted({metric for report in reports for metric in report.out_of_range_metrics})
    messages = [message for report in reports for message in report.messages]
    return QualityReport(completeness, missing, invalid_units, out_of_range, worst.quality_status, messages)
