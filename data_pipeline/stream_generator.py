"""Генератор 60-минутного 1-Гц потока телеметрии.

A1 — основной астронавт с четырьмя заложенными аномалиями.
A2 — здоровый контроль без аномалий. Все записи SYNTHETIC.
"""

from __future__ import annotations

import json
import math
import random
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from shared.contracts import (  # noqa: E402
    AnomalyManifestEntry,
    BodySystemId,
    FallbackStatus,
    MissionPhase,
    ProvenanceRecord,
    QualityStatus,
    SourceType,
    StreamTick,
    TriageStatus,
)
from data_pipeline.common import finite_float, utc_now_iso, write_json, write_jsonl  # noqa: E402

STREAM_DURATION_MINUTES: int = 60
STREAM_FREQUENCY_HZ: int = 1
TICKS_PER_ASTRONAUT: int = STREAM_DURATION_MINUTES * 60 * STREAM_FREQUENCY_HZ
DEFAULT_SEED: int = 20260501
STREAM_START_UTC: str = "2026-05-01T08:00:00Z"
STREAM_MISSION_DAY: int = 10
STREAM_MISSION_PHASE: MissionPhase = MissionPhase.PHASE_1_ACUTE_ADAPTATION

CREW_IDS: tuple[str, ...] = ("A1", "A2")
CREW_SOURCE_TYPE: SourceType = SourceType.SYNTHETIC
SYNTHETIC_GENERATOR_NAME: str = "astralis-stream-generator"
SYNTHETIC_GENERATOR_VERSION: str = "astralis-stream-1.0.0"
SYNTHETIC_STUDY_ID: str | None = None
SYNTHETIC_DATASET_ID: str | None = None
SYNTHETIC_SUBJECT_PREFIX: str = "SYNTH"
SYNTHETIC_SCENARIO_ID: str = "SYNTH-STREAM-60M-A1-ANOMALIES"

A1_ANOMALY_WINDOWS: tuple[dict[str, object], ...] = (
    {
        "anomaly_id": "ANOM-A1-01",
        "detector_id": "DET-01",
        "label": "Hypercapnic Cabin & Nocturnal Pocket",
        "start_minute": 8,
        "end_minute": 18,
        "target_systems": ["RESPIRATORY_ENV", "NEURO_BEHAVIORAL"],
    },
    {
        "anomaly_id": "ANOM-A1-02",
        "detector_id": "DET-03",
        "label": "SANS Neuro-Ocular & Cephalad Fluid Shift",
        "start_minute": 22,
        "end_minute": 32,
        "target_systems": ["NEURO_OCULAR_SANS"],
    },
    {
        "anomaly_id": "ANOM-A1-03",
        "detector_id": "DET-05",
        "label": "Circadian Slam-Shift & Hypnotic Residual",
        "start_minute": 36,
        "end_minute": 46,
        "target_systems": ["NEURO_BEHAVIORAL", "ENDOCRINE_METABOLIC"],
    },
    {
        "anomaly_id": "ANOM-A1-04",
        "detector_id": "DET-06",
        "label": "SPE Acute Radiation & GCR Biological Impact",
        "start_minute": 48,
        "end_minute": 56,
        "target_systems": ["IMMUNE_MUSCULOSKELETAL", "ENDOCRINE_METABOLIC"],
    },
)

ANOMALY_TIMING: dict[str, dict[str, float]] = {
    "ANOM-A1-01": {"onset": 8, "yellow": 10, "red": 15, "peak": 16, "recovery": 19},
    "ANOM-A1-02": {"onset": 22, "yellow": 25, "red": 28, "peak": 30, "recovery": 34},
    "ANOM-A1-03": {"onset": 36, "yellow": 39, "red": 43, "peak": 44, "recovery": 49},
    "ANOM-A1-04": {"onset": 48, "yellow": 48, "red": 49, "peak": 50, "recovery": 57},
}

GENERATION_CONFIG_PATH: str = "data_bundle/synthetic/generation_config.json"
GENERATION_CONFIG: dict[str, object] = {
    "generator_name": SYNTHETIC_GENERATOR_NAME,
    "generator_version": SYNTHETIC_GENERATOR_VERSION,
    "seed": DEFAULT_SEED,
    "duration_minutes": STREAM_DURATION_MINUTES,
    "frequency_hz": STREAM_FREQUENCY_HZ,
    "ticks_per_astronaut": TICKS_PER_ASTRONAUT,
    "total_ticks": TICKS_PER_ASTRONAUT * len(CREW_IDS),
    "start_utc": STREAM_START_UTC,
    "mission_day": STREAM_MISSION_DAY,
    "mission_phase": STREAM_MISSION_PHASE.value,
    "crew_ids": list(CREW_IDS),
    "anomaly_windows": list(A1_ANOMALY_WINDOWS),
    "anomaly_timing_minutes": ANOMALY_TIMING,
    "source_type": CREW_SOURCE_TYPE.value,
    "study_id": SYNTHETIC_STUDY_ID,
    "scenario_id": SYNTHETIC_SCENARIO_ID,
    "notes": "Synthetic demo crew; not real NASA astronauts and not NASA telemetry.",
}

HEALTHY_BASELINE: dict[str, float] = {
    "hr": 68.0,
    "hrv_rmssd": 48.0,
    "spo2": 98.0,
    "systolic_bp": 118.0,
    "diastolic_bp": 74.0,
    "temp_c": 36.6,
    "resp_rate": 14.0,
    "cabin_ppco2": 2.4,
    "radiation_dose_rate": 0.012,
    "iop_mmhg": 16.0,
    "pvt_slowest10_rt": 285.0,
}

A2_BASELINE: dict[str, float] = {
    **HEALTHY_BASELINE,
    "hr": 65.0,
    "hrv_rmssd": 50.0,
    "pvt_slowest10_rt": 280.0,
    "cabin_ppco2": 2.3,
}


def _start_datetime(start_utc: str) -> datetime:
    """Разобрать стартовое UTC-время."""
    return datetime.fromisoformat(start_utc.replace("Z", "+00:00")).astimezone(UTC)


def _tick_timestamp(start_utc: str, second: int) -> str:
    """UTC-таймстемп тика с точностью до секунды."""
    return (_start_datetime(start_utc) + timedelta(seconds=second)).isoformat().replace("+00:00", "Z")


def _piecewise(minute: float, points: list[tuple[float, float]]) -> float:
    """Линейная интерполяция по контрольным точкам с clamp на краях."""
    if minute <= points[0][0]:
        return points[0][1]
    for (left_t, left_v), (right_t, right_v) in zip(points, points[1:]):
        if minute <= right_t:
            span = right_t - left_t
            if span <= 0:
                return right_v
            ratio = (minute - left_t) / span
            return left_v + (right_v - left_v) * ratio
    return points[-1][1]


def _a1_offsets(minute: float) -> dict[str, float]:
    """Рассчитать аддитивные сдвиги A1 для текущей минуты."""
    offsets = {
        "hr": 0.0,
        "hrv_rmssd": 0.0,
        "pvt_slowest10_rt": 0.0,
        "cabin_ppco2": 0.0,
        "iop_mmhg": 0.0,
        "radiation_dose_rate": 0.0,
    }
    # ANOM-A1-01: CO2, PVT, HRV, HR.
    if 8.0 <= minute <= 19.0:
        offsets["cabin_ppco2"] = _piecewise(
            minute,
            [(8.0, 0.0), (10.0, 1.0), (11.0, 1.6), (15.0, 1.8), (16.0, 1.8), (19.0, 0.0)],
        )
        offsets["pvt_slowest10_rt"] = _piecewise(
            minute,
            [(8.0, 0.0), (10.0, 80.0), (11.0, 100.0), (15.0, 135.0), (16.0, 135.0), (19.0, 0.0)],
        )
        offsets["hrv_rmssd"] = _piecewise(
            minute,
            [(8.0, 0.0), (10.0, -16.0), (11.0, -18.0), (15.0, -18.0), (16.0, -18.0), (19.0, 0.0)],
        )
        offsets["hr"] = _piecewise(
            minute,
            [(8.0, 0.0), (10.0, 8.0), (11.0, 10.0), (15.0, 12.0), (16.0, 12.0), (19.0, 0.0)],
        )
    # ANOM-A1-02: IOP, HRV, PVT.
    if 22.0 <= minute <= 34.0:
        offsets["iop_mmhg"] = _piecewise(
            minute,
            [(22.0, 0.0), (25.0, 4.0), (28.0, 8.0), (31.0, 8.0), (34.0, 0.0)],
        )
        offsets["hrv_rmssd"] += _piecewise(
            minute,
            [(22.0, 0.0), (25.0, -4.0), (28.0, -8.0), (31.0, -8.0), (34.0, 0.0)],
        )
        offsets["pvt_slowest10_rt"] += _piecewise(
            minute,
            [(22.0, 0.0), (25.0, 12.0), (28.0, 18.0), (31.0, 18.0), (34.0, 0.0)],
        )
    # ANOM-A1-03: PVT, HRV, HR.
    if 36.0 <= minute <= 49.0:
        offsets["pvt_slowest10_rt"] += _piecewise(
            minute,
            [(36.0, 0.0), (39.0, 50.0), (43.0, 105.0), (44.0, 105.0), (49.0, 0.0)],
        )
        offsets["hrv_rmssd"] += _piecewise(
            minute,
            [(36.0, 0.0), (39.0, -6.0), (43.0, -14.0), (44.0, -14.0), (49.0, 0.0)],
        )
        offsets["hr"] += _piecewise(
            minute,
            [(36.0, 0.0), (39.0, 4.0), (43.0, 10.0), (44.0, 10.0), (49.0, 0.0)],
        )
    # ANOM-A1-04: dose rate.
    if 48.0 <= minute <= 57.0:
        offsets["radiation_dose_rate"] = _piecewise(
            minute,
            [(48.0, 0.0), (49.0, 1.188), (51.0, 1.188), (57.0, 0.0)],
        )
    return offsets


def _build_tick(
    *,
    astronaut_id: str,
    second: int,
    start_utc: str,
    baseline: dict[str, float],
    rng: random.Random,
    with_anomalies: bool,
) -> StreamTick:
    """Собрать один детерминированный тик."""
    minute = second / 60.0
    offsets = _a1_offsets(minute) if with_anomalies and astronaut_id == "A1" else {key: 0.0 for key in baseline}
    hr = baseline["hr"] + offsets.get("hr", 0.0) + rng.gauss(0.0, 0.65) + 0.6 * math.sin(second / 17.0)
    hrv = baseline["hrv_rmssd"] + offsets.get("hrv_rmssd", 0.0) + rng.gauss(0.0, 0.9) + 0.9 * math.sin(second / 23.0)
    pvt = baseline["pvt_slowest10_rt"] + offsets.get("pvt_slowest10_rt", 0.0) + rng.gauss(0.0, 2.6)
    co2 = baseline["cabin_ppco2"] + offsets.get("cabin_ppco2", 0.0) + rng.gauss(0.0, 0.025)
    iop = baseline["iop_mmhg"] + offsets.get("iop_mmhg", 0.0) + rng.gauss(0.0, 0.12)
    dose = baseline["radiation_dose_rate"] + offsets.get("radiation_dose_rate", 0.0) + abs(rng.gauss(0.0, 0.0015))
    spo2 = baseline["spo2"] + rng.gauss(0.0, 0.18)
    systolic = baseline["systolic_bp"] + rng.gauss(0.0, 1.1)
    diastolic = baseline["diastolic_bp"] + rng.gauss(0.0, 0.8)
    return StreamTick(
        timestamp=_tick_timestamp(start_utc, second),
        mission_day=STREAM_MISSION_DAY,
        mission_phase=STREAM_MISSION_PHASE,
        astronaut_id=astronaut_id,
        source_type=CREW_SOURCE_TYPE,
        hr=finite_float(max(20.0, min(250.0, hr))) or baseline["hr"],
        hrv_rmssd=finite_float(max(0.0, min(300.0, hrv))) or baseline["hrv_rmssd"],
        spo2=finite_float(max(50.0, min(100.0, spo2))) or baseline["spo2"],
        systolic_bp=int(max(50, min(260, round(systolic)))),
        diastolic_bp=int(max(20, min(160, round(diastolic)))),
        temp_c=finite_float(baseline["temp_c"] + rng.gauss(0.0, 0.035)) or baseline["temp_c"],
        resp_rate=finite_float(baseline["resp_rate"] + rng.gauss(0.0, 0.35)) or baseline["resp_rate"],
        iop_mmhg=finite_float(max(0.0, min(60.0, iop))) or baseline["iop_mmhg"],
        cabin_ppco2=finite_float(max(0.0, min(20.0, co2))) or baseline["cabin_ppco2"],
        radiation_dose_rate=finite_float(max(0.0, min(1000.0, dose))) or baseline["radiation_dose_rate"],
        pvt_slowest10_rt=finite_float(max(100.0, min(1000.0, pvt))) or baseline["pvt_slowest10_rt"],
        provenance_ids=[f"PROV-SYN-{astronaut_id}-STREAM-{second:04d}"],
    )


def generate_stream(
    astronaut_id: str,
    seed: int = DEFAULT_SEED,
    with_anomalies: bool = True,
    start_utc: str = STREAM_START_UTC,
    provenance_ids: list[str] | None = None,
) -> list[StreamTick]:
    """Сгенерировать 3 600 синтетических тиков для одного астронавта."""
    if astronaut_id not in CREW_IDS:
        raise ValueError(f"Unknown synthetic astronaut: {astronaut_id}")
    baseline = A2_BASELINE if astronaut_id == "A2" else HEALTHY_BASELINE
    rng = random.Random(seed + (101 if astronaut_id == "A1" else 202))
    return [
        _build_tick(
            astronaut_id=astronaut_id,
            second=second,
            start_utc=start_utc,
            baseline=baseline,
            rng=rng,
            with_anomalies=with_anomalies,
        )
        for second in range(TICKS_PER_ASTRONAUT)
    ]


def generate_all_streams(seed: int = DEFAULT_SEED) -> list[StreamTick]:
    """Сгенерировать оба потока, чередуя по одному тику."""
    a1 = generate_stream("A1", seed=seed, with_anomalies=True)
    a2 = generate_stream("A2", seed=seed, with_anomalies=False)
    interleaved: list[StreamTick] = []
    for left, right in zip(a1, a2):
        interleaved.extend((left, right))
    return interleaved


def build_synthetic_provenance_records(seed: int = DEFAULT_SEED) -> list[ProvenanceRecord]:
    """Создать provenance-записи SYNTHETIC с seed и generation_config."""
    records: list[ProvenanceRecord] = []
    config = {
        "seed": seed,
        "duration_minutes": STREAM_DURATION_MINUTES,
        "frequency_hz": STREAM_FREQUENCY_HZ,
        "start_utc": STREAM_START_UTC,
        "mission_day": STREAM_MISSION_DAY,
        "phase": STREAM_MISSION_PHASE.value,
        "anomaly_windows": [item["anomaly_id"] for item in A1_ANOMALY_WINDOWS],
    }
    for astronaut_id in CREW_IDS:
        for second in range(TICKS_PER_ASTRONAUT):
            timestamp = _tick_timestamp(STREAM_START_UTC, second)
            records.append(
                ProvenanceRecord(
                    provenance_id=f"PROV-SYN-{astronaut_id}-STREAM-{second:04d}",
                    source_type=SourceType.SYNTHETIC,
                    nasa_study_id=None,
                    nasa_dataset_id=None,
                    source_file=None,
                    source_url=None,
                    publication_reference=None,
                    subject_id=None,
                    collection_timepoint=f"STREAM_SECOND_{second}",
                    measurement_timestamp=timestamp,
                    measurement_unit="mixed",
                    original_value="synthetic_stream_tick",
                    normalized_value=None,
                    processing_method="deterministic_stream_generator",
                    quality_status=QualityStatus.VALIDATED,
                    metric_key="stream_tick",
                    fallback_status=FallbackStatus.NONE,
                    derived_from=[],
                    source_verified_utc=None,
                    notes="Synthetic 1 Hz stream tick; values generated, not measured from NASA crew.",
                    source_publication=None,
                    sample_id=None,
                    measurement_name="stream_tick",
                    original_unit="mixed",
                    normalized_unit="mixed",
                    processing_version=SYNTHETIC_GENERATOR_VERSION,
                    generated_at_utc=utc_now_iso(),
                    source_file_sha256=None,
                    license_or_access_terms="Project-generated synthetic data",
                    download_timestamp=None,
                    processing_timestamp=utc_now_iso(),
                    pipeline_version=SYNTHETIC_GENERATOR_VERSION,
                    generator_name=SYNTHETIC_GENERATOR_NAME,
                    generator_version=SYNTHETIC_GENERATOR_VERSION,
                    random_seed=seed,
                    scenario_id=SYNTHETIC_SCENARIO_ID,
                    scenario_configuration=config,
                    generation_timestamp=STREAM_START_UTC,
                )
            )
    for item in A1_ANOMALY_WINDOWS:
        anomaly_id = str(item["anomaly_id"])
        records.append(
            ProvenanceRecord(
                provenance_id=f"PROV-SYN-{anomaly_id}",
                source_type=SourceType.SYNTHETIC,
                nasa_study_id=None,
                nasa_dataset_id=None,
                source_file=None,
                source_url=None,
                publication_reference=None,
                subject_id=None,
                collection_timepoint=anomaly_id,
                measurement_timestamp=None,
                measurement_unit="mixed",
                original_value="synthetic_anomaly_scenario",
                normalized_value=None,
                processing_method="deterministic_scenario_definition",
                quality_status=QualityStatus.VALIDATED,
                metric_key="anomaly_scenario",
                fallback_status=FallbackStatus.NONE,
                derived_from=[],
                source_verified_utc=None,
                notes=f"Synthetic anomaly scenario {anomaly_id}; not a real patient event.",
                measurement_name="anomaly_scenario",
                original_unit="mixed",
                normalized_unit="mixed",
                processing_version=SYNTHETIC_GENERATOR_VERSION,
                generated_at_utc=utc_now_iso(),
                license_or_access_terms="Project-generated synthetic data",
                processing_timestamp=utc_now_iso(),
                pipeline_version=SYNTHETIC_GENERATOR_VERSION,
                generator_name=SYNTHETIC_GENERATOR_NAME,
                generator_version=SYNTHETIC_GENERATOR_VERSION,
                random_seed=seed,
                scenario_id=anomaly_id,
                scenario_configuration=dict(item),
                generation_timestamp=STREAM_START_UTC,
            )
        )
    return records


def _manifest_timestamp(minute: float) -> str:
    """UTC-таймстемп манифеста аномалии по минуте окна."""
    return _tick_timestamp(STREAM_START_UTC, int(round(minute * 60)))


def build_anomaly_manifest() -> list[AnomalyManifestEntry]:
    """Собрать точные метки времени четырёх сценариев A1."""
    entries: list[AnomalyManifestEntry] = []
    evidence = {
        "ANOM-A1-01": ["NASA-STD-3001 [V2 6004]", "OCHMO-TB-004", "ISS Flight Rule B17-5", "OSD-575"],
        "ANOM-A1-02": ["NASA HRP SANS Risk", "OSD-815", "OSD-816", "OSD-817", "OSD-818"],
        "ANOM-A1-03": ["NLSP RST", "SLEEP zsac006", "PMC7515915"],
        "ANOM-A1-04": ["NASA-STD-3001 [V1 4029]", "OSD-977", "OSD-968", "OSD-898", "OSD-989"],
    }
    rationale = {
        "ANOM-A1-01": "Elevated cabin CO2 combined with PVT slowing and HRV suppression models the multi-signal hypercapnic neurocognitive triad.",
        "ANOM-A1-02": "A rise in intraocular pressure with cephalad fluid shift models the direction of SANS findings; it is not a diagnosis.",
        "ANOM-A1-03": "A circadian shift with reduced sleep efficiency and increased PVT lapses models operational fatigue risk.",
        "ANOM-A1-04": "A transient rise in dose rate models an acute solar particle event and requires the hard radiation override.",
    }
    expected = {
        "ANOM-A1-01": TriageStatus.RED,
        "ANOM-A1-02": TriageStatus.RED,
        "ANOM-A1-03": TriageStatus.YELLOW,
        "ANOM-A1-04": TriageStatus.RED,
    }
    for item in A1_ANOMALY_WINDOWS:
        anomaly_id = str(item["anomaly_id"])
        timing = ANOMALY_TIMING[anomaly_id]
        systems = [BodySystemId(value) for value in item["target_systems"]]
        entries.append(
            AnomalyManifestEntry(
                anomaly_id=anomaly_id,
                astronaut_id="A1",
                detector_id=item["detector_id"],
                label=str(item["label"]),
                onset_utc=_manifest_timestamp(timing["onset"]),
                yellow_utc=_manifest_timestamp(timing["yellow"]),
                red_utc=_manifest_timestamp(timing["red"]),
                peak_utc=_manifest_timestamp(timing["peak"]),
                recovery_utc=_manifest_timestamp(timing["recovery"]),
                affected_systems=systems,
                description=str(item["label"]),
                source_type=SourceType.SYNTHETIC,
                provenance_ids=[f"PROV-SYN-{anomaly_id}"],
                scenario_id=anomaly_id,
                anomaly_type=str(item["label"]),
                start_timestamp=_manifest_timestamp(timing["onset"]),
                yellow_timestamp=_manifest_timestamp(timing["yellow"]),
                red_timestamp=_manifest_timestamp(timing["red"]),
                peak_timestamp=_manifest_timestamp(timing["peak"]),
                recovery_timestamp=_manifest_timestamp(timing["recovery"]),
                affected_metrics=[
                    "cabin_ppco2",
                    "pvt_slowest10_rt",
                    "hrv_rmssd",
                    "hr",
                    "iop_mmhg",
                    "radiation_dose_rate",
                ]
                if anomaly_id != "ANOM-A1-04"
                else ["radiation_dose_rate"],
                expected_triage_status=expected[anomaly_id],
                expected_trigger_conditions=[f"{item['detector_id']} crosses the configured demo threshold."],
                scenario_configuration={**item, **{key: _manifest_timestamp(value) for key, value in timing.items()}},
                scientific_rationale=rationale[anomaly_id],
                evidence_references=evidence[anomaly_id],
            )
        )
    return entries


def write_generation_config(destination: Path) -> Path:
    """Сохранить seed, версию генератора и полную конфигурацию сценария."""
    payload = dict(GENERATION_CONFIG)
    payload["anomaly_manifest"] = [entry.model_dump(mode="json") for entry in build_anomaly_manifest()]
    write_json(destination, payload)
    return destination


def write_jsonl_file(ticks: Sequence[StreamTick], output_path: Path) -> int:
    """Записать тики в JSONL и вернуть их количество."""
    return write_jsonl(output_path, [tick.model_dump(mode="json") for tick in ticks])


def main() -> None:
    """CLI: python data_pipeline/stream_generator.py."""
    bundle = _PROJECT_ROOT / "data_bundle"
    (bundle / "synthetic").mkdir(parents=True, exist_ok=True)
    ticks = generate_all_streams()
    count = write_jsonl_file(ticks, bundle / "telemetry_stream_60m.jsonl")
    write_generation_config(bundle / "synthetic" / "generation_config.json")
    print(json.dumps({"ticks": count, "per_astronaut": TICKS_PER_ASTRONAUT}, indent=2))


if __name__ == "__main__":
    main()
