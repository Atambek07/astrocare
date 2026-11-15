"""Производные признаки микробиома из реальных OSDR-таблиц.

Shannon diversity рассчитывается по относительным обилиям видов Metaphlan.
Это описательная величина, а не клинический порог.
"""

from __future__ import annotations

import csv
import math
import re
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from shared.contracts import FallbackStatus, ProvenanceRecord, QualityStatus, SourceType  # noqa: E402
from data_pipeline.common import finite_float, sha256_file, utc_now_iso  # noqa: E402
from data_pipeline.processing.lab_extractor import MANIFEST_PATH  # noqa: E402

RAW_DIR = _PROJECT_ROOT / "data_bundle" / "raw" / "nasa"
METAPHLAN_FILE = RAW_DIR / "OSD-572" / "GLDS-564_GMetagenomics_Metaphlan-taxonomy_GLmetagenomics.tsv"
OSD572_URL = "https://osdr.nasa.gov/bio/repo/data/studies/OSD-572"
OSD572_PUBLICATION = "Longitudinal multi-omics analysis of host microbiome architecture (DOI: 10.1038/s41564-024-01635-8)"


def _sample_metadata(sample: str) -> tuple[str | None, str | None, str | None]:
    """Разобрать C001_L-3_EAR в subject, timepoint и site."""
    match = re.match(r"^(C\d+)_(L-\d+|R\+\d+|FD\d+)_([A-Z0-9]+)$", sample)
    if not match:
        return None, None, None
    return match.group(1), match.group(2), match.group(3)


def compute_shannon_diversity() -> tuple[list[dict[str, object]], list[ProvenanceRecord]]:
    """Рассчитать Shannon diversity по видам для каждого образца."""
    if not METAPHLAN_FILE.exists():
        return [], []
    rows: list[dict[str, object]] = []
    provenance: list[ProvenanceRecord] = []
    sha = sha256_file(METAPHLAN_FILE)
    with METAPHLAN_FILE.open(encoding="utf-8", errors="replace", newline="") as handle:
        lines = (line for line in handle if not line.startswith("#"))
        reader = csv.DictReader(lines, delimiter="\t")
        samples = [field for field in (reader.fieldnames or []) if field != "clade_name"]
        abundances: dict[str, dict[str, float]] = {sample: {} for sample in samples}
        for record in reader:
            clade = str(record.get("clade_name") or "")
            if not ("|s__" in clade or clade.startswith("s__")):
                continue
            for sample in samples:
                try:
                    value = float(record.get(sample) or 0.0)
                except ValueError:
                    continue
                if value > 0.0 and math.isfinite(value):
                    abundances[sample][clade] = value
    for sample in samples:
        values = abundances[sample]
        total = sum(values.values())
        if total <= 0.0:
            shannon = None
            richness = 0
        else:
            shannon = -sum((value / total) * math.log(value / total) for value in values.values())
            richness = len(values)
        subject, timepoint, site = _sample_metadata(sample)
        result_id = f"OSD-572-SHANNON-{sample}"
        rows.append(
            {
                "sample_id": sample,
                "subject_id": subject,
                "collection_timepoint": timepoint,
                "body_site": site,
                "shannon_diversity": finite_float(shannon),
                "observed_species_richness": richness,
                "source_study_id": "OSD-572",
                "source_type": SourceType.NASA_DERIVED.value,
                "provenance_id": f"PROV-{result_id}",
            }
        )
        provenance.append(
            ProvenanceRecord(
                provenance_id=f"PROV-{result_id}",
                source_type=SourceType.NASA_DERIVED,
                nasa_study_id="OSD-572",
                nasa_dataset_id="OSD-572-MICROBIOME",
                source_file=METAPHLAN_FILE.name,
                source_url=OSD572_URL,
                publication_reference=OSD572_PUBLICATION,
                subject_id=subject,
                collection_timepoint=timepoint,
                measurement_timestamp=None,
                measurement_unit="index",
                original_value=str(len(values)),
                normalized_value=finite_float(shannon),
                processing_method="shannon_diversity_from_species_relative_abundance",
                quality_status=QualityStatus.VALID if shannon is not None else QualityStatus.MISSING,
                metric_key="microbiome_shannon_diversity",
                fallback_status=FallbackStatus.NONE,
                derived_from=[],
                source_verified_utc=utc_now_iso(),
                notes="Descriptive Shannon diversity; not a diagnostic threshold.",
                source_publication=OSD572_PUBLICATION,
                sample_id=sample,
                measurement_name="Shannon diversity",
                original_unit="relative abundance",
                normalized_unit="index",
                processing_version="microbiome-diversity-1.0.0",
                generated_at_utc=utc_now_iso(),
                source_file_sha256=sha,
                license_or_access_terms="OSDR public dataset. See source URL for data-use terms.",
                processing_timestamp=utc_now_iso(),
                pipeline_version="astralis-data-1.0.0",
                generator_name=None,
                generator_version=None,
                random_seed=None,
                scenario_id=None,
                scenario_configuration=None,
                generation_timestamp=None,
            )
        )
    return rows, provenance
