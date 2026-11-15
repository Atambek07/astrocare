"""Проверки нормализации, контроля качества и происхождения данных NASA."""

from __future__ import annotations

from pathlib import Path

import pytest

from data_pipeline.processing.normalization import (
    normalize_measurement,
    normalize_timestamp,
    normalize_unit,
)
from data_pipeline.processing.quality_checks import (
    assess_quality,
    check_baseline_sufficiency,
    check_completeness,
    check_ranges,
    check_timestamps,
    check_units,
)
from data_pipeline.provenance.evidence_registry import EvidenceRegistry
from shared.contracts import FallbackStatus, ProvenanceRecord, QualityStatus, SourceType


def test_normalization_preserves_original_values() -> None:
    """Valid, missing and invalid measurements preserve the original source string."""
    valid = normalize_measurement("hemoglobin", "13.8", "g/dl")
    missing = normalize_measurement("hemoglobin", "N/A", "g/dl")
    invalid = normalize_measurement("hemoglobin", "not numeric", "g/dl")

    assert valid.normalized_value == 13.8
    assert valid.normalized_unit == "g/dL"
    assert valid.original_value == "13.8"
    assert valid.quality_status == QualityStatus.VALID
    assert missing.normalized_value is None
    assert missing.quality_status == QualityStatus.MISSING
    assert missing.original_value == "N/A"
    assert invalid.quality_status == QualityStatus.SUSPECT
    assert invalid.normalized_value is None
    assert invalid.original_value == "not numeric"


def test_unknown_units_are_flagged_not_converted() -> None:
    """An unknown unit must not receive an invented normalized unit."""
    result = normalize_measurement("custom_marker", "12.5", "laboratory units")
    assert result.normalized_value == 12.5
    assert result.normalized_unit is None
    assert result.quality_status == QualityStatus.VALID_WITH_WARNINGS
    assert normalize_unit("unknown") is None


def test_timestamps_do_not_fabricate_absolute_time() -> None:
    """Relative OSDR labels remain null instead of being invented as dates."""
    assert normalize_timestamp("2026-04-22T08:00:00Z") == "2026-04-22T08:00:00Z"
    assert normalize_timestamp("2026-04-22 09:30:00") == "2026-04-22T09:30:00Z"
    assert normalize_timestamp("L-92") is None
    assert normalize_timestamp("R+1") is None
    assert normalize_timestamp("N/A") is None


def test_quality_checks_report_missing_and_out_of_range_values() -> None:
    """Quality aggregation must retain missing and implausible metrics."""
    completeness = check_completeness(["hr", "spo2"], {"hr": 72, "spo2": None})
    units = check_units({"hr": "bpm", "spo2": None})
    ranges = check_ranges({"hr": 72.0, "spo2": 101.0})
    timestamps = check_timestamps(["2026-04-22T08:00:00Z", "2026-04-22T08:00:01Z"])
    combined = assess_quality([completeness, units, ranges, timestamps])

    assert completeness.missing_metrics == ["spo2"]
    assert units.invalid_units == ["spo2"]
    assert ranges.out_of_range_metrics == ["spo2"]
    assert combined.quality_status == QualityStatus.INVALID_UNIT
    assert combined.completeness_pct == 50.0


def test_baseline_sufficiency_gate() -> None:
    """Fewer than seven daily observations are insufficient for a clinical baseline."""
    assert check_baseline_sufficiency(6, 6) == QualityStatus.INSUFFICIENT_BASELINE
    assert check_baseline_sufficiency(7, 7) == QualityStatus.VALID


def _make_provenance_record(source_type: SourceType) -> ProvenanceRecord:
    """Create a minimal contract-valid provenance record for registry tests."""
    synthetic = source_type == SourceType.SYNTHETIC
    return ProvenanceRecord(
        provenance_id="PROV-TEST",
        source_type=source_type,
        nasa_study_id=None if synthetic else "OSD-569",
        nasa_dataset_id=None if synthetic else "CBC",
        source_file=None if synthetic else "sample.csv",
        source_url=None if synthetic else "https://example.gov/sample.csv",
        publication_reference=None,
        subject_id=None,
        collection_timepoint=None,
        measurement_timestamp=None,
        measurement_unit="g/dL",
        original_value="13.8",
        normalized_value=13.8,
        processing_method="identity",
        quality_status=QualityStatus.VALID,
        metric_key="hemoglobin",
        fallback_status=FallbackStatus.NONE,
        derived_from=[],
        source_verified_utc=None,
        notes="Registry test record",
        source_publication=None,
        sample_id=None,
        measurement_name="hemoglobin",
        original_unit="g/dL",
        normalized_unit="g/dL",
        processing_version="test-1.0",
        generated_at_utc=None,
        source_file_sha256=None,
        license_or_access_terms=None,
        download_timestamp=None,
        processing_timestamp=None,
        pipeline_version="test-1.0",
        generator_name="test-generator" if synthetic else None,
        generator_version="1.0" if synthetic else None,
        random_seed=42 if synthetic else None,
        scenario_id="TEST_SCENARIO" if synthetic else None,
        scenario_configuration={"profile": "test"} if synthetic else None,
        generation_timestamp=None,
    )


def test_registry_accepts_and_exports_nasa_real_provenance() -> None:
    """NASA_REAL records must remain traceable through the registry."""
    registry = EvidenceRegistry("TEST-BUNDLE")
    record = _make_provenance_record(SourceType.NASA_REAL)
    registry.register(record)
    exported = registry.export_manifest(Path("/tmp/opencode/astrocare_provenance_manifest.json"))
    assert exported.fallback_status == FallbackStatus.NONE
    assert exported.records[0].nasa_study_id == "OSD-569"


def test_registry_rejects_synthetic_nasa_identity() -> None:
    """SYNTHETIC records must never claim a NASA study or subject."""
    registry = EvidenceRegistry("TEST-BUNDLE")
    record = _make_provenance_record(SourceType.SYNTHETIC).model_copy(
        update={"nasa_study_id": "OSD-569"}
    )
    with pytest.raises(ValueError):
        registry.register(record)
