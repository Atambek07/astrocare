"""Синтетические демонстрационные лабораторные панели.

Панели создаются для A1/A2 на дни 1, 30, 90 и 180. Они не являются
измерениями реальных астронавтов и не копируют идентичности Inspiration4.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from shared.contracts import (  # noqa: E402
    FallbackStatus,
    LaboratoryPanel,
    LaboratoryResult,
    ProvenanceRecord,
    QualityStatus,
    SourceType,
)
from data_pipeline.common import finite_float, utc_now_iso  # noqa: E402

LAB_SEED: int = 20260501
LAB_SCENARIO_ID: str = "SYNTH-LAB-PANELS-180D"
LAB_GENERATOR_NAME: str = "astralis-lab-generator"
LAB_GENERATOR_VERSION: str = "astralis-lab-1.0.0"
LAB_START_UTC: str = "2026-04-22T08:00:00Z"
LAB_DAYS: tuple[int, ...] = (1, 30, 90, 180)

CBC_UNITS = {
    "wbc_10_3_ul": "10^3/uL",
    "rbc_10_6_ul": "10^6/uL",
    "hemoglobin_g_dl": "g/dL",
    "hematocrit_pct": "%",
    "platelets_10_3_ul": "10^3/uL",
    "neutrophils_pct": "%",
    "lymphocytes_pct": "%",
    "monocytes_pct": "%",
    "eosinophils_pct": "%",
    "basophils_pct": "%",
}
CMP_UNITS = {
    "glucose_mg_dl": "mg/dL",
    "creatinine_mg_dl": "mg/dL",
    "bun_mg_dl": "mg/dL",
    "sodium_mmol_l": "mmol/L",
    "potassium_mmol_l": "mmol/L",
    "chloride_mmol_l": "mmol/L",
    "co2_mmol_l": "mmol/L",
    "calcium_mg_dl": "mg/dL",
    "albumin_g_dl": "g/dL",
    "alt_u_l": "U/L",
    "ast_u_l": "U/L",
    "alkaline_phosphatase_u_l": "U/L",
    "bilirubin_mg_dl": "mg/dL",
}
CYTOKINE_UNITS = {
    "il6_pg_ml": "pg/mL",
    "tnf_alpha_pg_ml": "pg/mL",
    "crp_mg_l": "mg/L",
    "il10_pg_ml": "pg/mL",
    "ifn_gamma_pg_ml": "pg/mL",
    "il1_beta_pg_ml": "pg/mL",
}

A1_VALUES = {
    "CBC": {
        "wbc_10_3_ul": [6.2, 5.4, 5.8, 5.1],
        "rbc_10_6_ul": [4.72, 4.55, 4.61, 4.52],
        "hemoglobin_g_dl": [14.4, 13.9, 14.0, 13.7],
        "hematocrit_pct": [42.0, 40.6, 41.0, 40.2],
        "platelets_10_3_ul": [238.0, 226.0, 232.0, 221.0],
        "neutrophils_pct": [58.0, 61.0, 59.5, 60.2],
        "lymphocytes_pct": [29.0, 26.0, 27.5, 27.0],
        "monocytes_pct": [8.0, 8.4, 8.1, 8.5],
        "eosinophils_pct": [3.5, 3.2, 3.6, 3.0],
        "basophils_pct": [0.5, 0.5, 0.4, 0.4],
    },
    "CMP": {
        "glucose_mg_dl": [96.0, 102.0, 99.0, 104.0],
        "creatinine_mg_dl": [0.88, 0.92, 0.90, 0.95],
        "bun_mg_dl": [14.0, 16.0, 15.0, 17.0],
        "sodium_mmol_l": [139.0, 138.0, 139.0, 137.0],
        "potassium_mmol_l": [4.1, 4.0, 4.2, 3.9],
        "chloride_mmol_l": [103.0, 102.0, 103.0, 101.0],
        "co2_mmol_l": [24.0, 23.0, 24.0, 23.0],
        "calcium_mg_dl": [9.4, 9.2, 9.3, 9.1],
        "albumin_g_dl": [4.3, 4.1, 4.2, 4.0],
        "alt_u_l": [22.0, 26.0, 24.0, 28.0],
        "ast_u_l": [21.0, 25.0, 23.0, 27.0],
        "alkaline_phosphatase_u_l": [72.0, 70.0, 71.0, 69.0],
        "bilirubin_mg_dl": [0.7, 0.8, 0.7, 0.8],
    },
    "CYTOKINES": {
        "il6_pg_ml": [1.4, 2.2, 1.9, 2.8],
        "tnf_alpha_pg_ml": [1.1, 1.5, 1.3, 1.7],
        "crp_mg_l": [0.8, 1.6, 1.2, 2.0],
        "il10_pg_ml": [0.7, 1.1, 0.9, 1.3],
        "ifn_gamma_pg_ml": [2.0, 2.8, 2.4, 3.2],
        "il1_beta_pg_ml": [0.4, 0.7, 0.5, 0.8],
    },
}
A2_VALUES = {
    "CBC": {
        "wbc_10_3_ul": [5.8, 5.9, 5.7, 5.8],
        "rbc_10_6_ul": [4.85, 4.82, 4.88, 4.84],
        "hemoglobin_g_dl": [14.9, 14.8, 15.0, 14.9],
        "hematocrit_pct": [43.0, 42.8, 43.2, 43.0],
        "platelets_10_3_ul": [255.0, 252.0, 258.0, 254.0],
        "neutrophils_pct": [57.0, 57.5, 56.8, 57.2],
        "lymphocytes_pct": [30.0, 29.8, 30.2, 30.0],
        "monocytes_pct": [8.2, 8.0, 8.1, 8.1],
        "eosinophils_pct": [3.4, 3.3, 3.5, 3.4],
        "basophils_pct": [0.4, 0.4, 0.4, 0.4],
    },
    "CMP": {
        "glucose_mg_dl": [92.0, 94.0, 93.0, 95.0],
        "creatinine_mg_dl": [0.92, 0.91, 0.93, 0.92],
        "bun_mg_dl": [15.0, 15.0, 16.0, 15.0],
        "sodium_mmol_l": [140.0, 140.0, 139.0, 140.0],
        "potassium_mmol_l": [4.2, 4.1, 4.2, 4.2],
        "chloride_mmol_l": [104.0, 104.0, 103.0, 104.0],
        "co2_mmol_l": [25.0, 25.0, 24.0, 25.0],
        "calcium_mg_dl": [9.5, 9.5, 9.4, 9.5],
        "albumin_g_dl": [4.4, 4.4, 4.3, 4.4],
        "alt_u_l": [20.0, 21.0, 20.0, 21.0],
        "ast_u_l": [20.0, 20.0, 19.0, 20.0],
        "alkaline_phosphatase_u_l": [75.0, 74.0, 75.0, 74.0],
        "bilirubin_mg_dl": [0.6, 0.6, 0.7, 0.6],
    },
    "CYTOKINES": {
        "il6_pg_ml": [1.2, 1.2, 1.1, 1.2],
        "tnf_alpha_pg_ml": [1.0, 1.0, 0.9, 1.0],
        "crp_mg_l": [0.6, 0.6, 0.5, 0.6],
        "il10_pg_ml": [0.6, 0.6, 0.6, 0.6],
        "ifn_gamma_pg_ml": [1.9, 1.9, 2.0, 1.9],
        "il1_beta_pg_ml": [0.3, 0.3, 0.3, 0.3],
    },
}


def _timestamp(day: int) -> str:
    """UTC-таймстемп демонстрационной панели."""
    start = datetime.fromisoformat(LAB_START_UTC.replace("Z", "+00:00"))
    return (start + timedelta(days=day - 1)).astimezone(UTC).isoformat().replace("+00:00", "Z")


def _panel_provenance(
    *,
    panel_id: str,
    result: LaboratoryResult,
    astronaut_id: str,
    day: int,
) -> ProvenanceRecord:
    """Provenance для одного синтетического лабораторного результата."""
    return ProvenanceRecord(
        provenance_id=result.provenance_id,
        source_type=SourceType.SYNTHETIC,
        nasa_study_id=None,
        nasa_dataset_id=None,
        source_file=None,
        source_url=None,
        publication_reference=None,
        subject_id=None,
        collection_timepoint=f"DAY-{day}",
        measurement_timestamp=_timestamp(day),
        measurement_unit=result.unit,
        original_value=result.original_value,
        normalized_value=result.value,
        processing_method="synthetic_clinical_panel",
        quality_status=QualityStatus.VALIDATED,
        metric_key=f"synthetic_lab_{result.test_name.lower()}",
        fallback_status=FallbackStatus.NONE,
        derived_from=[],
        source_verified_utc=None,
        notes="Synthetic demo laboratory value; not a real astronaut measurement.",
        measurement_name=result.test_name,
        original_unit=result.unit,
        normalized_unit=result.normalized_unit,
        processing_version=LAB_GENERATOR_VERSION,
        generated_at_utc=utc_now_iso(),
        license_or_access_terms="Project-generated synthetic data",
        processing_timestamp=utc_now_iso(),
        pipeline_version="astralis-data-1.0.0",
        generator_name=LAB_GENERATOR_NAME,
        generator_version=LAB_GENERATOR_VERSION,
        random_seed=LAB_SEED,
        scenario_id=LAB_SCENARIO_ID,
        scenario_configuration={"astronaut_id": astronaut_id, "mission_day": day, "panel_id": panel_id},
        generation_timestamp=_timestamp(day),
    )


def build_synthetic_lab_panels() -> tuple[list[LaboratoryPanel], list[ProvenanceRecord]]:
    """Создать 24 демонстрационные панели и provenance каждого результата."""
    panels: list[LaboratoryPanel] = []
    provenance: list[ProvenanceRecord] = []
    for astronaut_id, value_table in (("A1", A1_VALUES), ("A2", A2_VALUES)):
        for panel_type in ("CBC", "CMP", "CYTOKINES"):
            units = CBC_UNITS if panel_type == "CBC" else CMP_UNITS if panel_type == "CMP" else CYTOKINE_UNITS
            for offset, day in enumerate(LAB_DAYS):
                panel_id = f"LAB-{astronaut_id}-D{day:03d}-{panel_type}"
                details: list[LaboratoryResult] = []
                results: dict[str, float] = {}
                provenance_ids: list[str] = []
                for analyte, unit in units.items():
                    value = finite_float(float(value_table[panel_type][analyte][offset]))
                    result_id = f"{panel_id}-{analyte}"
                    result = LaboratoryResult(
                        result_id=result_id,
                        test_name=analyte,
                        value=value,
                        original_value=str(value),
                        unit=unit,
                        normalized_unit=unit,
                        sample_type="whole blood" if panel_type == "CBC" else "serum",
                        collection_timepoint=f"DAY-{day}",
                        subject_id=astronaut_id,
                        source_study_id=None,
                        source_file=None,
                        assay_method=panel_type,
                        quality_status=QualityStatus.VALIDATED,
                        provenance_id=f"PROV-SYN-{result_id}",
                    )
                    details.append(result)
                    results[analyte] = value or 0.0
                    provenance_ids.append(result.provenance_id)
                    provenance.append(
                        _panel_provenance(
                            panel_id=panel_id,
                            result=result,
                            astronaut_id=astronaut_id,
                            day=day,
                        )
                    )
                interpretation = (
                    "Synthetic demo panel; values are within broad clinical ranges and are not diagnostic."
                    if astronaut_id == "A2"
                    else "Synthetic demo panel; mild post-flight-like changes are simulated, not measured."
                )
                panel = LaboratoryPanel(
                    panel_id=panel_id,
                    astronaut_id=astronaut_id,
                    collected_at_utc=_timestamp(day),
                    mission_day=day,
                    panel_type=panel_type,
                    source_type=SourceType.SYNTHETIC,
                    results=results,
                    interpretation=interpretation,
                    data_completeness_pct=100.0,
                    provenance_ids=provenance_ids,
                    subject_id=astronaut_id,
                    source_study_ids=[],
                    sample_type="whole blood" if panel_type == "CBC" else "serum",
                    quality_status=QualityStatus.VALIDATED,
                    results_detail=details,
                )
                panels.append(panel)
    return panels, provenance
