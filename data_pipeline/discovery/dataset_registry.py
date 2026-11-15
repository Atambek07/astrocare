"""Реестр наборов данных OSDR и их модальностей.

Не каждый набор является непрерывной телеметрией: омиксные, лабораторные,
микробиомные и environmental datasets получают отдельную модальность.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from shared.contracts import (  # noqa: E402
    DataModality,
    DatasetCategory,
    IngestionStatus,
    NasaDatasetRecord,
    VerificationStatus,
)
from data_pipeline.common import read_json, write_json  # noqa: E402
from data_pipeline.connectors.osdr_files import list_public_files  # noqa: E402
from data_pipeline.ingestion.format_detector import detect_modality  # noqa: E402
from data_pipeline.discovery.study_catalog import CANDIDATE_STUDY_IDS, DISCOVERY_QUERIES  # noqa: E402

REGISTRY_PATH: Path = Path(__file__).resolve().parents[2] / "data_bundle" / "provenance" / "dataset_registry.json"
MANIFEST_PATH: Path = Path(__file__).resolve().parents[2] / "data_bundle" / "manifests" / "download_manifest.json"
MIN_SUBJECTS_FOR_BASELINE: int = 3
MIN_TIMEPOINTS_FOR_TREND: int = 3


def _load_downloads() -> dict[str, list[dict[str, object]]]:
    """Сгруппировать уже скачанные файлы по study_id."""
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    if not MANIFEST_PATH.exists():
        return grouped
    rows = read_json(MANIFEST_PATH)
    for row in rows if isinstance(rows, list) else []:
        if isinstance(row, dict):
            grouped[str(row.get("study_id"))].append(row)
    return grouped


def build_registry(study_ids: list[str]) -> list[NasaDatasetRecord]:
    """Построить реестр датасетов из фактических индексов файлов OSDR."""
    downloaded = _load_downloads()
    records: list[NasaDatasetRecord] = []
    for study_id in study_ids:
        try:
            files = list_public_files(study_id)
        except Exception:
            records.append(
                NasaDatasetRecord(
                    dataset_id=f"{study_id}-FILE-INDEX-UNAVAILABLE",
                    study_id=study_id,
                    title="OSDR file index unavailable",
                    modality=DataModality.OTHER,
                    measurement_types=[],
                    measurement_units=[],
                    subject_count=None,
                    timepoint_count=None,
                    file_count=None,
                    access_level="UNKNOWN",
                    verification_status=VerificationStatus.UNAVAILABLE,
                    source_url=None,
                    last_verified_utc=None,
                    continuous_telemetry=None,
                    notes="The public file index could not be retrieved.",
                    ingestion_status=IngestionStatus.UNAVAILABLE,
                    limitations=["No file-level evidence available."],
                )
            )
            continue
        grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
        for file in files:
            grouped[(str(file.get("category") or "Uncategorized"), str(file.get("subcategory") or ""))].append(file)
        for (category, subcategory), group in sorted(grouped.items()):
            file_names = [str(item.get("file_name")) for item in group]
            modalities = {detect_modality(name, item).value for name, item in zip(file_names, group)}
            modality = DataModality.OMICS if "OMICS" in modalities else DataModality(detect_modality(file_names[0], group[0]))
            downloaded_names = {
                str(row.get("file_name"))
                for row in downloaded.get(study_id, [])
                if row.get("actual_size") == row.get("expected_size")
            }
            downloaded_count = len([name for name in file_names if name in downloaded_names])
            records.append(
                NasaDatasetRecord(
                    dataset_id=f"{study_id}-{category.replace(' ', '_')}-{subcategory.replace(' ', '_')}".strip("-_"),
                    study_id=study_id,
                    title=f"{category} / {subcategory or 'files'}",
                    modality=modality,
                    measurement_types=[category],
                    measurement_units=[],
                    subject_count=None,
                    timepoint_count=None,
                    file_count=len(group),
                    access_level="PUBLIC",
                    verification_status=VerificationStatus.VERIFIED_FILES,
                    source_url=str(group[0].get("source_url") or ""),
                    last_verified_utc=str(group[0].get("verified_at_utc") or ""),
                    continuous_telemetry=False,
                    notes="Public file index inspected; table content is parsed separately.",
                    category=DatasetCategory.DIRECT_HUMAN_SPACEFLIGHT if study_id in CANDIDATE_STUDY_IDS else DatasetCategory.OTHER_RELEVANT_RESEARCH,
                    assay_types=[category],
                    public_files=len(group),
                    restricted_files=0,
                    downloaded_files=downloaded_count,
                    relevance_score=90.0 if downloaded_count else 55.0,
                    scientific_relevance="OSDR public dataset grouped by category and subcategory.",
                    limitations=["File-level measurement counts and units are recorded only for parsed files."],
                    ingestion_status=IngestionStatus.DOWNLOADED if downloaded_count else IngestionStatus.CATALOGUED,
                    source_file_names=file_names[:50],
                )
            )
    return records


def register_dataset(record: NasaDatasetRecord) -> None:
    """Добавить или обновить запись датасета с сохранением provenance."""
    current: list[dict[str, object]] = []
    if REGISTRY_PATH.exists():
        loaded = read_json(REGISTRY_PATH)
        current = loaded if isinstance(loaded, list) else []
    current = [row for row in current if row.get("dataset_id") != record.dataset_id]
    current.append(record.model_dump(mode="json"))
    write_json(REGISTRY_PATH, current)


def find_datasets_by_modality(modality: DataModality) -> list[NasaDatasetRecord]:
    """Найти датасеты конкретной модальности."""
    if not REGISTRY_PATH.exists():
        return []
    loaded = read_json(REGISTRY_PATH)
    return [
        NasaDatasetRecord.model_validate(row)
        for row in loaded
        if isinstance(row, dict) and row.get("modality") == modality.value
    ]


def mark_verified(dataset_id: str, *, status: VerificationStatus) -> None:
    """Обновить VerificationStatus после инспекции файлов."""
    if not REGISTRY_PATH.exists():
        return
    loaded = read_json(REGISTRY_PATH)
    rows = loaded if isinstance(loaded, list) else []
    for row in rows:
        if isinstance(row, dict) and row.get("dataset_id") == dataset_id:
            row["verification_status"] = status.value
    write_json(REGISTRY_PATH, rows)


def export_registry(destination: Path = REGISTRY_PATH) -> Path:
    """Экспортировать реестр в JSON рядом с provenance-манифестом."""
    if destination.exists():
        return destination
    write_json(destination, [])
    return destination


def discovery_query_manifest() -> list[dict[str, object]]:
    """Вернуть перечень реализованных поисковых запросов для аудита."""
    return [{"query": query, "endpoint": "https://osdr.nasa.gov/osdr/data/search", "parameter": "term"} for query in DISCOVERY_QUERIES]
