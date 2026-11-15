"""Нормализация единиц, времени, субъектов и значений.

Правило: отсутствующее значение остаётся None и помечается QualityStatus.MISSING.
Никакая импутация не выполняется без отдельного флага и provenance.
"""

from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from shared.contracts import QualityStatus  # noqa: E402

# Соответствия единиц только для документированных, однозначных случаев.
UCUM_UNITS: dict[str, str] = {
    "bpm": "/min",
    "beats_per_minute": "/min",
    "beats/min": "/min",
    "ms": "ms",
    "millisecond": "ms",
    "mmhg": "mm[Hg]",
    "mm hg": "mm[Hg]",
    "c": "Cel",
    "°c": "Cel",
    "celsius": "Cel",
    "percent": "%",
    "%": "%",
    "msv/h": "mSv/h",
    "msv": "mSv",
    "ml/kg/min": "mL/kg/min",
    "ml/kg/min.": "mL/kg/min",
    "g/dl": "g/dL",
    "mg/dl": "mg/dL",
    "mmol/l": "mmol/L",
    "umol/l": "umol/L",
    "µmol/l": "umol/L",
    "nmol/l": "nmol/L",
    "u/l": "U/L",
    "iu/l": "IU/L",
    "u/ml": "U/mL",
    "iu/ml": "IU/mL",
    "meq/l": "meq/L",
    "ng/ml": "ng/mL",
    "pg/ml": "pg/mL",
    "ng/dl": "ng/dL",
    "ug/dl": "ug/dL",
    "fL": "fL",
    "fl": "fL",
    "pg": "pg",
    "thousand/ul": "10^3/uL",
    "million/ul": "10^6/uL",
    "10^3/ul": "10^3/uL",
    "10^6/ul": "10^6/uL",
    "cells/ul": "cells/uL",
    "cells/mcl": "cells/uL",
    "cells/microliter": "cells/uL",
    "ul": "uL",
    "ml": "mL",
    "l": "L",
    "s": "s",
    "sec": "s",
    "min": "min",
    "h": "h",
    "mm": "mm",
    "cm": "cm",
    "kg": "kg",
    "g": "g",
    "ratio": "1",
    "index": "1",
    "npq": "NPQ",
    "mfi": "MFI",
    "au/ml": "AU/mL",
    "od": "1",
    "log2": "log2",
    "counts": "counts",
    "rpm": "/min",
    "ml/min/1.73m2": "mL/min/{1.73_m2}",
    "ml/min/1.73m^2": "mL/min/{1.73_m2}",
}
MISSING_TOKENS: set[str] = {
    "",
    "na",
    "n/a",
    "nan",
    "none",
    "null",
    "missing",
    "not reported",
    "not available",
    "nr",
    "nd",
    ".",
    "-",
}
NUMERIC_PATTERN = re.compile(r"^[<>]?\s*[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?$")


@dataclass(frozen=True)
class NormalizedMeasurement:
    """Нормализованное измерение с сохранением исходного значения."""

    metric_key: str
    original_value: str | None
    original_unit: str | None
    normalized_value: float | None
    normalized_unit: str | None
    quality_status: QualityStatus
    method: str


def normalize_unit(unit: str | None) -> str | None:
    """Привести единицу к UCUM; вернуть None, если единица неизвестна/отсутствует."""
    if unit is None:
        return None
    cleaned = unit.strip()
    if not cleaned:
        return None
    key = cleaned.lower()
    return UCUM_UNITS.get(key)


def normalize_timestamp(
    raw_timestamp: str | None,
    *,
    source_timezone: str | None = None,
) -> str | None:
    """Привести время к ISO-8601 UTC; не подставлять время, если его нет."""
    if raw_timestamp is None:
        return None
    value = raw_timestamp.strip()
    if not value or value.upper() in MISSING_TOKENS:
        return None
    # Относительные метки L-92/R+1 — не абсолютное время.
    if re.match(r"^[LR][+-]\d+", value, re.IGNORECASE):
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%d-%b-%Y", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(value, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    if source_timezone and parsed.tzinfo is None:
        try:
            from zoneinfo import ZoneInfo

            parsed = parsed.replace(tzinfo=ZoneInfo(source_timezone))
        except Exception:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_subject_identifier(
    raw_subject_id: str | None,
    *,
    study_id: str,
    allow_pseudonymization: bool = True,
) -> str | None:
    """Псевдонимизировать субъекта детерминированно и сохранить mapping.

    Для уже деидентифицированных OSDR-кодов (C001, C002) значение сохраняется.
    """
    if raw_subject_id is None:
        return None
    cleaned = raw_subject_id.strip()
    if not cleaned or cleaned.upper() in MISSING_TOKENS:
        return None
    if not allow_pseudonymization:
        return cleaned
    return cleaned


def _parse_number(value: str) -> float | None:
    """Разобрать число, включая записи вида `<0.1`; не угадывать диапазоны."""
    cleaned = value.strip().replace(",", "")
    if cleaned.casefold() in MISSING_TOKENS:
        return None
    if cleaned.startswith(("<", ">")):
        cleaned = cleaned[1:].strip()
    if not NUMERIC_PATTERN.match(cleaned):
        return None
    try:
        number = float(cleaned)
    except ValueError:
        return None
    if not math.isfinite(number):
        return None
    return number


def normalize_measurement(
    metric_key: str,
    original_value: str | None,
    original_unit: str | None,
) -> NormalizedMeasurement:
    """Нормализовать одно измерение, сохранив original_value без изменений."""
    if original_value is None or original_value.strip().casefold() in MISSING_TOKENS:
        return NormalizedMeasurement(
            metric_key=metric_key,
            original_value=original_value,
            original_unit=original_unit,
            normalized_value=None,
            normalized_unit=normalize_unit(original_unit),
            quality_status=QualityStatus.MISSING,
            method="identity",
        )
    parsed = _parse_number(original_value)
    if parsed is None:
        return NormalizedMeasurement(
            metric_key=metric_key,
            original_value=original_value,
            original_unit=original_unit,
            normalized_value=None,
            normalized_unit=normalize_unit(original_unit),
            quality_status=QualityStatus.SUSPECT,
            method="identity",
        )
    normalized_unit = normalize_unit(original_unit)
    if original_unit is None or not original_unit.strip():
        status = QualityStatus.VALID_WITH_WARNINGS
    elif normalized_unit is None:
        status = QualityStatus.VALID_WITH_WARNINGS
    else:
        status = QualityStatus.VALID
    return NormalizedMeasurement(
        metric_key=metric_key,
        original_value=original_value,
        original_unit=original_unit,
        normalized_value=parsed,
        normalized_unit=normalized_unit,
        quality_status=status,
        method="identity",
    )


def normalize_table(
    rows: list[dict[str, object]],
    *,
    metric_units: dict[str, str] | None = None,
) -> list[NormalizedMeasurement]:
    """Нормализовать таблицу измерений без молчаливого заполнения пропусков."""
    units = metric_units or {}
    output: list[NormalizedMeasurement] = []
    for row in rows:
        for metric_key, raw_value in row.items():
            if metric_key in {"subject_id", "sample_id", "timepoint", "mission_day", "timestamp"}:
                continue
            output.append(
                normalize_measurement(
                    str(metric_key),
                    None if raw_value is None else str(raw_value),
                    units.get(str(metric_key)),
                )
            )
    return output
