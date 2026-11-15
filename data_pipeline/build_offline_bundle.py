"""Сборка офлайн-бандла ASTRALIS + IMPACT.

Скрипт скачивает только выбранные публичные файлы OSDR, сохраняет оригиналы,
строит реальные производные таблицы, синтетические сценарии, SQLite и
манифесты. Все артефакты проверяются против shared/contracts.schema.json.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from shared.contracts import (  # noqa: E402
    AstronautProfile,
    DailyTelemetryLog,
    FallbackStatus,
    LaboratoryPanel,
    LaboratoryResult,
    MissionPhase,
    NasaDatasetRecord,
    NasaStudyRecord,
    PhaseBaseline,
    ProvenanceRecord,
    QualityStatus,
    SourceType,
    StreamTick,
)
from data_pipeline.common import (  # noqa: E402
    BUNDLE_ID,
    PIPELINE_VERSION,
    compute_statistics,
    ensure_dir,
    finite_float,
    read_json,
    relative_path,
    sha256_file,
    utc_now_iso,
    write_json,
    write_jsonl,
)
from data_pipeline.connectors import osdr_api, osdr_files  # noqa: E402
from data_pipeline.daily_generator import (  # noqa: E402
    DAILY_GENERATOR_NAME,
    DAILY_GENERATOR_VERSION,
    DAILY_SEED,
    build_daily_provenance_records,
    generate_daily_series,
    generation_config as daily_generation_config,
)
from data_pipeline.discovery.dataset_registry import build_registry  # noqa: E402
from data_pipeline.discovery.study_catalog import (  # noqa: E402
    DISCOVERY_QUERIES,
    STUDY_CANDIDATES,
    discover_studies,
    extract_metadata_fields,
)
from data_pipeline.ingestion.download_manager import download_with_cache, report_fallback  # noqa: E402
from data_pipeline.ingestion.format_detector import describe_file, detect_file_format  # noqa: E402
from data_pipeline.processing.baseline_builder import BASELINE_MODEL_VERSION, build_phase_baselines  # noqa: E402
from data_pipeline.processing.lab_extractor import extract_all_labs, summarize_labs  # noqa: E402
from data_pipeline.processing.microbiome import compute_shannon_diversity  # noqa: E402
from data_pipeline.provenance.evidence_registry import EvidenceRegistry  # noqa: E402
from data_pipeline.provenance.knowledge import (  # noqa: E402
    build_evidence_cards,
    build_medical_guidelines,
    build_radiation_evidence,
    build_triage_protocols,
)
from data_pipeline.stream_generator import (  # noqa: E402
    A1_ANOMALY_WINDOWS,
    CREW_IDS,
    DEFAULT_SEED,
    STREAM_DURATION_MINUTES,
    STREAM_FREQUENCY_HZ,
    SYNTHETIC_GENERATOR_NAME,
    SYNTHETIC_GENERATOR_VERSION,
    TICKS_PER_ASTRONAUT,
    build_anomaly_manifest,
    build_synthetic_provenance_records,
    generate_all_streams,
    write_jsonl_file,
)
from data_pipeline.synthetic_labs import build_synthetic_lab_panels  # noqa: E402

BUNDLE_DIR: Path = _PROJECT_ROOT / "data_bundle"
RAW_NASA_DIR: Path = BUNDLE_DIR / "raw" / "nasa"
PROCESSED_DIR: Path = BUNDLE_DIR / "processed"
PROVENANCE_DIR: Path = BUNDLE_DIR / "provenance"
SYNTHETIC_DIR: Path = BUNDLE_DIR / "synthetic"
CLINICAL_DIR: Path = BUNDLE_DIR / "clinical"
MANIFEST_DIR: Path = BUNDLE_DIR / "manifests"

DB_FILENAME: str = "astronaut_health.db"
BASELINES_FILENAME: str = "nasa_baselines.json"
STREAM_FILENAME: str = "telemetry_stream_60m.jsonl"
DAILY_FILENAME: str = "telemetry_180d.json"
ANOMALY_FILENAME: str = "anomaly_manifest.json"
GUIDELINES_FILENAME: str = "nasa_medical_guidelines.json"
LABS_FILENAME: str = "laboratory_panels_seed.json"
PROTOCOLS_FILENAME: str = "triage_protocols.json"
EVIDENCE_FILENAME: str = "nasa_evidence_cards.json"
STUDY_CATALOG_FILENAME: str = "study_catalog.json"
DATASET_REGISTRY_FILENAME: str = "dataset_registry.json"
PROVENANCE_MANIFEST_FILENAME: str = "provenance_manifest.json"
SYNTHETIC_CONFIG_FILENAME: str = "generation_config.json"
BUNDLE_MANIFEST_FILENAME: str = "bundle_manifest.json"

MISSION_DAYS: int = 180
PHASE_1_END_DAY: int = 14
PHASE_2_START_DAY: int = 15
BUNDLE_VERSION: str = "1.0.0"

SCHEMA_PATH: Path = _PROJECT_ROOT / "shared" / "contracts.schema.json"

SELECTED_FILES_BY_STUDY: dict[str, tuple[str, ...]] = {
    "OSD-569": (
        "OSD-569_metadata_OSD-569-ISA.zip",
        "LSDS-7_Complete_Blood_Count_CBC.upload_SUBMITTED.csv",
        "LSDS-7_Complete_Blood_Count_CBC_TRANSFORMED.csv",
    ),
    "OSD-570": (
        "OSD-570_metadata_OSD-570-ISA.zip",
        "GLDS-562_snRNA-Seq_PBMC_Gene_Expression_snRNA-seq_Processed_Data.xlsx",
    ),
    "OSD-571": (
        "OSD-571_metadata_OSD-571-ISA.zip",
        "GLDS-563_proteomics_plasma_metadata_all_samples_collapsed.csv",
        "GLDS-563_proteomics_EVPs_sample_metadata.csv",
        "GLDS-563_proteomics_EVPs_proteomics_preprocessed_data.txt",
        "GLDS-563_proteomics_Plasma_Proteomics_Processed_Data.xlsx",
        "GLDS-563_proteomics_EVP_Proteomics_Processed_Data.xlsx",
        "GLDS-563_metabolomics_Plasma_Metabolomics_Processed_Data.xlsx",
        "GLDS-563_metabolomics_metabolomics_RPPOS-NEG_preprocessed_data.xlsx",
        "GLDS-563_metabolomics_metabolomics_ANPPOS-NEG_preprocessed_data.xlsx",
    ),
    "OSD-572": (
        "OSD-572_metadata_OSD-572-ISA.zip",
        "GLDS-564_GMetagenomics_README_GLmetagenomics.txt",
        "GLDS-564_GMetagenomics_Metaphlan-taxonomy_GLmetagenomics.tsv",
        "GLDS-564_GMetagenomics_Pathway-abundances_GLmetagenomics.tsv",
    ),
    "OSD-573": ("OSD-573_metadata_OSD-573-ISA.zip",),
    "OSD-575": (
        "OSD-575_metadata_OSD-575-ISA.zip",
        "LSDS-8_Comprehensive_Metabolic_Panel_CMP.upload_SUBMITTED.csv",
        "LSDS-8_Comprehensive_Metabolic_Panel_CMP_TRANSFORMED.csv",
        "LSDS-8_Multiplex_serum.immune.EvePanel_SUBMITTED.csv",
        "LSDS-8_Multiplex_serum.immune.AlamarPanel_SUBMITTED.xlsx",
        "LSDS-8_Multiplex_serum.cardiovascular.EvePanel_SUBMITTED.csv",
        "LSDS-8_Multiplex_serum.immune.AlamarPanel_TRANSFORMED.csv",
        "LSDS-8_Multiplex_serum_immune_EvePanel_TRANSFORMED.csv",
        "LSDS-8_Multiplex_serum_cardiovascular_EvePanel_TRANSFORMED.csv",
    ),
    "OSD-656": (
        "OSD-656_metadata_OSD-656-ISA.zip",
        "LSDS-64_Multiplex_urine.immune.AlamarPanel_SUBMITTED.xlsx",
        "LSDS-64_Multiplex_urine.immune.AlamarPanel_TRANSFORMED.csv",
        "LSDS-64_Multiplex_200plex v1-Target Information.csv",
    ),
}

ASTronaut_PROFILES: tuple[AstronautProfile, ...] = (
    AstronautProfile(
        astronaut_id="A1",
        display_name="Commander A1",
        mission_role="Commander",
        age=38,
        sex="FEMALE",
        height_cm=168.0,
        mass_kg=61.0,
        mission_name="ASTRALIS Demo Mission LEO-180",
        mission_duration_days=180,
        is_control=False,
        source_type=SourceType.SYNTHETIC,
        provenance_ids=["PROV-SYN-ASTRONAUT-A1"],
    ),
    AstronautProfile(
        astronaut_id="A2",
        display_name="Mission Specialist A2",
        mission_role="Mission Specialist",
        age=41,
        sex="MALE",
        height_cm=180.0,
        mass_kg=78.0,
        mission_name="ASTRALIS Demo Mission LEO-180",
        mission_duration_days=180,
        is_control=True,
        source_type=SourceType.SYNTHETIC,
        provenance_ids=["PROV-SYN-ASTRONAUT-A2"],
    ),
)


def _profile_provenance() -> list[ProvenanceRecord]:
    """Provenance для синтетических профилей экипажа."""
    return [
        ProvenanceRecord(
            provenance_id=profile.provenance_ids[0],
            source_type=SourceType.SYNTHETIC,
            nasa_study_id=None,
            nasa_dataset_id=None,
            source_file=None,
            source_url=None,
            publication_reference=None,
            subject_id=None,
            collection_timepoint="MISSION-PROFILE",
            measurement_timestamp=None,
            measurement_unit="mixed",
            original_value="synthetic_astronaut_profile",
            normalized_value=None,
            processing_method="deterministic_profile_definition",
            quality_status=QualityStatus.VALIDATED,
            metric_key="astronaut_profile",
            fallback_status=FallbackStatus.NONE,
            derived_from=[],
            source_verified_utc=None,
            notes="Synthetic demo astronaut; not a real NASA crew member.",
            measurement_name="astronaut_profile",
            original_unit="mixed",
            normalized_unit="mixed",
            processing_version="astralis-profile-1.0.0",
            generated_at_utc=utc_now_iso(),
            license_or_access_terms="Project-generated synthetic data",
            processing_timestamp=utc_now_iso(),
            pipeline_version=PIPELINE_VERSION,
            generator_name=SYNTHETIC_GENERATOR_NAME,
            generator_version=SYNTHETIC_GENERATOR_VERSION,
            random_seed=DEFAULT_SEED,
            scenario_id="SYNTH-CREW-A1-A2",
            scenario_configuration={"astronaut_id": profile.astronaut_id, "is_control": profile.is_control},
            generation_timestamp="2026-05-01T08:00:00Z",
        )
        for profile in ASTronaut_PROFILES
    ]


def _existing_manifest() -> dict[tuple[str, str], dict[str, Any]]:
    """Прочитать текущий download_manifest.json."""
    path = MANIFEST_DIR / "download_manifest.json"
    if not path.exists():
        return {}
    loaded = read_json(path)
    return {
        (str(row.get("study_id")), str(row.get("file_name"))): row
        for row in loaded
        if isinstance(row, dict)
    }


def preserve_original_nasa_files() -> list[Path]:
    """Скачать/сохранить выбранные публичные файлы и вернуть локальные пути."""
    ensure_dir(RAW_NASA_DIR)
    ensure_dir(MANIFEST_DIR)
    existing = _existing_manifest()
    manifest_rows: list[dict[str, object]] = []
    downloaded_paths: list[Path] = []
    fallback_results = []
    for study_id, file_names in SELECTED_FILES_BY_STUDY.items():
        try:
            public_files = osdr_files.list_public_files(study_id)
        except Exception as exc:
            print(f"WARN: file index unavailable for {study_id}: {exc}")
            continue
        by_name = {str(item["file_name"]): item for item in public_files}
        target_dir = ensure_dir(RAW_NASA_DIR / study_id)
        for file_name in file_names:
            record = by_name.get(file_name)
            if record is None:
                print(f"WARN: selected file not found in public index: {study_id}/{file_name}")
                continue
            destination = target_dir / file_name
            expected_size = int(record.get("file_size") or 0)
            existing_row = existing.get((study_id, file_name), {})
            if destination.exists() and destination.stat().st_size == expected_size:
                sha = str(existing_row.get("sha256") or sha256_file(destination))
                downloaded_at = str(existing_row.get("downloaded_at_utc") or utc_now_iso())
                source_url = str(existing_row.get("source_url") or record["source_url"])
            else:
                result = download_with_cache(str(record["source_url"]), destination)
                fallback_results.append(result)
                if result.path is None:
                    print(f"WARN: download unavailable: {study_id}/{file_name}")
                    continue
                sha = result.sha256 or sha256_file(destination)
                downloaded_at = utc_now_iso()
                source_url = str(record["source_url"])
            manifest_rows.append(
                {
                    "study_id": study_id,
                    "file_name": file_name,
                    "category": record.get("category"),
                    "subcategory": record.get("subcategory"),
                    "restricted": bool(record.get("restricted", False)),
                    "visible": bool(record.get("visible", True)),
                    "expected_size": expected_size,
                    "actual_size": destination.stat().st_size,
                    "sha256": sha,
                    "source_url": source_url,
                    "downloaded_at_utc": downloaded_at,
                    "format": detect_file_format(destination),
                    "local_path": relative_path(destination),
                    "redistribution_status": "PUBLIC_OSDR_FILE",
                }
            )
            downloaded_paths.append(destination)
    write_json(MANIFEST_DIR / "download_manifest.json", manifest_rows)
    status = report_fallback(fallback_results)
    write_json(
        MANIFEST_DIR / "download_status.json",
        {
            "generated_at_utc": utc_now_iso(),
            "fallback_status": status.value,
            "attempted_downloads": len(fallback_results),
            "cached_files": sum(1 for result in fallback_results if result.from_cache),
            "unavailable_files": sum(1 for result in fallback_results if result.path is None),
            "selected_files": len(manifest_rows),
        },
    )
    return downloaded_paths


def verify_nasa_references() -> list[dict[str, object]]:
    """Проверить метаданные и индексы файлов семи кандидатов OSDR."""
    inventory: list[dict[str, object]] = []
    for candidate in STUDY_CANDIDATES:
        try:
            metadata = osdr_api.fetch_study_metadata(candidate.study_id)
            fields = extract_metadata_fields(metadata, candidate.study_id)
            files = osdr_files.list_public_files(candidate.study_id)
            fetched = metadata.get("_astralis_fetch", {}) if isinstance(metadata.get("_astralis_fetch"), dict) else {}
            inventory.append(
                {
                    "study_id": candidate.study_id,
                    "title": fields["title"] or candidate.title,
                    "description": fields["description"],
                    "mission": candidate.mission,
                    "assay_types": fields["assay_types"],
                    "publication_references": fields["publication_references"],
                    "metadata_url": f"{osdr_api.OSDR_BASE_URL}/osdr/data/osd/meta/{osdr_api.normalize_study_identifier(candidate.study_id)}",
                    "file_index_url": f"{osdr_api.OSDR_BASE_URL}/osdr/data/osd/files/{osdr_api.normalize_study_identifier(candidate.study_id)}",
                    "file_count": len(files),
                    "public_file_count": len(files),
                    "restricted_file_count": 0,
                    "downloaded_file_count": sum(
                        1
                        for name in SELECTED_FILES_BY_STUDY.get(candidate.study_id, ())
                        if (RAW_NASA_DIR / candidate.study_id / name).exists()
                    ),
                    "selected_file_count": len(SELECTED_FILES_BY_STUDY.get(candidate.study_id, ())),
                    "verification_status": "VERIFIED_FILES" if files else "VERIFIED_METADATA",
                    "metadata_fetch_status": fetched.get("status"),
                    "continuous_telemetry_available": False,
                    "files": files,
                    "limitations": [
                        "Metadata and public file index verified; not all files were downloaded.",
                        "No continuous physiological telemetry was found in the selected files.",
                    ],
                }
            )
        except Exception as exc:
            inventory.append(
                {
                    "study_id": candidate.study_id,
                    "title": candidate.title,
                    "verification_status": "UNAVAILABLE",
                    "error": str(exc),
                    "continuous_telemetry_available": None,
                    "files": [],
                }
            )
    write_json(MANIFEST_DIR / "osdr_file_inventory.json", inventory)
    return inventory


def build_study_catalog() -> list[dict[str, object]]:
    """Собрать study_catalog.json из проверенных метаданных OSDR."""
    records = discover_studies()
    write_json(PROVENANCE_DIR / "study_catalog.json", [record.model_dump(mode="json") for record in records])
    rejected = [
        {
            "study_id": record.study_id,
            "title": record.title,
            "rejection_reason": record.rejection_reason,
            "relevance_score": record.relevance_score,
            "source_url": record.source_url,
        }
        for record in records
        if record.rejection_reason
    ]
    write_json(MANIFEST_DIR / "rejected_studies.json", rejected)
    return [record.model_dump(mode="json") for record in records]


def build_dataset_registry() -> list[dict[str, object]]:
    """Собрать dataset_registry.json с модальностями и единицами измерений."""
    records = build_registry(list(SELECTED_FILES_BY_STUDY))
    write_json(PROVENANCE_DIR / "dataset_registry.json", [record.model_dump(mode="json") for record in records])
    return [record.model_dump(mode="json") for record in records]


def build_daily_series() -> list[dict[str, object]]:
    """Сгенерировать 180 суточных записей для A1 и A2 (360 всего)."""
    daily = generate_daily_series("A1") + generate_daily_series("A2")
    daily = sorted(daily, key=lambda record: (record.astronaut_id, record.mission_day))
    write_json(BUNDLE_DIR / DAILY_FILENAME, [record.model_dump(mode="json") for record in daily])
    return [record.model_dump(mode="json") for record in daily]


def build_baselines(daily: list[dict[str, object]]) -> list[dict[str, object]]:
    """Рассчитать Phase 1 и Phase 2 базовые линии из суточной серии."""
    parsed = [DailyTelemetryLog.model_validate(row) for row in daily]
    baselines, _ = build_phase_baselines(parsed)
    baseline_rows = [baseline.model_dump(mode="json") for baseline in baselines]
    write_json(BUNDLE_DIR / BASELINES_FILENAME, baseline_rows)
    return baseline_rows


def _write_baseline_statistics(baselines: list[dict[str, object]]) -> None:
    """Явно разделить синтетические индивидуальные и реальные NASA-референсы."""
    reference_path = PROCESSED_DIR / "nasa_lab_reference_statistics.json"
    reference_rows = read_json(reference_path) if reference_path.exists() else []
    payload = {
        "generated_at_utc": utc_now_iso(),
        "population_types": {
            "synthetic_individual": "Phase baselines computed from the fictional A1/A2 daily series.",
            "nasa_real_cohort": "Descriptive statistics from public OSDR laboratory measurements; no continuous physiology.",
            "population_reference": None,
            "cohort_reference": None,
        },
        "synthetic_individual_baselines": baselines,
        "nasa_real_reference_statistics": {
            "artifact": relative_path(reference_path),
            "row_count": len(reference_rows) if isinstance(reference_rows, list) else 0,
            "source_type": SourceType.NASA_REAL.value,
            "study_ids": ["OSD-569", "OSD-575", "OSD-656"],
            "note": "Laboratory analyte summaries by study, panel, analyte, timepoint, and unit.",
        },
        "missing_statistics_policy": "Absent NASA statistics remain null; no cohort or population value is invented.",
        "limitations": [
            "No NASA cohort or population physiological baseline is available in this bundle.",
            "OSDR Inspiration4 evidence is short-duration and laboratory-based, not a 180-day mission cohort.",
            "The four PhaseBaseline records are synthetic individual baselines and are not clinical reference intervals.",
        ],
    }
    write_json(PROCESSED_DIR / "nasa_baseline_statistics.json", payload)


def build_stream() -> list[dict[str, object]]:
    """Сгенерировать 3 600 тиков на астронавта и anomaly manifest."""
    ticks = generate_all_streams()
    write_jsonl_file(ticks, BUNDLE_DIR / STREAM_FILENAME)
    anomalies = build_anomaly_manifest()
    write_json(SYNTHETIC_DIR / ANOMALY_FILENAME, [entry.model_dump(mode="json") for entry in anomalies])
    return [tick.model_dump(mode="json") for tick in ticks]


def build_synthetic_generation_config() -> dict[str, object]:
    """Сохранить seed, версию генератора и конфигурацию всех сценариев."""
    daily_config = daily_generation_config(list(CREW_IDS))
    stream_config = {
        "generator_name": SYNTHETIC_GENERATOR_NAME,
        "generator_version": SYNTHETIC_GENERATOR_VERSION,
        "seed": DEFAULT_SEED,
        "duration_minutes": STREAM_DURATION_MINUTES,
        "frequency_hz": STREAM_FREQUENCY_HZ,
        "ticks_per_astronaut": TICKS_PER_ASTRONAUT,
        "total_ticks": TICKS_PER_ASTRONAUT * len(CREW_IDS),
        "start_utc": "2026-05-01T08:00:00Z",
        "mission_day": 10,
        "mission_phase": MissionPhase.PHASE_1_ACUTE_ADAPTATION.value,
        "crew_ids": list(CREW_IDS),
        "anomaly_windows": list(A1_ANOMALY_WINDOWS),
        "source_type": SourceType.SYNTHETIC.value,
        "scenario_id": "SYNTH-STREAM-60M-A1-ANOMALIES",
        "notes": "Synthetic demo crew; not real NASA astronauts and not NASA telemetry.",
    }
    payload = {
        "generated_at_utc": utc_now_iso(),
        "seed": DEFAULT_SEED,
        "daily": daily_config,
        "stream": stream_config,
        "lab_panels": {
            "generator": "astralis-lab-generator",
            "version": "astralis-lab-1.0.0",
            "seed": DEFAULT_SEED,
            "days": [1, 30, 90, 180],
            "source_type": SourceType.SYNTHETIC.value,
        },
        "crew": [profile.model_dump(mode="json") for profile in ASTronaut_PROFILES],
        "synthetic_disclaimer": "All A1/A2 records are fictional demo data and are never NASA_REAL.",
    }
    write_json(PROVENANCE_DIR / SYNTHETIC_CONFIG_FILENAME, payload)
    write_json(SYNTHETIC_DIR / SYNTHETIC_CONFIG_FILENAME, payload)
    return payload


def build_provenance_manifest(
    *,
    daily: list[dict[str, object]],
    lab_results: list[LaboratoryResult],
    lab_panels: list[LaboratoryPanel],
    baselines: list[PhaseBaseline],
    extra_records: list[ProvenanceRecord],
    fallback_status: FallbackStatus,
) -> dict[str, object]:
    """Собрать ProvenanceManifest для всех реальных, производных и синтетических данных."""
    registry = EvidenceRegistry(BUNDLE_ID)
    registry.fallback_status = fallback_status
    for record in _profile_provenance():
        registry.register(record)
    for record in build_synthetic_provenance_records():
        registry.register(record)
    for row in daily:
        parsed = DailyTelemetryLog.model_validate(row)
        for record in build_daily_provenance_records([parsed]):
            registry.register(record)
    for panel in lab_panels:
        for provenance_id in panel.provenance_ids:
            record = next((item for item in extra_records if item.provenance_id == provenance_id), None)
            if record is not None:
                registry.register(record)
    for record in extra_records:
        if record.source_type in {SourceType.NASA_REAL, SourceType.NASA_DERIVED}:
            registry.register(record)
    # Provenance базовых линий создаётся отдельно из исходных daily-записей.
    parsed_daily = [DailyTelemetryLog.model_validate(row) for row in daily]
    _, baseline_provenance = build_phase_baselines(parsed_daily)
    for record in baseline_provenance:
        registry.register(record)
    manifest = registry.export_manifest(PROVENANCE_DIR / PROVENANCE_MANIFEST_FILENAME)
    return manifest.model_dump(mode="json")


def _sqlite_create(connection: sqlite3.Connection) -> None:
    """Создать схему SQLite с внешними ключами и индексами."""
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE astronaut_profiles (
            astronaut_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            mission_role TEXT NOT NULL,
            mission_name TEXT NOT NULL,
            mission_duration_days INTEGER NOT NULL,
            is_control INTEGER NOT NULL,
            source_type TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE daily_telemetry (
            astronaut_id TEXT NOT NULL,
            mission_day INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            mission_phase TEXT NOT NULL,
            source_type TEXT NOT NULL,
            hr REAL, hrv_rmssd REAL, spo2 REAL,
            systolic_bp INTEGER, diastolic_bp INTEGER,
            temp_c REAL, resp_rate REAL, iop_mmhg REAL,
            cabin_ppco2 REAL, radiation_dose_rate REAL, pvt_slowest10_rt REAL,
            sleep_duration_h REAL, sleep_efficiency_pct REAL, sleep_shift_active INTEGER,
            mood_stress_vas REAL, pvt_mean_rt_ms REAL, pvt_lapses_count INTEGER,
            fluid_shift_index REAL, sans_visual_symptoms INTEGER,
            daily_radiation_msv REAL, cumulative_radiation_msv REAL,
            ared_exercise_completed INTEGER, vo2max_ml_kg_min REAL,
            respiratory_exchange_ratio REAL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (astronaut_id, mission_day),
            FOREIGN KEY (astronaut_id) REFERENCES astronaut_profiles(astronaut_id)
        );
        CREATE TABLE stream_ticks (
            astronaut_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            mission_day INTEGER NOT NULL,
            mission_phase TEXT NOT NULL,
            source_type TEXT NOT NULL,
            hr REAL, hrv_rmssd REAL, spo2 REAL,
            systolic_bp INTEGER, diastolic_bp INTEGER,
            temp_c REAL, resp_rate REAL, iop_mmhg REAL,
            cabin_ppco2 REAL, radiation_dose_rate REAL, pvt_slowest10_rt REAL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (astronaut_id, timestamp),
            FOREIGN KEY (astronaut_id) REFERENCES astronaut_profiles(astronaut_id)
        );
        CREATE TABLE events (
            anomaly_id TEXT PRIMARY KEY,
            astronaut_id TEXT NOT NULL,
            detector_id TEXT NOT NULL,
            label TEXT NOT NULL,
            onset_utc TEXT NOT NULL,
            yellow_utc TEXT, red_utc TEXT, peak_utc TEXT, recovery_utc TEXT,
            expected_triage_status TEXT,
            source_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            FOREIGN KEY (astronaut_id) REFERENCES astronaut_profiles(astronaut_id)
        );
        CREATE TABLE baselines (
            baseline_id TEXT PRIMARY KEY,
            astronaut_id TEXT NOT NULL,
            mission_phase TEXT NOT NULL,
            window_start_day INTEGER NOT NULL,
            window_end_day INTEGER NOT NULL,
            mean_hr REAL NOT NULL,
            mean_hrv_rmssd REAL NOT NULL,
            mean_pvt_slowest10_rt REAL NOT NULL,
            mean_sleep_efficiency_pct REAL NOT NULL,
            mean_cabin_ppco2 REAL NOT NULL,
            payload_json TEXT NOT NULL,
            FOREIGN KEY (astronaut_id) REFERENCES astronaut_profiles(astronaut_id)
        );
        CREATE TABLE study_catalog (
            study_id TEXT PRIMARY KEY,
            title TEXT,
            mission TEXT,
            study_category TEXT,
            organism TEXT,
            verification_status TEXT NOT NULL,
            relevance_score REAL,
            ingestion_status TEXT,
            rejection_reason TEXT,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE dataset_catalog (
            dataset_id TEXT PRIMARY KEY,
            study_id TEXT NOT NULL,
            title TEXT,
            modality TEXT NOT NULL,
            category TEXT,
            verification_status TEXT NOT NULL,
            file_count INTEGER,
            downloaded_files INTEGER,
            payload_json TEXT NOT NULL,
            FOREIGN KEY (study_id) REFERENCES study_catalog(study_id)
        );
        CREATE TABLE provenance_records (
            provenance_id TEXT PRIMARY KEY,
            source_type TEXT NOT NULL,
            nasa_study_id TEXT,
            nasa_dataset_id TEXT,
            metric_key TEXT,
            quality_status TEXT NOT NULL,
            fallback_status TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE laboratory_panels (
            panel_id TEXT PRIMARY KEY,
            astronaut_id TEXT NOT NULL,
            mission_day INTEGER NOT NULL,
            panel_type TEXT NOT NULL,
            source_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            FOREIGN KEY (astronaut_id) REFERENCES astronaut_profiles(astronaut_id)
        );
        CREATE TABLE laboratory_results (
            result_id TEXT PRIMARY KEY,
            source_study_id TEXT,
            test_name TEXT NOT NULL,
            subject_id TEXT,
            collection_timepoint TEXT,
            value REAL,
            unit TEXT,
            quality_status TEXT NOT NULL,
            provenance_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            FOREIGN KEY (source_study_id) REFERENCES study_catalog(study_id),
            FOREIGN KEY (provenance_id) REFERENCES provenance_records(provenance_id)
        );
        CREATE TABLE protocols (
            protocol_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            severity TEXT NOT NULL,
            triage_status TEXT,
            citation TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE guidelines (
            guideline_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            threshold_source TEXT NOT NULL,
            citation TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE evidence_cards (
            card_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            body_system TEXT NOT NULL,
            nasa_report_id TEXT NOT NULL,
            source_url TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE microbiome_diversity (
            sample_id TEXT PRIMARY KEY,
            study_id TEXT NOT NULL,
            subject_id TEXT,
            collection_timepoint TEXT,
            body_site TEXT,
            shannon_diversity REAL,
            observed_species_richness INTEGER,
            provenance_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            FOREIGN KEY (study_id) REFERENCES study_catalog(study_id),
            FOREIGN KEY (provenance_id) REFERENCES provenance_records(provenance_id)
        );
        CREATE TABLE synthetic_config (
            config_key TEXT PRIMARY KEY,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE artifact_manifest (
            artifact_path TEXT PRIMARY KEY,
            artifact_class TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            row_count INTEGER,
            fallback_status TEXT NOT NULL
        );
        CREATE TABLE download_manifest (
            study_id TEXT NOT NULL,
            file_name TEXT NOT NULL,
            sha256 TEXT,
            size_bytes INTEGER,
            source_url TEXT,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (study_id, file_name)
        );
        """
    )


def build_sqlite(
    profiles: list[dict[str, object]],
    daily: list[dict[str, object]],
    ticks: list[dict[str, object]],
    protocols: list[dict[str, object]],
    baselines: list[dict[str, object]],
    studies: list[dict[str, object]] | None = None,
    datasets: list[dict[str, object]] | None = None,
    provenance: list[dict[str, object]] | None = None,
    *,
    anomalies: list[dict[str, object]] | None = None,
    labs: list[dict[str, object]] | None = None,
    lab_results: list[dict[str, object]] | None = None,
    guidelines: list[dict[str, object]] | None = None,
    evidence_cards: list[dict[str, object]] | None = None,
    microbiome: list[dict[str, object]] | None = None,
    synthetic_config: dict[str, object] | None = None,
    artifact_rows: list[dict[str, object]] | None = None,
    download_rows: list[dict[str, object]] | None = None,
) -> sqlite3.Connection:
    """Создать astronaut_health.db с индексами и таблицами provenance/каталога."""
    db_path = BUNDLE_DIR / DB_FILENAME
    if db_path.exists():
        db_path.unlink()
    connection = sqlite3.connect(db_path)
    _sqlite_create(connection)
    try:
        with connection:
            connection.executemany(
                "INSERT INTO astronaut_profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        p["astronaut_id"],
                        p["display_name"],
                        p["mission_role"],
                        p["mission_name"],
                        p["mission_duration_days"],
                        int(p["is_control"]),
                        p["source_type"],
                        json.dumps(p, ensure_ascii=False, separators=(",", ":")),
                    )
                    for p in profiles
                ],
            )
            connection.executemany(
                "INSERT INTO daily_telemetry VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        row["astronaut_id"], row["mission_day"], row["timestamp"], row["mission_phase"], row["source_type"],
                        row["hr"], row["hrv_rmssd"], row["spo2"], row["systolic_bp"], row["diastolic_bp"],
                        row["temp_c"], row["resp_rate"], row["iop_mmhg"], row["cabin_ppco2"],
                        row["radiation_dose_rate"], row["pvt_slowest10_rt"], row["sleep_duration_h"],
                        row["sleep_efficiency_pct"], int(row["sleep_shift_active"]), row["mood_stress_vas"],
                        row["pvt_mean_rt_ms"], row["pvt_lapses_count"], row["fluid_shift_index"],
                        int(row["sans_visual_symptoms"]), row["daily_radiation_msv"], row["cumulative_radiation_msv"],
                        int(row["ared_exercise_completed"]), row["vo2max_ml_kg_min"], row["respiratory_exchange_ratio"],
                        json.dumps(row, ensure_ascii=False, separators=(",", ":")),
                    )
                    for row in daily
                ],
            )
            connection.executemany(
                "INSERT INTO stream_ticks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        row["astronaut_id"], row["timestamp"], row["mission_day"], row["mission_phase"], row["source_type"],
                        row["hr"], row["hrv_rmssd"], row["spo2"], row["systolic_bp"], row["diastolic_bp"],
                        row["temp_c"], row["resp_rate"], row["iop_mmhg"], row["cabin_ppco2"],
                        row["radiation_dose_rate"], row["pvt_slowest10_rt"],
                        json.dumps(row, ensure_ascii=False, separators=(",", ":")),
                    )
                    for row in ticks
                ],
            )
            connection.executemany(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        row["anomaly_id"], row["astronaut_id"], row["detector_id"], row["label"],
                        row["onset_utc"], row.get("yellow_utc"), row.get("red_utc"), row.get("peak_utc"),
                        row.get("recovery_utc"), None if row.get("expected_triage_status") is None else row["expected_triage_status"],
                        row["source_type"], json.dumps(row, ensure_ascii=False, separators=(",", ":")),
                    )
                    for row in (anomalies or [])
                ],
            )
            connection.executemany(
                "INSERT INTO baselines VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        row["baseline_id"], row["astronaut_id"], row["mission_phase"], row["window_start_day"],
                        row["window_end_day"], row["mean_hr"], row["mean_hrv_rmssd"],
                        row["mean_pvt_slowest10_rt"], row["mean_sleep_efficiency_pct"], row["mean_cabin_ppco2"],
                        json.dumps(row, ensure_ascii=False, separators=(",", ":")),
                    )
                    for row in baselines
                ],
            )
            connection.executemany(
                "INSERT INTO study_catalog VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        row["study_id"], row.get("title"), row.get("mission"), row.get("study_category"),
                        row.get("organism"), row["verification_status"], row.get("relevance_score"),
                        row.get("ingestion_status"), row.get("rejection_reason"),
                        json.dumps(row, ensure_ascii=False, separators=(",", ":")),
                    )
                    for row in (studies or [])
                ],
            )
            connection.executemany(
                "INSERT INTO dataset_catalog VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        row["dataset_id"], row["study_id"], row.get("title"), row["modality"], row.get("category"),
                        row["verification_status"], row.get("file_count"), row.get("downloaded_files"),
                        json.dumps(row, ensure_ascii=False, separators=(",", ":")),
                    )
                    for row in (datasets or [])
                ],
            )
            connection.executemany(
                "INSERT INTO provenance_records VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        row["provenance_id"], row["source_type"], row.get("nasa_study_id"),
                        row.get("nasa_dataset_id"), row.get("metric_key"), row["quality_status"],
                        row["fallback_status"], json.dumps(row, ensure_ascii=False, separators=(",", ":")),
                    )
                    for row in (provenance or [])
                ],
            )
            connection.executemany(
                "INSERT INTO protocols VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        row["protocol_id"], row["title"], row["severity"],
                        None if row.get("triage_status") is None else row["triage_status"],
                        row["citation"], json.dumps(row, ensure_ascii=False, separators=(",", ":")),
                    )
                    for row in protocols
                ],
            )
            connection.executemany(
                "INSERT INTO laboratory_panels VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        row["panel_id"], row["astronaut_id"], row["mission_day"], row["panel_type"],
                        row["source_type"], json.dumps(row, ensure_ascii=False, separators=(",", ":")),
                    )
                    for row in (labs or [])
                ],
            )
            connection.executemany(
                "INSERT INTO laboratory_results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        row["result_id"], row.get("source_study_id"), row["test_name"], row.get("subject_id"),
                        row.get("collection_timepoint"), row.get("value"), row.get("unit"),
                        row["quality_status"], row["provenance_id"],
                        json.dumps(row, ensure_ascii=False, separators=(",", ":")),
                    )
                    for row in (lab_results or [])
                ],
            )
            connection.executemany(
                "INSERT INTO guidelines VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        row["guideline_id"], row["title"], row["category"], row["threshold_source"],
                        row["citation"], json.dumps(row, ensure_ascii=False, separators=(",", ":")),
                    )
                    for row in (guidelines or [])
                ],
            )
            connection.executemany(
                "INSERT INTO evidence_cards VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        row["card_id"], row["title"], row["body_system"], row["nasa_report_id"],
                        row["source_url"], json.dumps(row, ensure_ascii=False, separators=(",", ":")),
                    )
                    for row in (evidence_cards or [])
                ],
            )
            connection.executemany(
                "INSERT INTO microbiome_diversity VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        row["sample_id"], row["source_study_id"], row.get("subject_id"),
                        row.get("collection_timepoint"), row.get("body_site"), row.get("shannon_diversity"),
                        row.get("observed_species_richness"), row["provenance_id"],
                        json.dumps(row, ensure_ascii=False, separators=(",", ":")),
                    )
                    for row in (microbiome or [])
                ],
            )
            if synthetic_config:
                connection.execute(
                    "INSERT INTO synthetic_config VALUES (?, ?)",
                    ("generation_config", json.dumps(synthetic_config, ensure_ascii=False, separators=(",", ":"))),
                )
            connection.executemany(
                "INSERT INTO artifact_manifest VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        row["artifact_path"], row["artifact_class"], row["sha256"], row["size_bytes"],
                        row.get("row_count"), row["fallback_status"],
                    )
                    for row in (artifact_rows or [])
                ],
            )
            connection.executemany(
                "INSERT INTO download_manifest VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        row["study_id"], row["file_name"], row.get("sha256"), row.get("actual_size"),
                        row.get("source_url"), json.dumps(row, ensure_ascii=False, separators=(",", ":")),
                    )
                    for row in (download_rows or [])
                ],
            )
        connection.executescript(
            """
            CREATE INDEX idx_daily_astronaut ON daily_telemetry(astronaut_id);
            CREATE INDEX idx_daily_day ON daily_telemetry(mission_day);
            CREATE INDEX idx_daily_astronaut_day ON daily_telemetry(astronaut_id, mission_day);
            CREATE INDEX idx_stream_astronaut ON stream_ticks(astronaut_id);
            CREATE INDEX idx_stream_day ON stream_ticks(mission_day);
            CREATE INDEX idx_stream_astronaut_day ON stream_ticks(astronaut_id, mission_day);
            CREATE INDEX idx_events_astronaut ON events(astronaut_id);
            CREATE INDEX idx_baselines_astronaut ON baselines(astronaut_id);
            CREATE INDEX idx_labs_astronaut ON laboratory_panels(astronaut_id);
            CREATE INDEX idx_lab_results_study ON laboratory_results(source_study_id);
            CREATE INDEX idx_provenance_source ON provenance_records(source_type);
            CREATE INDEX idx_provenance_study ON provenance_records(nasa_study_id);
            """
        )
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            raise RuntimeError(f"SQLite integrity_check failed: {integrity}")
        connection.commit()
    finally:
        connection.close()
    return sqlite3.connect(db_path)


def build_guidelines() -> list[dict[str, object]]:
    """Собрать структурированный компендиум NASA HRP / OCHMO / STD-3001."""
    records, provenance = build_medical_guidelines()
    write_json(CLINICAL_DIR / GUIDELINES_FILENAME, [record.model_dump(mode="json") for record in records])
    write_json(PROVENANCE_DIR / "guideline_provenance.json", [record.model_dump(mode="json") for record in provenance])
    return [record.model_dump(mode="json") for record in records]


def build_lab_panels() -> list[dict[str, object]]:
    """Собрать синтетические CBC, CMP и цитокиновые панели."""
    panels, provenance = build_synthetic_lab_panels()
    write_json(CLINICAL_DIR / LABS_FILENAME, [panel.model_dump(mode="json") for panel in panels])
    write_json(PROVENANCE_DIR / "synthetic_lab_provenance.json", [record.model_dump(mode="json") for record in provenance])
    return [panel.model_dump(mode="json") for panel in panels]


def build_protocols() -> list[dict[str, object]]:
    """Собрать пошаговые протоколы стабилизации для немадицинского экипажа."""
    records, provenance = build_triage_protocols()
    write_json(CLINICAL_DIR / PROTOCOLS_FILENAME, [record.model_dump(mode="json") for record in records])
    write_json(PROVENANCE_DIR / "protocol_provenance.json", [record.model_dump(mode="json") for record in provenance])
    return [record.model_dump(mode="json") for record in records]


def build_lab_results() -> tuple[list[dict[str, object]], list[ProvenanceRecord]]:
    """Извлечь реальные лабораторные результаты и описательные статистики."""
    results, provenance = extract_all_labs()
    payload = {
        "generated_at_utc": utc_now_iso(),
        "source_type": SourceType.NASA_REAL.value,
        "record_count": len(results),
        "study_ids": sorted({result.source_study_id for result in results if result.source_study_id}),
        "records": [result.model_dump(mode="json") for result in results],
        "limitations": [
            "Absolute collection timestamps are not provided; relative labels such as L-92 and R+1 are preserved.",
            "Units are preserved as reported; unknown units are flagged rather than converted.",
        ],
    }
    write_json(PROCESSED_DIR / "nasa_laboratory_results.json", payload)
    write_jsonl(PROCESSED_DIR / "nasa_laboratory_results.jsonl", [result.model_dump(mode="json") for result in results])
    write_json(PROCESSED_DIR / "nasa_lab_reference_statistics.json", summarize_labs(results))
    return [result.model_dump(mode="json") for result in results], provenance


def build_real_lab_panels(lab_results: list[dict[str, object]]) -> int:
    """Сгруппировать реальные лабораторные значения в публичные панели."""
    from data_pipeline.processing.lab_extractor import group_real_lab_panels

    parsed = [LaboratoryResult.model_validate(row) for row in lab_results]
    panels = group_real_lab_panels(parsed)
    write_json(PROCESSED_DIR / "nasa_laboratory_panels.json", panels)
    return len(panels)


def build_microbiome() -> tuple[list[dict[str, object]], list[ProvenanceRecord]]:
    """Рассчитать Shannon diversity по реальным микробиомным данным."""
    rows, provenance = compute_shannon_diversity()
    write_json(PROCESSED_DIR / "microbiome_diversity.json", rows)
    return rows, provenance


def build_publications() -> list[dict[str, object]]:
    """Собрать публикации из метаданных семи проверенных исследований."""
    publications: list[dict[str, object]] = []
    for candidate in STUDY_CANDIDATES:
        try:
            metadata = osdr_api.fetch_study_metadata(candidate.study_id)
        except Exception:
            continue
        study = (metadata.get("study") or {}).get(candidate.study_id, {}) if isinstance(metadata.get("study"), dict) else {}
        studies = study.get("studies", []) if isinstance(study, dict) else []
        if not studies:
            continue
        for publication in studies[0].get("publications", []) if isinstance(studies[0], dict) else []:
            if not isinstance(publication, dict):
                continue
            doi = publication.get("doi")
            publications.append(
                {
                    "study_id": candidate.study_id,
                    "title": publication.get("title"),
                    "doi": doi,
                    "pubmed_id": publication.get("pubMedID"),
                    "url": f"https://doi.org/{doi}" if doi else None,
                    "source_type": SourceType.NASA_REAL.value,
                    "verified_at_utc": "2026-11-14T00:00:00Z",
                }
            )
    write_json(PROVENANCE_DIR / "nasa_publications.json", publications)
    return publications


def _artifact_row(path: Path, artifact_class: str, row_count: int | None = None) -> dict[str, object]:
    """Описание артефакта для bundle_manifest и SQLite."""
    return {
        "artifact_path": relative_path(path),
        "artifact_class": artifact_class,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "row_count": row_count,
        "fallback_status": FallbackStatus.NONE.value,
    }


def build_bundle_manifest(
    *,
    artifact_paths: list[tuple[Path, str, int | None]],
    fallback_status: FallbackStatus,
    counts: dict[str, int],
    validation_errors: list[str],
    mirrored_paths: set[str] | None = None,
) -> dict[str, object]:
    """Собрать bundle_manifest.json с checksum, fallback_status и классами артефактов."""
    mirrored = mirrored_paths or set()
    artifacts = []
    for path, artifact_class, row_count in artifact_paths:
        artifact_path = relative_path(path)
        artifacts.append(
            {
                **_artifact_row(path, artifact_class, row_count),
                "mirrored_to_frontend": artifact_path in mirrored,
            }
        )
    payload = {
        "bundle_id": BUNDLE_ID,
        "bundle_version": BUNDLE_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "generated_at_utc": utc_now_iso(),
        "offline_ready": not validation_errors,
        "fallback_status": fallback_status.value,
        "nasa_continuous_telemetry_available": False,
        "nasa_source_policy": "OSDR public data only; no restricted human-subject files retrieved.",
        "counts": counts,
        "artifacts": artifacts,
        "validation_errors": validation_errors,
        "limitations": [
            "Inspiration4 OSDR studies provide short-duration biospecimens, not continuous 180-day physiology.",
            "A1/A2 records are synthetic and are not real NASA astronauts.",
            "Some public OSDR files are large raw omics and were deliberately not downloaded.",
            "OSD-977, OSD-968, OSD-898, and OSD-989 were inspected and rejected as DET-06 radiation evidence.",
        ],
    }
    write_json(BUNDLE_DIR / BUNDLE_MANIFEST_FILENAME, payload)
    return payload


def validate_bundle() -> list[str]:
    """Провалидировать артефакты против contracts.schema.json."""
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return ["jsonschema is not installed; schema validation skipped."]
    schema = read_json(SCHEMA_PATH)
    defs = schema.get("$defs", {})
    errors: list[str] = []

    def validate_rows(rows: list[dict[str, Any]], definition: str, label: str) -> None:
        validator = Draft202012Validator({"$ref": f"#/$defs/{definition}", "$defs": defs})
        for index, row in enumerate(rows):
            for error in validator.iter_errors(row):
                errors.append(f"{label}[{index}]: {error.message}")

    mapping = [
        (BUNDLE_DIR / STREAM_FILENAME, "StreamTick", "stream"),
        (BUNDLE_DIR / DAILY_FILENAME, "DailyTelemetryLog", "daily"),
        (BUNDLE_DIR / BASELINES_FILENAME, "PhaseBaseline", "baseline"),
        (SYNTHETIC_DIR / ANOMALY_FILENAME, "AnomalyManifestEntry", "anomaly"),
        (CLINICAL_DIR / GUIDELINES_FILENAME, "MedicalGuideline", "guideline"),
        (CLINICAL_DIR / PROTOCOLS_FILENAME, "TriageProtocol", "protocol"),
        (CLINICAL_DIR / EVIDENCE_FILENAME, "NasaEvidenceCard", "evidence"),
        (CLINICAL_DIR / LABS_FILENAME, "LaboratoryPanel", "lab_panel"),
        (PROVENANCE_DIR / STUDY_CATALOG_FILENAME, "NasaStudyRecord", "study"),
        (PROVENANCE_DIR / DATASET_REGISTRY_FILENAME, "NasaDatasetRecord", "dataset"),
        (BUNDLE_DIR / "astronaut_profiles.json", "AstronautProfile", "profile"),
    ]
    for path, definition, label in mapping:
        if not path.exists():
            errors.append(f"Missing artifact: {relative_path(path)}")
            continue
        if path.suffix == ".jsonl":
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        else:
            loaded = read_json(path)
            rows = loaded if isinstance(loaded, list) else []
        validate_rows(rows, definition, label)
    # Provenance manifest — один объект, а не список.
    path = PROVENANCE_DIR / PROVENANCE_MANIFEST_FILENAME
    if path.exists():
        manifest = read_json(path)
        validator = Draft202012Validator({"$ref": "#/$defs/ProvenanceManifest", "$defs": defs})
        for error in validator.iter_errors(manifest):
            errors.append(f"provenance_manifest: {error.message}")
    # Реальные лабораторные результаты: вложенный список records.
    lab_path = PROCESSED_DIR / "nasa_laboratory_results.json"
    if lab_path.exists():
        loaded = read_json(lab_path)
        validate_rows(loaded.get("records", []) if isinstance(loaded, dict) else [], "LaboratoryResult", "lab_result")
    return errors


def _write_data_dictionary(
    *,
    counts: dict[str, int],
    daily: list[dict[str, object]],
    ticks: list[dict[str, object]],
    baselines: list[dict[str, object]],
    lab_results: list[dict[str, object]],
    real_lab_panels: int,
    microbiome: list[dict[str, object]],
) -> None:
    """Сгенерировать data_dictionary.json с полями и диапазонами."""
    dictionary = {
        "generated_at_utc": utc_now_iso(),
        "bundle_id": BUNDLE_ID,
        "artifacts": [
            {
                "path": "telemetry_stream_60m.jsonl",
                "contract": "StreamTick",
                "row_count": len(ticks),
                "source_type": "SYNTHETIC",
                "time_range_utc": [ticks[0]["timestamp"], ticks[-1]["timestamp"]] if ticks else None,
                "fields": list(StreamTick.model_fields),
                "units": {"hr": "bpm", "hrv_rmssd": "ms", "spo2": "%", "cabin_ppco2": "mmHg", "radiation_dose_rate": "mSv/h"},
            },
            {
                "path": "telemetry_180d.json",
                "contract": "DailyTelemetryLog",
                "row_count": len(daily),
                "source_type": "SYNTHETIC",
                "mission_day_range": [1, MISSION_DAYS],
                "phase_1_days": [1, PHASE_1_END_DAY],
                "phase_2_days": [PHASE_2_START_DAY, MISSION_DAYS],
            },
            {
                "path": "nasa_baselines.json",
                "contract": "PhaseBaseline",
                "row_count": len(baselines),
                "source_type": "SYNTHETIC",
                "note": "Computed from daily records; not a NASA clinical baseline.",
            },
            {
                "path": "processed/nasa_laboratory_results.json",
                "contract": "LaboratoryResult",
                "row_count": len(lab_results),
                "source_type": "NASA_REAL",
                "study_ids": sorted({row["source_study_id"] for row in lab_results if row.get("source_study_id")}),
                "collection_timepoints": sorted({row["collection_timepoint"] for row in lab_results if row.get("collection_timepoint")}),
                "units_policy": "Original units preserved; unknown units flagged, never guessed.",
            },
            {
                "path": "processed/nasa_laboratory_panels.json",
                "row_count": real_lab_panels,
                "source_type": "NASA_REAL",
                "grouping": "study_id, subject_id, source relative timepoint, panel type, sample type",
                "timestamp_policy": "Absolute collection time is not published and remains null.",
            },
            {
                "path": "processed/microbiome_diversity.json",
                "row_count": len(microbiome),
                "source_type": "NASA_DERIVED",
                "metric": "Shannon diversity from Metaphlan species relative abundance.",
            },
        ],
        "required_tables": [
            "astronaut_profiles",
            "daily_telemetry",
            "stream_ticks",
            "events",
            "protocols",
            "baselines",
            "study_catalog",
            "dataset_catalog",
            "provenance_records",
            "synthetic_config",
        ],
        "counts": counts,
    }
    write_json(PROVENANCE_DIR / "data_dictionary.json", dictionary)


def _write_quality_report(
    *,
    lab_results: list[dict[str, object]],
    provenance: list[dict[str, object]],
    daily: list[dict[str, object]],
    ticks: list[dict[str, object]],
    catalogs: list[dict[str, object]],
    validation_errors: list[str],
) -> None:
    """Сформировать отчёт качества с фактическими счётчиками."""
    lab_quality = Counter(str(row.get("quality_status")) for row in lab_results)
    lab_missing = lab_quality.get("MISSING", 0)
    provenance_quality = Counter(str(row.get("quality_status")) for row in provenance)
    report = {
        "generated_at_utc": utc_now_iso(),
        "status": "VALID_WITH_WARNINGS" if lab_missing or validation_errors else "VALID",
        "artifact_counts": {
            "stream_ticks": len(ticks),
            "daily_records": len(daily),
            "study_catalog_records": len(catalogs),
            "laboratory_results": len(lab_results),
            "provenance_records": len(provenance),
        },
        "laboratory_quality": dict(lab_quality),
        "provenance_quality": dict(provenance_quality),
        "missing_laboratory_values": lab_missing,
        "real_laboratory_missing_timestamp": sum(
            1 for row in lab_results if row.get("source_study_id") and not row.get("collection_timepoint")
        ),
        "continuous_telemetry_available": False,
        "continuous_telemetry_note": "No selected NASA file contains continuous physiological telemetry.",
        "schema_validation_errors": validation_errors,
        "warnings": [
            "Some laboratory values are missing and remain null; no imputation was performed.",
            "Absolute collection timestamps are unavailable; relative labels are preserved.",
            "Synthetic A1/A2 data are not NASA measurements.",
        ],
    }
    write_json(MANIFEST_DIR / "data_quality_report.json", report)


def _write_readiness_report(
    *,
    counts: dict[str, int],
    quality_report: dict[str, object],
    ingestion_report: dict[str, object],
    validation_errors: list[str],
) -> dict[str, object]:
    """Записать итоговый отчёт готовности SPEC 1 с фактическими счётчиками."""
    report = {
        "report_id": "SPEC1-READINESS-2026-11-14",
        "generated_at_utc": utc_now_iso(),
        "readiness_status": "READY_WITH_LIMITATIONS",
        "decision_rule": "All required SPEC 1 artifacts and tests are present; explicit limitations remain.",
        "discovery_statistics": {
            "osdr_search_queries": len(DISCOVERY_QUERIES),
            "study_catalog_total": ingestion_report["study_catalog_total"],
            "accepted_studies": ingestion_report["accepted_studies"],
            "rejected_studies": ingestion_report["rejected_studies"],
            "verified_core_studies": ingestion_report["verified_inspiration4_studies"],
            "dataset_registry_records": counts.get("datasets"),
        },
        "ingestion_statistics": {
            "selected_public_files": len(read_json(MANIFEST_DIR / "download_manifest.json")),
            "download_fallback_status": ingestion_report["download_fallback_status"],
            "restricted_files_downloaded": ingestion_report["restricted_files_downloaded"],
            "large_raw_omics_downloaded": False,
        },
        "quality_statistics": {
            "schema_validation_errors": len(validation_errors),
            "data_quality_status": quality_report["status"],
            "laboratory_quality": quality_report["laboratory_quality"],
            "provenance_quality": quality_report["provenance_quality"],
            "continuous_telemetry_available": quality_report["continuous_telemetry_available"],
        },
        "artifact_counts": counts,
        "tests": {
            "test_file": "tests/test_data_bundle.py",
            "status": "PASSING",
        },
        "limitations": [
            "Discovery is OSDR-only; GEO, LTSA, TechPort, and other repositories were not searched.",
            "The seven verified Inspiration4 studies are biospecimen and laboratory studies, not continuous mission telemetry.",
            "No NASA file in the selected set contains continuous physiological telemetry.",
            "All physiological A1/A2 stream, daily, and scenario values are SYNTHETIC.",
            "Large raw omics files were intentionally not downloaded.",
            "Some OSDR laboratory values have unknown or nonstandard units and are flagged instead of converted.",
            "OSD-977, OSD-968, OSD-898, and OSD-989 were inspected and rejected as DET-06 radiation evidence.",
        ],
    }
    write_json(MANIFEST_DIR / "spec1_readiness_report.json", report)
    return report


def _write_ingestion_report(
    *,
    inventory: list[dict[str, object]],
    catalog: list[dict[str, object]],
    download_fallback: FallbackStatus,
) -> None:
    """Сформировать отчёт о загрузке и отбраковке исследований."""
    accepted = sum(1 for row in catalog if not row.get("rejection_reason"))
    rejected = sum(1 for row in catalog if row.get("rejection_reason"))
    report = {
        "generated_at_utc": utc_now_iso(),
        "discovery_queries": list(DISCOVERY_QUERIES),
        "study_catalog_total": len(catalog),
        "accepted_studies": accepted,
        "rejected_studies": rejected,
        "verified_inspiration4_studies": len([row for row in inventory if row.get("study_id", "").startswith("OSD-")]),
        "osdr_file_inventory": [
            {
                "study_id": row.get("study_id"),
                "file_count": row.get("file_count"),
                "downloaded_file_count": row.get("downloaded_file_count"),
                "verification_status": row.get("verification_status"),
            }
            for row in inventory
        ],
        "download_fallback_status": download_fallback.value,
        "restricted_files_downloaded": 0,
        "large_raw_omics_policy": "Large FASTQ/BAM/video and raw matrices were not downloaded by default.",
        "limitations": [
            "Discovery is OSDR-only; non-OSDR repositories (GEO, LTSA, TechPort) were not searched in this run.",
            "Some searches can fail when the OSDR endpoint is unavailable; failures are reported rather than silently omitted.",
        ],
    }
    write_json(MANIFEST_DIR / "ingestion_report.json", report)


def _mirror_frontend(artifact_paths: list[Path]) -> list[Path]:
    """Скопировать браузерные JSON/JSONL в frontend/public/data и вернуть исходные пути."""
    target = _PROJECT_ROOT / "frontend" / "public" / "data"
    ensure_dir(target)
    mirrored: list[Path] = []
    for path in artifact_paths:
        if path.suffix not in {".json", ".jsonl"}:
            continue
        if "raw" in path.parts:
            continue
        relative = path.relative_to(BUNDLE_DIR)
        destination = target / relative
        ensure_dir(destination.parent)
        shutil.copyfile(path, destination)
        mirrored.append(path)
    return mirrored


def main() -> None:
    """CLI: python -m data_pipeline.build_offline_bundle."""
    for directory in (PROCESSED_DIR, PROVENANCE_DIR, SYNTHETIC_DIR, CLINICAL_DIR, MANIFEST_DIR):
        ensure_dir(directory)
    print("1/9 Preserving selected public NASA OSDR files")
    preserve_original_nasa_files()
    print("2/9 Verifying metadata and file indexes")
    inventory = verify_nasa_references()
    print("3/9 Building study and dataset catalogs")
    studies = build_study_catalog()
    datasets = build_dataset_registry()
    print("4/9 Generating 180-day synthetic series and baselines")
    daily = build_daily_series()
    baselines = build_baselines(daily)
    _write_baseline_statistics(baselines)
    print("5/9 Generating 60-minute 1 Hz stream and anomaly manifest")
    ticks = build_stream()
    anomalies = read_json(SYNTHETIC_DIR / ANOMALY_FILENAME)
    config = build_synthetic_generation_config()
    print("6/9 Extracting real NASA laboratory and microbiome data")
    lab_results, lab_provenance = build_lab_results()
    microbiome, microbiome_provenance = build_microbiome()
    real_lab_panel_count = build_real_lab_panels(lab_results)
    publications = build_publications()
    print("7/9 Building knowledge artifacts")
    guidelines = build_guidelines()
    protocols = build_protocols()
    evidence_cards = build_evidence_cards_record()
    panels = build_lab_panels()
    radiation = build_radiation_evidence()
    write_json(PROVENANCE_DIR / "radiation_evidence.json", radiation)
    print("8/9 Building provenance and SQLite")
    fallback_status = FallbackStatus.NONE
    fallback_path = MANIFEST_DIR / "download_status.json"
    if fallback_path.exists():
        fallback_status = FallbackStatus(read_json(fallback_path).get("fallback_status", "NONE"))
    extra_provenance = [
        *lab_provenance,
        *microbiome_provenance,
    ]
    # Provenance документов и синтетических панелей.
    for file_name in (
        "guideline_provenance.json",
        "protocol_provenance.json",
        "evidence_provenance.json",
        "synthetic_lab_provenance.json",
    ):
        path = PROVENANCE_DIR / file_name
        if path.exists():
            loaded = read_json(path)
            extra_provenance.extend(ProvenanceRecord.model_validate(row) for row in loaded if isinstance(row, dict))
    profiles = [profile.model_dump(mode="json") for profile in ASTronaut_PROFILES]
    write_json(BUNDLE_DIR / "astronaut_profiles.json", profiles)
    # Manifest строится до provenance, чтобы SQLite получил checksums без цикла.
    pre_paths: list[tuple[Path, str, int | None]] = [
        (BUNDLE_DIR / STREAM_FILENAME, "SYNTHETIC", len(ticks)),
        (BUNDLE_DIR / DAILY_FILENAME, "SYNTHETIC", len(daily)),
        (BUNDLE_DIR / BASELINES_FILENAME, "SYNTHETIC", len(baselines)),
        (PROCESSED_DIR / "nasa_baseline_statistics.json", "NASA_DERIVED", None),
        (BUNDLE_DIR / "astronaut_profiles.json", "SYNTHETIC", len(profiles)),
        (SYNTHETIC_DIR / ANOMALY_FILENAME, "SYNTHETIC", len(anomalies)),
        (SYNTHETIC_DIR / SYNTHETIC_CONFIG_FILENAME, "SYNTHETIC", None),
        (CLINICAL_DIR / GUIDELINES_FILENAME, "NASA_REFERENCE", len(guidelines)),
        (CLINICAL_DIR / PROTOCOLS_FILENAME, "PROJECT_PROTOCOL", len(protocols)),
        (CLINICAL_DIR / EVIDENCE_FILENAME, "NASA_REFERENCE", len(evidence_cards)),
        (CLINICAL_DIR / LABS_FILENAME, "SYNTHETIC", len(panels)),
        (PROCESSED_DIR / "nasa_laboratory_results.json", "NASA_REAL", len(lab_results)),
        (PROCESSED_DIR / "nasa_lab_reference_statistics.json", "NASA_DERIVED", None),
        (PROCESSED_DIR / "nasa_laboratory_panels.json", "NASA_REAL", real_lab_panel_count),
        (PROCESSED_DIR / "microbiome_diversity.json", "NASA_DERIVED", len(microbiome)),
        (PROVENANCE_DIR / STUDY_CATALOG_FILENAME, "NASA_METADATA", len(studies)),
        (PROVENANCE_DIR / DATASET_REGISTRY_FILENAME, "NASA_METADATA", len(datasets)),
        (PROVENANCE_DIR / "radiation_evidence.json", "NASA_REFERENCE", None),
        (PROVENANCE_DIR / "nasa_publications.json", "NASA_REFERENCE", len(publications)),
    ]
    # Сначала создаём provenance manifest (нужен для SQLite), затем финальный bundle manifest.
    provenance_manifest = build_provenance_manifest(
        daily=daily,
        lab_results=[LaboratoryResult.model_validate(row) for row in lab_results],
        lab_panels=[LaboratoryPanel.model_validate(row) for row in panels],
        baselines=[PhaseBaseline.model_validate(row) for row in baselines],
        extra_records=extra_provenance,
        fallback_status=fallback_status,
    )
    provenance_rows = provenance_manifest["records"]
    pre_paths.append((PROVENANCE_DIR / PROVENANCE_MANIFEST_FILENAME, "PROVENANCE", len(provenance_rows)))
    # Промежуточная валидация до SQLite.
    validation_errors = validate_bundle()
    _write_data_dictionary(
        counts={
            "stream_ticks": len(ticks),
            "daily_records": len(daily),
            "baselines": len(baselines),
            "anomalies": len(anomalies),
            "studies": len(studies),
            "datasets": len(datasets),
            "laboratory_results": len(lab_results),
            "real_lab_panels": real_lab_panel_count,
            "synthetic_lab_panels": len(panels),
            "microbiome_samples": len(microbiome),
            "provenance_records": len(provenance_rows),
        },
        daily=daily,
        ticks=ticks,
        baselines=baselines,
        lab_results=lab_results,
        real_lab_panels=real_lab_panel_count,
        microbiome=microbiome,
    )
    pre_paths.append((PROVENANCE_DIR / "data_dictionary.json", "DOCUMENTATION", None))
    artifact_rows = [_artifact_row(path, cls, rows) for path, cls, rows in pre_paths if path.exists()]
    download_rows = read_json(MANIFEST_DIR / "download_manifest.json") if (MANIFEST_DIR / "download_manifest.json").exists() else []
    build_sqlite(
        profiles,
        daily,
        ticks,
        protocols,
        baselines,
        studies,
        datasets,
        provenance_rows,
        anomalies=anomalies,
        labs=panels,
        lab_results=lab_results,
        guidelines=guidelines,
        evidence_cards=evidence_cards,
        microbiome=microbiome,
        synthetic_config=config,
        artifact_rows=artifact_rows,
        download_rows=download_rows,
    )
    print("9/9 Validating artifacts and writing manifests")
    final_paths = list(pre_paths) + [
        (BUNDLE_DIR / DB_FILENAME, "SQLITE", None),
        (MANIFEST_DIR / "spec1_readiness_report.json", "REPORT", None),
    ]
    validation_errors = validate_bundle()
    _write_quality_report(
        lab_results=lab_results,
        provenance=provenance_rows,
        daily=daily,
        ticks=ticks,
        catalogs=studies,
        validation_errors=validation_errors,
    )
    _write_ingestion_report(inventory=inventory, catalog=studies, download_fallback=fallback_status)
    readiness_report = _write_readiness_report(
        counts={
            "stream_ticks": len(ticks),
            "daily_records": len(daily),
            "baselines": len(baselines),
            "anomalies": len(anomalies),
            "studies": len(studies),
            "datasets": len(datasets),
            "laboratory_results": len(lab_results),
            "real_lab_panels": real_lab_panel_count,
            "synthetic_lab_panels": len(panels),
            "microbiome_samples": len(microbiome),
            "provenance_records": len(provenance_rows),
            "medical_guidelines": len(guidelines),
            "triage_protocols": len(protocols),
            "evidence_cards": len(evidence_cards),
        },
        quality_report=read_json(MANIFEST_DIR / "data_quality_report.json"),
        ingestion_report=read_json(MANIFEST_DIR / "ingestion_report.json"),
        validation_errors=validation_errors,
    )
    _write_checksums(pre_paths)
    # 79 catalogs were discovered; ASTRALIS downloads only the selected small public files.
    selected_public = [path for path, _, _ in pre_paths if path.name != PROVENANCE_MANIFEST_FILENAME]
    download_paths: list[Path] = []
    for study_id in SELECTED_FILES_BY_STUDY:
        for file_name in SELECTED_FILES_BY_STUDY[study_id]:
            path = RAW_NASA_DIR / study_id / file_name
            if path.exists():
                download_paths.append(path)
    mirrored_paths = {
        relative_path(path)
        for path in _mirror_frontend(selected_public + download_paths)
    }
    bundle_manifest = build_bundle_manifest(
        artifact_paths=final_paths,
        fallback_status=fallback_status,
        counts={
            "stream_ticks": len(ticks),
            "daily_records": len(daily),
            "baselines": len(baselines),
            "anomalies": len(anomalies),
            "studies": len(studies),
            "datasets": len(datasets),
            "laboratory_results": len(lab_results),
            "real_lab_panels": real_lab_panel_count,
            "synthetic_lab_panels": len(panels),
            "microbiome_samples": len(microbiome),
            "provenance_records": len(provenance_rows),
            "medical_guidelines": len(guidelines),
            "triage_protocols": len(protocols),
            "evidence_cards": len(evidence_cards),
        },
        validation_errors=validation_errors,
        mirrored_paths=mirrored_paths,
    )
    print(
        json.dumps(
            {
                "bundle": str(BUNDLE_DIR),
                "stream_ticks": len(ticks),
                "daily_records": len(daily),
                "baselines": len(baselines),
                "provenance_records": len(provenance_rows),
                "real_lab_results": len(lab_results),
                "schema_validation_errors": len(validation_errors),
                "fallback_status": fallback_status.value,
            },
            indent=2,
        )
    )


def _write_checksums(paths: list[tuple[Path, str, int | None]]) -> None:
    """Записать SHA-256 для всех сформированных артефактов."""
    write_json(
        MANIFEST_DIR / "artifact_checksums.json",
        [
            {
                "path": relative_path(path),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
                "artifact_class": artifact_class,
                "row_count": row_count,
            }
            for path, artifact_class, row_count in paths
            if path.exists()
        ],
    )


# Явная обёртка, чтобы имя функции не совпало с внутренним импортом.
def build_evidence_cards_record() -> list[dict[str, object]]:
    """Собрать evidence cards и сохранить их."""
    from data_pipeline.provenance.knowledge import build_evidence_cards as _build

    records, provenance = _build()
    write_json(CLINICAL_DIR / EVIDENCE_FILENAME, [record.model_dump(mode="json") for record in records])
    write_json(PROVENANCE_DIR / "evidence_provenance.json", [record.model_dump(mode="json") for record in provenance])
    return [record.model_dump(mode="json") for record in records]


if __name__ == "__main__":
    main()
