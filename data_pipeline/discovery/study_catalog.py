"""Каталог кандидатных исследований OSDR и их проверка.

Метаданные семи Inspiration4-исследований проверены вручную 2026-11-14.
Остальные записи появляются через публичный поиск OSDR (`term`, `size`,
`from`). Метаданные не доказывают наличие файлов, единиц, временных точек или
непрерывной телеметрии: это проверяется отдельно по фактическим файлам.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from shared.contracts import (  # noqa: E402
    DatasetCategory,
    IngestionStatus,
    NasaStudyRecord,
    VerificationStatus,
)
from data_pipeline.common import utc_now_iso  # noqa: E402
from data_pipeline.connectors import osdr_api  # noqa: E402

VERIFICATION_STALE_AFTER_DAYS: int = 30
LAST_METADATA_VERIFICATION_UTC: str = "2026-11-14"

REQUIRED_INSPECTION_FIELDS: tuple[str, ...] = (
    "study_metadata",
    "downloadable_files",
    "measurement_types",
    "measurement_units",
    "collection_timepoints",
    "subject_identifiers",
    "redistribution_permission",
)

DISCOVERY_QUERIES: tuple[str, ...] = (
    "Inspiration4",
    "ISS human physiology",
    "astronaut cardiovascular deconditioning",
    "spaceflight associated neuro-ocular syndrome",
    "orthostatic intolerance spaceflight",
    "circadian sleep astronaut",
    "immune function spaceflight",
    "bone muscle loss spaceflight",
    "bed rest",
    "head-down tilt",
    "dry immersion",
    "isolation confinement",
    "cabin carbon dioxide",
    "space radiation",
    "galactic cosmic radiation",
    "solar particle event",
    "microbiome astronaut",
)


@dataclass(frozen=True)
class StudyCandidate:
    """Проверенная только по метаданным запись исследования OSDR."""

    study_id: str
    title: str | None
    mission: str | None
    metadata_summary: str | None
    continuous_telemetry_available: bool | None
    verification_status: VerificationStatus
    last_verified_utc: str | None


# Все семь ссылок подтверждены как существующие исследования Inspiration4.
STUDY_CANDIDATES: tuple[StudyCandidate, ...] = (
    StudyCandidate(
        study_id="OSD-569",
        title="Whole Blood Measurements from the SpaceX Inspiration4 Mission (RNA-seq, epitranscriptome, WGS, clonal hematopoiesis, CBC)",
        mission="SpaceX Inspiration4",
        metadata_summary="Whole blood omics and CBC from pre-flight and post-flight timepoints.",
        continuous_telemetry_available=None,
        verification_status=VerificationStatus.VERIFIED_METADATA,
        last_verified_utc=LAST_METADATA_VERIFICATION_UTC,
    ),
    StudyCandidate(
        study_id="OSD-570",
        title="SpaceX Inspiration4 PBMC Profiling: snRNA-seq, snATAC-seq, and T-cell and B-cell repertoire profiling",
        mission="SpaceX Inspiration4",
        metadata_summary="PBMC single-nucleus omics and immune repertoire profiling.",
        continuous_telemetry_available=None,
        verification_status=VerificationStatus.VERIFIED_METADATA,
        last_verified_utc=LAST_METADATA_VERIFICATION_UTC,
    ),
    StudyCandidate(
        study_id="OSD-571",
        title="SpaceX Inspiration4 Plasma Profiling: Proteomics, EVPs, Metabolomics, cfDNA Sequencing and cfRNA Sequencing",
        mission="SpaceX Inspiration4",
        metadata_summary="Plasma proteomics, metabolomics, EVP and cell-free nucleic acid assays.",
        continuous_telemetry_available=None,
        verification_status=VerificationStatus.VERIFIED_METADATA,
        last_verified_utc=LAST_METADATA_VERIFICATION_UTC,
    ),
    StudyCandidate(
        study_id="OSD-572",
        title="SpaceX Inspiration4 Oral, Nasal, and Skin Metagenomic and Metatranscriptomic Microbial Swabs",
        mission="SpaceX Inspiration4",
        metadata_summary="Crew oral, nasal and skin microbiome swabs collected around flight.",
        continuous_telemetry_available=None,
        verification_status=VerificationStatus.VERIFIED_METADATA,
        last_verified_utc=LAST_METADATA_VERIFICATION_UTC,
    ),
    StudyCandidate(
        study_id="OSD-573",
        title="SpaceX Inspiration4 Dragon Capsule Metagenomic and Metatranscriptomic Microbial Swabs",
        mission="SpaceX Inspiration4",
        metadata_summary="Environmental microbial swabs from nine Dragon capsule surfaces.",
        continuous_telemetry_available=None,
        verification_status=VerificationStatus.VERIFIED_METADATA,
        last_verified_utc=LAST_METADATA_VERIFICATION_UTC,
    ),
    StudyCandidate(
        study_id="OSD-575",
        title="SpaceX Inspiration4 Blood Serum Metabolic Panel and Immune/Cardiac Cytokine Arrays (Comprehensive Metabolic Panel and Multiplex)",
        mission="SpaceX Inspiration4",
        metadata_summary="Serum metabolic panel and immune/cardiac cytokine multiplex assays.",
        continuous_telemetry_available=None,
        verification_status=VerificationStatus.VERIFIED_METADATA,
        last_verified_utc=LAST_METADATA_VERIFICATION_UTC,
    ),
    StudyCandidate(
        study_id="OSD-656",
        title="SpaceX Inspiration4 Urine Inflammation Panel (Multiplex, NULISAseq)",
        mission="SpaceX Inspiration4",
        metadata_summary="Urine inflammatory, cytokine and chemokine protein panel.",
        continuous_telemetry_available=None,
        verification_status=VerificationStatus.VERIFIED_METADATA,
        last_verified_utc=LAST_METADATA_VERIFICATION_UTC,
    ),
)

CANDIDATE_STUDY_IDS: tuple[str, ...] = tuple(s.study_id for s in STUDY_CANDIDATES)


def list_candidate_studies() -> list[StudyCandidate]:
    """Вернуть кандидатов без права считать их данные валидными."""
    return list(STUDY_CANDIDATES)


def _compact(value: Any) -> str | None:
    """Сериализовать поле метаданных в строку без выдумывания содержимого."""
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if isinstance(value, dict):
        for key in ("name", "Name", "title", "value"):
            if key in value:
                return _compact(value[key])
        return None
    if isinstance(value, list):
        parts = [_compact(item) for item in value]
        return "; ".join(part for part in parts if part) or None
    return str(value)


def metadata_study_payload(payload: dict[str, object], study_id: str) -> dict[str, Any]:
    """Достать объект исследования из ISA-JSON ответа OSDR."""
    study_root = payload.get("study")
    if isinstance(study_root, dict):
        entry = study_root.get(study_id)
        if isinstance(entry, dict):
            studies = entry.get("studies")
            if isinstance(studies, list) and studies and isinstance(studies[0], dict):
                return studies[0]
            return entry
    return {}


def extract_metadata_fields(payload: dict[str, object], study_id: str) -> dict[str, object]:
    """Извлечь title/description/assay types из проверенного metadata JSON."""
    study = metadata_study_payload(payload, study_id)
    assays = study.get("assays") if isinstance(study.get("assays"), list) else []
    assay_types: list[str] = []
    for assay in assays:
        if not isinstance(assay, dict):
            continue
        for key in ("measurementType", "technologyType", "technologyPlatform"):
            value = _compact(assay.get(key))
            if value and value not in assay_types:
                assay_types.append(value)
    publications = study.get("publications") if isinstance(study.get("publications"), list) else []
    pub_refs: list[str] = []
    for publication in publications:
        if not isinstance(publication, dict):
            continue
        title = _compact(publication.get("title"))
        doi = _compact(publication.get("doi"))
        if title:
            pub_refs.append(f"{title} (DOI: {doi})" if doi else title)
    return {
        "title": _compact(study.get("title")),
        "description": _compact(study.get("description")),
        "assay_types": assay_types,
        "publication_references": pub_refs,
        "submission_date": _compact(study.get("submissionDate")),
        "public_release_date": _compact(study.get("publicReleaseDate")),
    }


def verify_study_metadata(study_id: str, *, refresh: bool = False) -> StudyCandidate:
    """Перепроверить метаданные через OSDR API и обновить статус."""
    payload = osdr_api.fetch_study_metadata(study_id, force_refresh=refresh)
    key = f"OSD-{osdr_api.normalize_study_identifier(study_id)}"
    fields = extract_metadata_fields(payload, key)
    existing = next((item for item in STUDY_CANDIDATES if item.study_id == key), None)
    fetch = payload.get("_astralis_fetch") if isinstance(payload.get("_astralis_fetch"), dict) else {}
    verification = (
        VerificationStatus.CACHE_FALLBACK
        if fetch.get("status") == "CACHE_FALLBACK"
        else VerificationStatus.VERIFIED_METADATA
    )
    return StudyCandidate(
        study_id=key,
        title=str(fields["title"]) if fields["title"] else (existing.title if existing else None),
        mission=existing.mission if existing else None,
        metadata_summary=str(fields["description"])[:1200] if fields["description"] else (existing.metadata_summary if existing else None),
        continuous_telemetry_available=None,
        verification_status=verification,
        last_verified_utc=str(fetch.get("fetched_at_utc") or LAST_METADATA_VERIFICATION_UTC),
    )


def refresh_study_catalog() -> list[StudyCandidate]:
    """Обновить каталог всех кандидатов и пометить устаревшие записи."""
    refreshed: list[StudyCandidate] = []
    for candidate in STUDY_CANDIDATES:
        try:
            refreshed.append(verify_study_metadata(candidate.study_id))
        except Exception:
            refreshed.append(
                replace(
                    candidate,
                    verification_status=VerificationStatus.UNAVAILABLE,
                    continuous_telemetry_available=None,
                )
            )
    return refreshed


def require_file_level_verification(study_id: str) -> bool:
    """Вернуть True, пока файлы, единицы и timepoints не инспектированы."""
    candidate = next((item for item in STUDY_CANDIDATES if item.study_id == study_id), None)
    return candidate is None or candidate.verification_status != VerificationStatus.VERIFIED_FILES


def _classify(title: str, organism: str, mission: str, assay_types: list[str]) -> DatasetCategory:
    """Классифицировать исследование по явным признакам, без клинических выводов."""
    text = f"{title} {organism} {mission}".lower()
    if any(token in text for token in ("radiation", "cosmic ray", "solar particle", "dosimetry")):
        return DatasetCategory.RADIATION_EVIDENCE
    if any(token in text for token in ("cabin", "environmental", "carbon dioxide", "co2 monitor", "air quality")):
        return DatasetCategory.ENVIRONMENTAL_TELEMETRY
    if any(token in text for token in ("bed rest", "head-down tilt", "dry immersion", "isolation", "confinement", "confined environment")):
        return DatasetCategory.HUMAN_SPACEFLIGHT_ANALOG
    if "homo sapiens" in text and any(
        token in text for token in ("iss", "international space station", "inspiration4", "spacex", "spaceflight", "astronaut")
    ):
        return DatasetCategory.DIRECT_HUMAN_SPACEFLIGHT
    if any(token in text for token in ("spaceflight", "iss", "microgravity")) or assay_types:
        return DatasetCategory.SUPPORTING_BIOLOGICAL_EVIDENCE
    return DatasetCategory.OTHER_RELEVANT_RESEARCH


def _relevance_score(
    *,
    category: DatasetCategory,
    title: str,
    organism: str,
    assay_types: list[str],
    has_human: bool,
) -> float:
    """Рассчитать прозрачный 100-балльный рейтинг релевантности."""
    text = f"{title} {organism}".lower()
    score = 0.0
    score += {
        DatasetCategory.DIRECT_HUMAN_SPACEFLIGHT: 40.0,
        DatasetCategory.HUMAN_SPACEFLIGHT_ANALOG: 32.0,
        DatasetCategory.RADIATION_EVIDENCE: 28.0,
        DatasetCategory.ENVIRONMENTAL_TELEMETRY: 26.0,
        DatasetCategory.SUPPORTING_BIOLOGICAL_EVIDENCE: 18.0,
        DatasetCategory.OTHER_RELEVANT_RESEARCH: 6.0,
    }[category]
    score += 12.0 if has_human else 0.0
    if "inspiration4" in text:
        score += 10.0
    if any(token in text for token in ("astronaut", "crew", "spaceflight", "iss")):
        score += 8.0
    if any(token in text for token in ("cardiovascular", "neuro-ocular", "sans", "immune", "bone", "muscle", "metabolic")):
        score += 6.0
    if any(token in text for token in ("bed rest", "head-down tilt", "dry immersion", "isolation", "confinement", "confined environment")):
        score += 6.0
    if any(token in text for token in ("radiation", "cosmic", "solar particle")):
        score += 6.0
    if any(token in text for token in ("carbon dioxide", "cabin", "environmental")):
        score += 5.0
    score += min(6.0, 2.0 * len(set(assay_types)))
    score += 4.0 if has_human else 0.0
    score += 3.0 if "homo sapiens" in text else 0.0
    return round(min(100.0, score), 3)


def _search_records() -> dict[str, dict[str, Any]]:
    """Собрать уникальные OSD-записи из тематических запросов OSDR."""
    found: dict[str, dict[str, Any]] = {}
    for query in DISCOVERY_QUERIES:
        try:
            payload = osdr_api.search_osdr(query, page_size=8, page_number=1)
        except Exception:
            continue
        hits = payload.get("hits") if isinstance(payload.get("hits"), dict) else {}
        for hit in hits.get("hits", []) if isinstance(hits.get("hits"), list) else []:
            source = hit.get("_source") if isinstance(hit, dict) else None
            if not isinstance(source, dict):
                continue
            accession = str(source.get("Accession") or "").strip().upper()
            if not accession.startswith("OSD-"):
                continue
            found[accession] = source
    return found


def discover_studies() -> list[NasaStudyRecord]:
    """Обнаружить исследования и записать accepted/rejected с причинами.

    Поиск ограничен публичным индексом OSDR. Не-OSD accession (например,
    GEO GSE) не включаются в каталог OSDR и явно перечисляются в limitations.
    """
    records: dict[str, NasaStudyRecord] = {}
    for candidate in STUDY_CANDIDATES:
        records[candidate.study_id] = NasaStudyRecord(
            study_id=candidate.study_id,
            title=candidate.title,
            description=candidate.metadata_summary,
            mission=candidate.mission,
            verification_status=candidate.verification_status,
            metadata_url=f"{osdr_api.OSDR_BASE_URL}{osdr_api.STUDY_META_PATH.format(study_number=osdr_api.normalize_study_identifier(candidate.study_id))}",
            file_index_url=f"{osdr_api.OSDR_BASE_URL}{osdr_api.STUDY_FILES_PATH.format(study_number=osdr_api.normalize_study_identifier(candidate.study_id))}",
            s3_prefix=None,
            dataset_ids=[],
            continuous_telemetry_available=None,
            last_verified_utc=candidate.last_verified_utc,
            notes="Verified metadata; file-level inspection is recorded separately in the dataset registry.",
            study_category=DatasetCategory.DIRECT_HUMAN_SPACEFLIGHT,
            organism="Homo sapiens",
            public_access_status="PUBLIC_METADATA; file-level redistribution checked separately",
            relevance_score=98.0,
            scientific_relevance="Inspiration4 human spaceflight biospecimen and laboratory study.",
            limitations=["Not continuous mission telemetry.", "Short-duration mission biospecimens; no 180-day physiology."],
            source_url=f"https://osdr.nasa.gov/bio/repo/data/studies/{candidate.study_id}",
            ingestion_status=IngestionStatus.CATALOGUED,
        )
    for study_id, source in sorted(_search_records().items()):
        if study_id in records:
            continue
        title = _compact(source.get("Study Title")) or ""
        description = _compact(source.get("Study Description")) or ""
        organism_value = source.get("organism")
        organism = _compact(organism_value) or ""
        mission_value = source.get("Mission")
        mission = _compact(mission_value) or _compact(source.get("Flight Program")) or ""
        assay_types = [_compact(source.get("Study Assay Technology Type")) or ""]
        assay_types = [item for item in assay_types if item]
        category = _classify(title, organism, mission, assay_types)
        has_human = "homo sapiens" in organism.lower() or "human" in title.lower()
        score = _relevance_score(
            category=category,
            title=title,
            organism=organism,
            assay_types=assay_types,
            has_human=has_human,
        )
        rejected = score < 24.0 or (not has_human and category in {DatasetCategory.OTHER_RELEVANT_RESEARCH})
        reason = None
        if rejected:
            reason = (
                "Rejected: low human-relevance score or non-human study without a radiation/environmental role."
                if score < 24.0
                else "Rejected: non-human study without a direct human spaceflight, analog, radiation, or environmental role."
            )
        records[study_id] = NasaStudyRecord(
            study_id=study_id,
            title=title or None,
            description=description[:1600] or None,
            mission=mission or None,
            verification_status=VerificationStatus.VERIFIED_METADATA,
            metadata_url=f"{osdr_api.OSDR_BASE_URL}{osdr_api.STUDY_META_PATH.format(study_number=osdr_api.normalize_study_identifier(study_id))}",
            file_index_url=f"{osdr_api.OSDR_BASE_URL}{osdr_api.STUDY_FILES_PATH.format(study_number=osdr_api.normalize_study_identifier(study_id))}",
            s3_prefix=None,
            dataset_ids=[],
            continuous_telemetry_available=None,
            last_verified_utc=utc_now_iso(),
            notes="Discovered through the public OSDR search endpoint; files were not downloaded for this record.",
            study_category=category,
            organism=organism or None,
            assay_types=assay_types,
            relevance_score=score,
            scientific_relevance=f"Automated discovery classification: {category.value}.",
            limitations=["Metadata-only discovery; file-level content and units are not verified."],
            source_url=f"https://osdr.nasa.gov/bio/repo/data/studies/{study_id}",
            publication_references=[],
            ingestion_status=IngestionStatus.REJECTED if rejected else IngestionStatus.CATALOGUED,
            rejection_reason=reason,
        )
    return sorted(records.values(), key=lambda record: (record.rejection_reason is not None, -(record.relevance_score or 0.0), record.study_id))
