"""Реестр доказательств и происхождения.

Каждая измеренная величина и каждый производный признак получают
ProvenanceRecord. SYNTHETIC-записи не могут ссылаться на NASA study/subject.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from shared.contracts import (  # noqa: E402
    FallbackStatus,
    ProvenanceManifest,
    ProvenanceRecord,
    SourceType,
    VerificationStatus,
)
from data_pipeline.common import utc_now_iso, write_json  # noqa: E402

PROVENANCE_MANIFEST_FILENAME: str = "provenance_manifest.json"
EVIDENCE_REGISTRY_FILENAME: str = "evidence_registry.json"
MIN_CONFIDENCE_FOR_CLINICAL_USE: float = 0.60


class EvidenceRegistry:
    """In-memory реестр provenance-записей с экспортом в офлайн-бандл."""

    def __init__(self, bundle_id: str) -> None:
        self.bundle_id = bundle_id
        self.records: dict[str, ProvenanceRecord] = {}
        self.fallback_status: FallbackStatus = FallbackStatus.NONE
        self.verification: dict[str, VerificationStatus] = {}

    def register(self, record: ProvenanceRecord) -> None:
        """Добавить запись; дубликаты provenance_id запрещены."""
        if record.provenance_id in self.records:
            raise ValueError(f"Duplicate provenance_id: {record.provenance_id}")
        problems = self.validate_record(record)
        if problems:
            raise ValueError("Invalid provenance record: " + "; ".join(problems))
        self.records[record.provenance_id] = record

    def get(self, provenance_id: str) -> ProvenanceRecord | None:
        """Вернуть запись по ID или None."""
        return self.records.get(provenance_id)

    def link_derived(self, child_id: str, parent_ids: list[str]) -> None:
        """Связать производный признак с исходными записями."""
        child = self.records.get(child_id)
        if child is None:
            raise KeyError(f"Unknown child provenance_id: {child_id}")
        unknown = [parent for parent in parent_ids if parent not in self.records]
        if unknown:
            raise KeyError(f"Unknown parent provenance IDs: {', '.join(unknown)}")
        updated = child.model_copy(update={"derived_from": sorted(set(child.derived_from + parent_ids))})
        self.records[child_id] = updated

    def validate_record(self, record: ProvenanceRecord) -> list[str]:
        """Проверить обязательные поля и запрет выдуманных NASA-значений."""
        problems: list[str] = []
        if source_type_requires_nasa_fields(record.source_type):
            if not record.nasa_study_id and not record.nasa_dataset_id:
                problems.append("NASA source requires nasa_study_id or a NASA document/dataset ID")
            if record.subject_id is not None and not record.source_file and not record.nasa_dataset_id:
                problems.append("Subject provenance lacks a source file or dataset")
        else:
            if record.nasa_study_id is not None or record.subject_id is not None:
                problems.append("SYNTHETIC record must not claim NASA study or subject")
            if not record.generator_name or not record.generator_version:
                problems.append("SYNTHETIC record requires generator_name and generator_version")
            if record.random_seed is None or not record.scenario_id:
                problems.append("SYNTHETIC record requires random_seed and scenario_id")
        if record.normalized_value is None and record.quality_status.value == "VALID":
            problems.append("VALID record cannot have a null normalized_value")
        return problems

    def mark_fallback(self, status: FallbackStatus) -> None:
        """Зафиксировать деградацию источника для manifest.fallback_status."""
        priority = {
            FallbackStatus.NONE: 0,
            FallbackStatus.CACHE_FALLBACK: 1,
            FallbackStatus.SYNTHETIC_FALLBACK: 2,
            FallbackStatus.UNAVAILABLE: 3,
        }
        if priority[status] >= priority[self.fallback_status]:
            self.fallback_status = status

    def export_manifest(
        self,
        destination: Path,
        *,
        manifest_version: str = "1.0.0",
    ) -> ProvenanceManifest:
        """Экспортировать ProvenanceManifest в JSON."""
        manifest = ProvenanceManifest(
            manifest_id=f"PROV-MANIFEST-{self.bundle_id}",
            bundle_id=self.bundle_id,
            manifest_version=manifest_version,
            generated_at_utc=utc_now_iso(),
            fallback_status=self.fallback_status,
            records=sorted(self.records.values(), key=lambda record: record.provenance_id),
        )
        write_json(destination, manifest.model_dump(mode="json"))
        return manifest

    def verification_status_for(self, study_id: str | None) -> VerificationStatus:
        """Вернуть статус проверки источника, не повышая его без оснований."""
        if study_id is None:
            return VerificationStatus.UNVERIFIED
        return self.verification.get(study_id, VerificationStatus.UNVERIFIED)


def source_type_requires_nasa_fields(source_type: SourceType) -> bool:
    """True для NASA_REAL/NASA_DERIVED, False для SYNTHETIC."""
    return source_type in {SourceType.NASA_REAL, SourceType.NASA_DERIVED}
