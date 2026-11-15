"""Минимальные проверки NASA-данных в едином репозитории AstroCare."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_nasa_manifest_exists() -> None:
    """NASA manifest must exist and record successful ingestion."""
    path = ROOT / "data" / "manifests" / "bundle_manifest.json"
    assert path.exists(), f"missing NASA bundle manifest: {path}"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["fallback_status"] == "NONE"
    assert payload["counts"]["laboratory_results"] > 0
    assert payload["nasa_continuous_telemetry_available"] is False


def test_study_catalog_contains_verified_osdr_studies() -> None:
    """The catalog must contain the seven verified OSDR studies."""
    path = ROOT / "data" / "reference" / "study_catalog.json"
    assert path.exists()
    rows = json.loads(path.read_text(encoding="utf-8"))
    ids = {row["study_id"] for row in rows}
    assert {"OSD-569", "OSD-570", "OSD-571", "OSD-572", "OSD-573", "OSD-575", "OSD-656"} <= ids


def test_radiation_evidence_rejects_non_radiation_studies() -> None:
    """Prompt-suggested radiation studies must be explicitly rejected, not reused."""
    path = ROOT / "data" / "reference" / "radiation_evidence.json"
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    rejected = {row["study_id"] for row in payload["rejected_reference_audit"]}
    assert {"OSD-977", "OSD-968", "OSD-898", "OSD-989"} <= rejected
