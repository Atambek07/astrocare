"""Извлечение реальных лабораторных измерений из публичных файлов OSDR.

Поддерживаются длинные таблицы CBC/CMP/мультиплексов и широкие таблицы
AlamarPanel. Значения сохраняются как исходные строки; нормализация не
подменяет отсутствующие значения и не угадывает единицы.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from shared.contracts import (  # noqa: E402
    FallbackStatus,
    LaboratoryResult,
    ProvenanceRecord,
    QualityStatus,
    SourceType,
)
from data_pipeline.common import read_json, sha256_file, utc_now_iso  # noqa: E402
from data_pipeline.processing.normalization import normalize_measurement  # noqa: E402

RAW_DIR: Path = _PROJECT_ROOT / "data_bundle" / "raw" / "nasa"
MANIFEST_PATH: Path = _PROJECT_ROOT / "data_bundle" / "manifests" / "download_manifest.json"
PUBLICATION_BY_STUDY: dict[str, str] = {
    "OSD-569": "The Space Omics and Medical Atlas (SOMA) and international astronaut biobank (DOI: 10.1038/s41586-024-07639-y)",
    "OSD-570": "Single-cell multi-ome and immune profiles of the Inspiration4 crew (DOI: 10.1038/s41467-024-49211-2)",
    "OSD-571": "Secretome profiling after short-duration spaceflight (DOI: 10.1038/s41467-024-48841-w)",
    "OSD-572": "Longitudinal multi-omics analysis of host microbiome architecture (DOI: 10.1038/s41564-024-01635-8)",
    "OSD-573": "Longitudinal multi-omics analysis of host microbiome architecture (DOI: 10.1038/s41564-024-01635-8)",
    "OSD-575": "Collection of Biospecimens from the Inspiration4 Mission (DOI: 10.1038/s41467-024-48806-z)",
    "OSD-656": "Collection of Biospecimens from the Inspiration4 Mission (DOI: 10.1038/s41467-024-48806-z)",
}
LICENSE_TERMS = "OSDR public dataset. See the source URL for NASA data-use and attribution terms."


def _manifest_index() -> dict[tuple[str, str], dict[str, Any]]:
    """Индексировать скачанные файлы по (study_id, file_name)."""
    if not MANIFEST_PATH.exists():
        return {}
    loaded = read_json(MANIFEST_PATH)
    rows = loaded if isinstance(loaded, list) else []
    return {
        (str(row.get("study_id")), str(row.get("file_name"))): row
        for row in rows
        if isinstance(row, dict)
    }


def _metric_key(panel_type: str, analyte: str) -> str:
    """Построить стабильный английский metric key."""
    slug = re.sub(r"[^a-z0-9]+", "_", analyte.lower()).strip("_")
    return f"lab_{panel_type.lower()}_{slug}"


def _read_csv(path: Path) -> list[dict[str, str]]:
    """Прочитать CSV с BOM и вернуть строки как словари."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _numeric(value: str | None) -> float | None:
    """Разобрать число для reference interval без изменения исходного значения."""
    if value is None or not str(value).strip():
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _make_provenance(
    *,
    result_id: str,
    study_id: str,
    file_name: str,
    source_url: str,
    sha256: str,
    subject_id: str | None,
    timepoint: str | None,
    analyte: str,
    original_value: str | None,
    original_unit: str | None,
    normalized_value: float | None,
    quality: QualityStatus,
    dataset_id: str,
    assay_method: str,
) -> ProvenanceRecord:
    """Создать NASA_REAL provenance-запись для одного лабораторного значения."""
    return ProvenanceRecord(
        provenance_id=f"PROV-{result_id}",
        source_type=SourceType.NASA_REAL,
        nasa_study_id=study_id,
        nasa_dataset_id=dataset_id,
        source_file=file_name,
        source_url=source_url,
        publication_reference=PUBLICATION_BY_STUDY.get(study_id),
        subject_id=subject_id,
        collection_timepoint=timepoint,
        measurement_timestamp=None,
        measurement_unit=original_unit,
        original_value=original_value,
        normalized_value=normalized_value,
        processing_method="identity",
        quality_status=quality,
        metric_key=_metric_key(assay_method, analyte),
        fallback_status=FallbackStatus.NONE,
        derived_from=[],
        source_verified_utc=utc_now_iso(),
        notes="Public OSDR laboratory value; absolute collection time is not provided, relative label preserved.",
        source_publication=PUBLICATION_BY_STUDY.get(study_id),
        sample_id=None,
        measurement_name=analyte,
        original_unit=original_unit,
        normalized_unit=None,
        processing_version="lab-extractor-1.0.0",
        generated_at_utc=utc_now_iso(),
        source_file_sha256=sha256,
        license_or_access_terms=LICENSE_TERMS,
        download_timestamp=None,
        processing_timestamp=utc_now_iso(),
        pipeline_version="astralis-data-1.0.0",
        generator_name=None,
        generator_version=None,
        random_seed=None,
        scenario_id=None,
        scenario_configuration=None,
        generation_timestamp=None,
    )


def extract_long_lab(
    *,
    study_id: str,
    file_name: str,
    panel_type: str,
    sample_type: str,
    assay_method: str,
    analyte_column: str,
    value_column: str,
    unit_column: str,
    timepoint_column: str,
    subject_column: str,
    low_column: str | None = None,
    high_column: str | None = None,
) -> tuple[list[LaboratoryResult], list[ProvenanceRecord]]:
    """Извлечь длинную таблицу лабораторных измерений."""
    path = RAW_DIR / study_id / file_name
    if not path.exists():
        return [], []
    manifest = _manifest_index().get((study_id, file_name), {})
    source_url = str(manifest.get("source_url") or "")
    sha256 = str(manifest.get("sha256") or sha256_file(path))
    results: list[LaboratoryResult] = []
    provenance: list[ProvenanceRecord] = []
    for index, row in enumerate(_read_csv(path), start=1):
        analyte = str(row.get(analyte_column) or "").strip()
        if not analyte:
            continue
        raw_value = row.get(value_column)
        raw_unit = row.get(unit_column)
        normalized = normalize_measurement(analyte, raw_value, raw_unit)
        subject = str(row.get(subject_column) or "").strip() or None
        timepoint = str(row.get(timepoint_column) or "").strip() or None
        result_id = f"{study_id}-{panel_type}-{index:05d}"
        quality = normalized.quality_status
        if quality == QualityStatus.VALID and normalized.normalized_value is None:
            quality = QualityStatus.SUSPECT
        result = LaboratoryResult(
            result_id=result_id,
            test_name=analyte,
            value=normalized.normalized_value,
            original_value=None if raw_value is None else str(raw_value),
            unit=None if raw_unit is None else str(raw_unit),
            normalized_unit=normalized.normalized_unit,
            sample_type=sample_type,
            collection_timepoint=timepoint,
            subject_id=subject,
            source_study_id=study_id,
            source_file=file_name,
            reference_interval_low=_numeric(row.get(low_column)) if low_column else None,
            reference_interval_high=_numeric(row.get(high_column)) if high_column else None,
            assay_method=assay_method,
            quality_status=quality,
            provenance_id=f"PROV-{result_id}",
        )
        provenance.append(
            _make_provenance(
                result_id=result_id,
                study_id=study_id,
                file_name=file_name,
                source_url=source_url,
                sha256=sha256,
                subject_id=subject,
                timepoint=timepoint,
                analyte=analyte,
                original_value=None if raw_value is None else str(raw_value),
                original_unit=None if raw_unit is None else str(raw_unit),
                normalized_value=normalized.normalized_value,
                quality=quality,
                dataset_id=f"{study_id}-{panel_type}",
                assay_method=panel_type,
            )
        )
        results.append(result)
    return results, provenance


def extract_wide_alamar(
    *,
    study_id: str,
    file_name: str,
    panel_type: str,
    sample_type: str,
    assay_method: str,
) -> tuple[list[LaboratoryResult], list[ProvenanceRecord]]:
    """Извлечь широкую таблицу AlamarPanel (концентрации NPQ и проценты)."""
    path = RAW_DIR / study_id / file_name
    if not path.exists():
        return [], []
    manifest = _manifest_index().get((study_id, file_name), {})
    source_url = str(manifest.get("source_url") or "")
    sha256 = str(manifest.get("sha256") or sha256_file(path))
    rows = _read_csv(path)
    if not rows:
        return [], []
    fields = list(rows[0].keys())
    sample_column = fields[0]
    value_fields = [
        field
        for field in fields[1:]
        if field and (field.endswith("_concentration_npq") or field.endswith("_percent_normalized_value"))
    ]
    results: list[LaboratoryResult] = []
    provenance: list[ProvenanceRecord] = []
    index = 0
    for row in rows:
        sample = str(row.get(sample_column) or "").strip()
        if not sample:
            continue
        match = re.match(r"^(C\d+)_", sample)
        subject = match.group(1) if match else None
        timepoint_match = re.search(r"_(L-\d+|R\+\d+|FD\d+)(?:_|$)", sample)
        timepoint = timepoint_match.group(1) if timepoint_match else None
        for field in value_fields:
            index += 1
            raw_value = row.get(field)
            is_percent = field.endswith("_percent_normalized_value")
            analyte = field.replace("_concentration_npq", "").replace("_percent_normalized_value", "")
            unit = "%" if is_percent else "NPQ"
            normalized = normalize_measurement(analyte, raw_value, unit)
            result_id = f"{study_id}-{panel_type}-{index:06d}"
            quality = normalized.quality_status
            result = LaboratoryResult(
                result_id=result_id,
                test_name=analyte if not is_percent else f"{analyte} percent normalized",
                value=normalized.normalized_value,
                original_value=None if raw_value is None else str(raw_value),
                unit=unit,
                normalized_unit=normalized.normalized_unit,
                sample_type=sample_type,
                collection_timepoint=timepoint,
                subject_id=subject,
                source_study_id=study_id,
                source_file=file_name,
                assay_method=assay_method,
                quality_status=quality,
                provenance_id=f"PROV-{result_id}",
            )
            provenance.append(
                _make_provenance(
                    result_id=result_id,
                    study_id=study_id,
                    file_name=file_name,
                    source_url=source_url,
                    sha256=sha256,
                    subject_id=subject,
                    timepoint=timepoint,
                    analyte=result.test_name,
                    original_value=None if raw_value is None else str(raw_value),
                    original_unit=unit,
                    normalized_value=normalized.normalized_value,
                    quality=quality,
                    dataset_id=f"{study_id}-{panel_type}",
                    assay_method=panel_type,
                )
            )
            results.append(result)
    return results, provenance


def extract_all_labs() -> tuple[list[LaboratoryResult], list[ProvenanceRecord]]:
    """Извлечь все поддерживаемые реальные лабораторные файлы."""
    results: list[LaboratoryResult] = []
    provenance: list[ProvenanceRecord] = []
    specs = [
        {
            "study_id": "OSD-569",
            "file_name": "LSDS-7_Complete_Blood_Count_CBC.upload_SUBMITTED.csv",
            "panel_type": "CBC",
            "sample_type": "whole blood",
            "assay_method": "CBC",
            "analyte_column": "ANALYTE",
            "value_column": "VALUE",
            "unit_column": "UNITS",
            "timepoint_column": "TEST_DATE",
            "subject_column": "SUBJECT_ID",
            "low_column": "RANGE_MIN",
            "high_column": "RANGE_MAX",
        },
        {
            "study_id": "OSD-575",
            "file_name": "LSDS-8_Comprehensive_Metabolic_Panel_CMP.upload_SUBMITTED.csv",
            "panel_type": "CMP",
            "sample_type": "serum",
            "assay_method": "CMP",
            "analyte_column": "ANALYTE",
            "value_column": "VALUE",
            "unit_column": "UNITS",
            "timepoint_column": "timepoint",
            "subject_column": "SUBJECT_ID",
            "low_column": "RANGE_MIN",
            "high_column": "RANGE_MAX",
        },
        {
            "study_id": "OSD-575",
            "file_name": "LSDS-8_Multiplex_serum.immune.EvePanel_SUBMITTED.csv",
            "panel_type": "CYTOKINES_IMMUNE",
            "sample_type": "serum",
            "assay_method": "EvePanel multiplex",
            "analyte_column": "Analyte",
            "value_column": "Concentration",
            "unit_column": "Unit",
            "timepoint_column": "Timepoint",
            "subject_column": "ID",
        },
        {
            "study_id": "OSD-575",
            "file_name": "LSDS-8_Multiplex_serum.cardiovascular.EvePanel_SUBMITTED.csv",
            "panel_type": "CYTOKINES_CARDIOVASCULAR",
            "sample_type": "serum",
            "assay_method": "EvePanel multiplex",
            "analyte_column": "Analyte",
            "value_column": "Concentration",
            "unit_column": "Unit",
            "timepoint_column": "Timepoint",
            "subject_column": "ID",
        },
    ]
    for spec in specs:
        part_results, part_provenance = extract_long_lab(**spec)  # type: ignore[arg-type]
        results.extend(part_results)
        provenance.extend(part_provenance)
    for spec in [
        {
            "study_id": "OSD-575",
            "file_name": "LSDS-8_Multiplex_serum.immune.AlamarPanel_TRANSFORMED.csv",
            "panel_type": "CYTOKINES_IMMUNE_ALAMAR",
            "sample_type": "serum",
            "assay_method": "AlamarPanel",
        },
        {
            "study_id": "OSD-656",
            "file_name": "LSDS-64_Multiplex_urine.immune.AlamarPanel_TRANSFORMED.csv",
            "panel_type": "URINE_INFLAMMATION_ALAMAR",
            "sample_type": "urine",
            "assay_method": "AlamarPanel",
        },
    ]:
        part_results, part_provenance = extract_wide_alamar(**spec)  # type: ignore[arg-type]
        results.extend(part_results)
        provenance.extend(part_provenance)
    return results, provenance


def summarize_labs(results: list[LaboratoryResult]) -> list[dict[str, object]]:
    """Свести реальные измерения по study/panel/analyte/timepoint без импутации."""
    from data_pipeline.common import compute_statistics

    grouped: dict[tuple[str, str, str, str, str], list[float]] = {}
    for result in results:
        key = (
            result.source_study_id or "",
            result.assay_method or result.test_name,
            result.test_name,
            result.collection_timepoint or "UNKNOWN",
            result.unit or "UNKNOWN",
        )
        grouped.setdefault(key, []).append(result.value)  # type: ignore[arg-type]
    rows: list[dict[str, object]] = []
    for (study_id, panel, analyte, timepoint, unit), values in sorted(grouped.items()):
        stats = compute_statistics(values)
        rows.append(
            {
                "study_id": study_id,
                "panel": panel,
                "analyte": analyte,
                "collection_timepoint": timepoint,
                "unit": unit,
                "n": stats["n"],
                "mean": stats["mean"],
                "sd": stats["sd"],
                "median": stats["median"],
                "min": stats["min"],
                "max": stats["max"],
                "source_type": SourceType.NASA_REAL.value,
                "notes": "Descriptive statistics only; reference intervals are not inferred.",
            }
        )
    return rows


def group_real_lab_panels(results: list[LaboratoryResult]) -> list[dict[str, object]]:
    """Сгруппировать реальные результаты в панели по study/subject/timepoint/panel.

    Абсолютное время измерения в OSDR отсутствует; мы сохраняем исходную
    относительную метку и не создаём фейковый ISO-таймстемп.
    """
    grouped: dict[tuple[str, str, str, str, str], list[LaboratoryResult]] = {}
    for result in results:
        key = (
            result.source_study_id or "",
            result.subject_id or "UNKNOWN",
            result.collection_timepoint or "UNKNOWN",
            result.assay_method or result.test_name,
            result.sample_type or "UNKNOWN",
        )
        grouped.setdefault(key, []).append(result)
    panels: list[dict[str, object]] = []
    for index, ((study_id, subject_id, timepoint, panel_type, sample_type), items) in enumerate(
        sorted(grouped.items()), start=1
    ):
        source_files = sorted({item.source_file for item in items if item.source_file})
        panels.append(
            {
                "panel_id": f"REAL-{study_id}-{panel_type}-{subject_id}-{timepoint}".replace(" ", "_"),
                "study_id": study_id,
                "subject_id": subject_id,
                "collection_timepoint": timepoint,
                "panel_type": panel_type,
                "sample_type": sample_type,
                "source_type": SourceType.NASA_REAL.value,
                "absolute_collection_timestamp_utc": None,
                "source_files": source_files,
                "result_count": len(items),
                "results": [
                    {
                        "result_id": item.result_id,
                        "test_name": item.test_name,
                        "value": item.value,
                        "unit": item.unit,
                        "normalized_unit": item.normalized_unit,
                        "quality_status": item.quality_status.value,
                        "provenance_id": item.provenance_id,
                    }
                    for item in sorted(items, key=lambda item: item.result_id)
                ],
                "provenance_ids": sorted({item.provenance_id for item in items}),
                "limitations": [
                    "Absolute collection time is not published; only the source relative label is preserved.",
                    "This panel is a descriptive real-data grouping, not a synthetic clinical panel.",
                ],
            }
        )
    return panels
