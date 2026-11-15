"""Канонические контракты данных ASTRALIS + IMPACT.

ЭТОТ ФАЙЛ — ИСТОЧНИК ИСТИНЫ ДЛЯ ВСЕХ ЯЗЫКОВ.
Любое изменение здесь ОБЯЗАТЕЛЬНО должно быть синхронно внесено в:
  - frontend/src/types/health.ts
  - shared/contracts.schema.json
  - AGENTS.md (раздел "Data Contracts")

Правила:
  - имена полей и значения enum — строго английские (требование жюри NASA);
  - комментарии в коде — русские;
  - никакой бизнес-логики в этом модуле, только типы и валидационные границы;
  - отсутствующие данные обозначаются null, но никогда не выдумываются.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Перечисления (значения должны совпадать с JSON Schema и health.ts)
# ---------------------------------------------------------------------------


class MissionPhase(str, Enum):
    """Фаза миссии: острая адаптация или длительная экспедиция."""

    PHASE_1_ACUTE_ADAPTATION = "PHASE_1_ACUTE_ADAPTATION"
    PHASE_2_LONG_DURATION = "PHASE_2_LONG_DURATION"


class TriageStatus(str, Enum):
    """Светофорная сортировка.

    INSUFFICIENT_DATA не является клиническим статусом: это явный отказ
    классифицировать неполные данные как GREEN.
    """

    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class BodySystemId(str, Enum):
    """Шесть физиологических систем для цифрового двойника тела."""

    CARDIOVASCULAR = "CARDIOVASCULAR"
    NEURO_OCULAR_SANS = "NEURO_OCULAR_SANS"
    NEURO_BEHAVIORAL = "NEURO_BEHAVIORAL"
    RESPIRATORY_ENV = "RESPIRATORY_ENV"
    ENDOCRINE_METABOLIC = "ENDOCRINE_METABOLIC"
    IMMUNE_MUSCULOSKELETAL = "IMMUNE_MUSCULOSKELETAL"


class CommDelayProfile(str, Enum):
    """Профиль связи Земля—экипаж (односторонняя задержка)."""

    LEO = "LEO"      # 0 секунд
    LUNAR = "LUNAR"  # 30 секунд
    MARS = "MARS"    # 22 минуты (1320 секунд)


class BiologicalSex(str, Enum):
    """Пол для профиля экипажа (влияет на радиационные лимиты)."""

    FEMALE = "FEMALE"
    MALE = "MALE"
    OTHER = "OTHER"


class DetectorId(str, Enum):
    """Идентификаторы семи специализированных детекторов NASA."""

    DET_01 = "DET-01"
    DET_02 = "DET-02"
    DET_03 = "DET-03"
    DET_04 = "DET-04"
    DET_05 = "DET-05"
    DET_06 = "DET-06"
    DET_07 = "DET-07"


class DetectorSeverity(str, Enum):
    """Степень клинической значимости срабатывания детектора."""

    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ForecastMetric(str, Enum):
    """Метрики, для которых IMPACT считает Time-to-Threshold."""

    CABIN_PPCO2 = "cabin_ppco2"
    HR = "hr"
    HRV_RMSSD = "hrv_rmssd"
    SPO2 = "spo2"
    PVT_SLOWEST10_RT = "pvt_slowest10_rt"
    MFI_RISK_SCORE = "mfi_risk_score"
    VO2MAX_ML_KG_MIN = "vo2max_ml_kg_min"
    CUMULATIVE_RADIATION_MSV = "cumulative_radiation_msv"


class SourceType(str, Enum):
    """Классификация происхождения каждого измерения и признака."""

    NASA_REAL = "NASA_REAL"          # опубликованное измерение NASA/OSDR
    NASA_DERIVED = "NASA_DERIVED"    # расчёт поверх реальных данных NASA
    SYNTHETIC = "SYNTHETIC"          # сгенерировано проектом


class QualityStatus(str, Enum):
    """Статус качества измерения или производного признака.

    VALID / VALID_WITH_WARNINGS / UNVERIFIED добавлены для ETL SPEC 1.
    Они не отменяют существующие статусы, а описывают качество источника.
    """

    VALIDATED = "VALIDATED"
    ACCEPTED = "ACCEPTED"
    VALID = "VALID"
    VALID_WITH_WARNINGS = "VALID_WITH_WARNINGS"
    SUSPECT = "SUSPECT"
    MISSING = "MISSING"
    INVALID = "INVALID"
    INVALID_UNIT = "INVALID_UNIT"
    INSUFFICIENT_BASELINE = "INSUFFICIENT_BASELINE"
    UNVERIFIED = "UNVERIFIED"
    NOT_ASSESSED = "NOT_ASSESSED"


class ThresholdSource(str, Enum):
    """Происхождение клинического или модельного порога."""

    NASA_PUBLISHED = "NASA_PUBLISHED"
    RESEARCH_REFERENCE = "RESEARCH_REFERENCE"
    EXPERIMENTAL = "EXPERIMENTAL"
    PROJECT_SIMULATION = "PROJECT_SIMULATION"


class VerificationStatus(str, Enum):
    """Степень проверки записи каталога OSDR."""

    VERIFIED_METADATA = "VERIFIED_METADATA"
    VERIFIED_FILES = "VERIFIED_FILES"
    UNVERIFIED = "UNVERIFIED"
    UNAVAILABLE = "UNAVAILABLE"
    CACHE_FALLBACK = "CACHE_FALLBACK"


class FallbackStatus(str, Enum):
    """Явный статус деградации при отсутствии сети или файлов."""

    NONE = "NONE"
    CACHE_FALLBACK = "CACHE_FALLBACK"
    SYNTHETIC_FALLBACK = "SYNTHETIC_FALLBACK"
    UNAVAILABLE = "UNAVAILABLE"


class DataModality(str, Enum):
    """Тип набора данных; непрерывная телеметрия — лишь один из многих."""

    CONTINUOUS_TELEMETRY = "CONTINUOUS_TELEMETRY"
    DAILY_AGGREGATE = "DAILY_AGGREGATE"
    LAB_PANEL = "LAB_PANEL"
    OMICS = "OMICS"
    MICROBIOME = "MICROBIOME"
    ENVIRONMENTAL = "ENVIRONMENTAL"
    RADIATION = "RADIATION"
    QUESTIONNAIRE = "QUESTIONNAIRE"
    IMAGING = "IMAGING"
    OTHER = "OTHER"


class DatasetCategory(str, Enum):
    """Научная роль набора данных в каталоге ASTRALIS."""

    DIRECT_HUMAN_SPACEFLIGHT = "DIRECT_HUMAN_SPACEFLIGHT"
    HUMAN_SPACEFLIGHT_ANALOG = "HUMAN_SPACEFLIGHT_ANALOG"
    SUPPORTING_BIOLOGICAL_EVIDENCE = "SUPPORTING_BIOLOGICAL_EVIDENCE"
    ENVIRONMENTAL_TELEMETRY = "ENVIRONMENTAL_TELEMETRY"
    RADIATION_EVIDENCE = "RADIATION_EVIDENCE"
    OTHER_RELEVANT_RESEARCH = "OTHER_RELEVANT_RESEARCH"


class IngestionStatus(str, Enum):
    """Статус обработки исследования или набора данных."""

    DISCOVERED = "DISCOVERED"
    CATALOGUED = "CATALOGUED"
    DOWNLOADED = "DOWNLOADED"
    PROCESSED = "PROCESSED"
    REJECTED = "REJECTED"
    UNAVAILABLE = "UNAVAILABLE"


class EvidenceLevel(str, Enum):
    """Уровень доказательности ссылки, без повышения статуса источника."""

    NASA_OFFICIAL_REQUIREMENT = "NASA_OFFICIAL_REQUIREMENT"
    NASA_TECHNICAL_GUIDANCE = "NASA_TECHNICAL_GUIDANCE"
    PEER_REVIEWED_FINDING = "PEER_REVIEWED_FINDING"
    RESEARCH_REFERENCE = "RESEARCH_REFERENCE"
    PROJECT_SIMULATION_ASSUMPTION = "PROJECT_SIMULATION_ASSUMPTION"


# ---------------------------------------------------------------------------
# Базовый класс: запрещаем лишние поля, чтобы Python/TypeScript/JSON Schema
# не расходились незаметно.
# ---------------------------------------------------------------------------


class ContractModel(BaseModel):
    """Базовый класс всех контрактов ASTRALIS."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


# ---------------------------------------------------------------------------
# Происхождение данных (provenance)
# ---------------------------------------------------------------------------


class ProvenanceRecord(ContractModel):
    """Одна запись происхождения для измерения или производного признака.

    Для NASA_REAL поля NASA обязательны, если они опубликованы. Если значение
    отсутствует в источнике, используется null; выдумывать его запрещено.
    Для SYNTHETIC поля NASA и subject_id должны быть null.
    """

    provenance_id: str = Field(..., min_length=1)
    source_type: SourceType
    nasa_study_id: str | None = Field(..., description="OSDR study accession, e.g. OSD-569; null if synthetic")
    nasa_dataset_id: str | None = Field(..., description="OSDR dataset or assay identifier; null if absent")
    source_file: str | None = Field(..., description="Original file name or object key; null if none")
    source_url: str | None = Field(..., description="Public HTTP(S) source URL; null if none")
    publication_reference: str | None = Field(..., description="Citation or DOI; null if not published")
    subject_id: str | None = Field(..., description="De-identified subject ID from the source; null if absent")
    collection_timepoint: str | None = Field(..., description="Source collection label, e.g. L-92 or R+1; null if absent")
    measurement_timestamp: str | None = Field(..., description="ISO-8601 UTC timestamp; null if the source has none")
    measurement_unit: str | None = Field(..., description="Original or UCUM unit; null if not reported")
    original_value: str | None = Field(..., description="Unmodified source value serialized as text; null if missing")
    normalized_value: float | None = Field(..., description="Processed numeric value; null if not normalized")
    processing_method: str = Field(..., min_length=1, description="Method used, e.g. identity, unit_conversion, synthetic_gaussian")
    quality_status: QualityStatus
    metric_key: str | None = Field(..., description="Target field name, e.g. hr or hrv_rmssd; null if not mapped")
    fallback_status: FallbackStatus
    derived_from: list[str] = Field(..., description="Parent provenance IDs for derived features")
    source_verified_utc: str | None = Field(..., description="When the source record was last verified; null if unknown")
    notes: str | None = Field(..., description="English free-text note; null if none")

    # Расширение SPEC 1: сохраняем исходные единицы и полный путь обработки.
    source_publication: str | None = Field(default=None, description="Publication title, DOI, or citation; null if absent")
    sample_id: str | None = Field(default=None, description="Source sample identifier; null if absent")
    measurement_name: str | None = Field(default=None, description="Original measurement/analyte name; null if absent")
    original_unit: str | None = Field(default=None, description="Unit exactly as reported by the source")
    normalized_unit: str | None = Field(default=None, description="UCUM or documented normalized unit")
    processing_version: str | None = Field(default=None, description="Version of the normalization or feature routine")
    generated_at_utc: str | None = Field(default=None, description="When this provenance record was generated")
    source_file_sha256: str | None = Field(default=None, description="SHA-256 of the source file, if available")
    license_or_access_terms: str | None = Field(default=None, description="License or public-access terms; null if unknown")
    download_timestamp: str | None = Field(default=None, description="ISO-8601 download time; null if not downloaded")
    processing_timestamp: str | None = Field(default=None, description="ISO-8601 processing time; null if not processed")
    pipeline_version: str | None = Field(default=None, description="Data pipeline version that produced the record")
    generator_name: str | None = Field(default=None, description="Synthetic generator name; null for real data")
    generator_version: str | None = Field(default=None, description="Synthetic generator version; null for real data")
    random_seed: int | None = Field(default=None, description="Deterministic seed; null for real data")
    scenario_id: str | None = Field(default=None, description="Synthetic scenario identifier; null for real data")
    scenario_configuration: dict[str, object] | None = Field(default=None, description="Synthetic scenario parameters; null for real data")
    generation_timestamp: str | None = Field(default=None, description="ISO-8601 synthetic generation time; null for real data")


class ProvenanceManifest(ContractModel):
    """Манифест происхождения, поставляемый вместе с офлайн-бандлом."""

    manifest_id: str = Field(..., min_length=1)
    bundle_id: str = Field(..., min_length=1)
    manifest_version: str = Field(..., min_length=1)
    generated_at_utc: str
    fallback_status: FallbackStatus
    records: list[ProvenanceRecord]


# ---------------------------------------------------------------------------
# Потоковые и суточные данные
# ---------------------------------------------------------------------------


class StreamTick(ContractModel):
    """Один 1-герцовый тик телеметрии (60 минут = 3600 тиков на астронавта)."""

    timestamp: str = Field(..., description="ISO-8601 UTC timestamp, e.g. 2026-05-01T12:00:00Z")
    mission_day: Annotated[int, Field(ge=1, le=3650, description="1-based mission day")]
    mission_phase: MissionPhase
    astronaut_id: str = Field(..., min_length=1, description="Crew member identifier, e.g. A1")
    source_type: SourceType = Field(
        ...,
        description="Direct label for the measurement source; SYNTHETIC demo ticks are never NASA_REAL",
    )

    # Физиология
    hr: Annotated[float, Field(ge=20.0, le=250.0, description="Heart rate, bpm")]
    hrv_rmssd: Annotated[float, Field(ge=0.0, le=300.0, description="HRV RMSSD, ms")]
    spo2: Annotated[float, Field(ge=50.0, le=100.0, description="Peripheral oxygen saturation, %")]
    systolic_bp: Annotated[int, Field(ge=50, le=260, description="Systolic blood pressure, mmHg")]
    diastolic_bp: Annotated[int, Field(ge=20, le=160, description="Diastolic blood pressure, mmHg")]
    temp_c: Annotated[float, Field(ge=30.0, le=45.0, description="Core/skin temperature, Celsius")]
    resp_rate: Annotated[float, Field(ge=4.0, le=60.0, description="Respiratory rate, breaths/min")]
    iop_mmhg: Annotated[float, Field(ge=0.0, le=60.0, description="Intraocular pressure, mmHg")]

    # Среда кабины и радиация
    cabin_ppco2: Annotated[float, Field(ge=0.0, le=20.0, description="Cabin partial pressure of CO2, mmHg")]
    radiation_dose_rate: Annotated[float, Field(ge=0.0, le=1000.0, description="Instantaneous dose rate, mSv/h")]

    # Нейрокогнитивный тест PVT-B
    pvt_slowest10_rt: Annotated[float, Field(ge=100.0, le=1000.0, description="PVT-B slowest 10% reaction time, ms")]

    # Ссылки на записи происхождения для измерений в этом тике.
    provenance_ids: list[str] = Field(..., min_length=1)


class DailyTelemetryLog(ContractModel):
    """Суточная агрегированная телеметрия для 180-дневной серии.

    Расширяет физиологический блок StreamTick суточными показателями сна,
    настроения, флюидного сдвига, радиации и физической формы.
    """

    timestamp: str = Field(..., description="ISO-8601 UTC timestamp for the daily record")
    mission_day: Annotated[int, Field(ge=1, le=3650)]
    mission_phase: MissionPhase
    astronaut_id: str = Field(..., min_length=1)

    # Прямая метка источника для суточного агрегата.
    source_type: SourceType

    # Физиология (суточные средние/минимумы)
    hr: Annotated[float, Field(ge=20.0, le=250.0)]
    hrv_rmssd: Annotated[float, Field(ge=0.0, le=300.0)]
    spo2: Annotated[float, Field(ge=50.0, le=100.0)]
    systolic_bp: Annotated[int, Field(ge=50, le=260)]
    diastolic_bp: Annotated[int, Field(ge=20, le=160)]
    temp_c: Annotated[float, Field(ge=30.0, le=45.0)]
    resp_rate: Annotated[float, Field(ge=4.0, le=60.0)]
    cabin_ppco2: Annotated[float, Field(ge=0.0, le=20.0)]
    radiation_dose_rate: Annotated[float, Field(ge=0.0, le=1000.0)]
    iop_mmhg: Annotated[float, Field(ge=0.0, le=60.0)]
    pvt_slowest10_rt: Annotated[float, Field(ge=100.0, le=1000.0)]

    # Сон и циркадный ритм
    sleep_duration_h: Annotated[float, Field(ge=0.0, le=24.0, description="Total sleep time, hours")]
    sleep_efficiency_pct: Annotated[float, Field(ge=0.0, le=100.0, description="Sleep efficiency, %")]
    sleep_shift_active: bool = Field(..., description="Slam-shift / circadian misalignment flag")

    # Психофизиология и PVT-B
    mood_stress_vas: Annotated[float, Field(ge=0.0, le=100.0, description="Stress visual analogue scale, 0-100")]
    pvt_mean_rt_ms: Annotated[float, Field(ge=100.0, le=2000.0, description="PVT-B mean reaction time, ms")]
    pvt_lapses_count: Annotated[int, Field(ge=0, le=100, description="Number of PVT-B lapses (>500 ms)")]

    # SANS и флюидный сдвиг
    fluid_shift_index: Annotated[float, Field(ge=0.0, le=3.0, description="Cephalad fluid shift index, 0-3")]
    sans_visual_symptoms: bool = Field(..., description="Visual symptoms consistent with SANS")

    # Радиация
    daily_radiation_msv: Annotated[float, Field(ge=0.0, le=1000.0, description="Daily dose, mSv")]
    cumulative_radiation_msv: Annotated[float, Field(ge=0.0, le=5000.0, description="Cumulative mission dose, mSv")]

    # Контрмеры и физическая форма
    ared_exercise_completed: bool = Field(..., description="ARED resistance exercise completed")
    vo2max_ml_kg_min: Annotated[float, Field(ge=0.0, le=100.0, description="VO2max, mL/kg/min")]
    respiratory_exchange_ratio: Annotated[float, Field(ge=0.6, le=1.4, description="Metabolic RQ (DET-07 input)")]

    provenance_ids: list[str] = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Каталог NASA OSDR
# ---------------------------------------------------------------------------


class NasaStudyRecord(ContractModel):
    """Проверяемая запись исследования NASA OSDR."""

    study_id: str = Field(..., min_length=1, description="OSDR accession, e.g. OSD-569")
    title: str | None = Field(..., description="Study title from OSDR; null if metadata unavailable")
    description: str | None = Field(..., description="Study description from OSDR; null if unavailable")
    mission: str | None = Field(..., description="Mission or platform, e.g. SpaceX Inspiration4; null if absent")
    verification_status: VerificationStatus
    metadata_url: str | None
    file_index_url: str | None
    s3_prefix: str | None
    dataset_ids: list[str]
    continuous_telemetry_available: bool | None = Field(
        ...,
        description="True/False only after file inspection; null when not yet verified",
    )
    last_verified_utc: str | None
    notes: str | None

    # Каталожные поля SPEC 1. None означает "не опубликовано в источнике".
    study_category: DatasetCategory | None = None
    organism: str | None = None
    subject_count: Annotated[int, Field(ge=0)] | None = None
    sample_count: Annotated[int, Field(ge=0)] | None = None
    assay_types: list[str] = Field(default_factory=list)
    available_measurements: list[str] = Field(default_factory=list)
    collection_timepoints: list[str] = Field(default_factory=list)
    file_count: Annotated[int, Field(ge=0)] | None = None
    downloaded_file_count: Annotated[int, Field(ge=0)] | None = None
    public_access_status: str | None = None
    relevance_score: Annotated[float, Field(ge=0.0, le=100.0)] | None = None
    scientific_relevance: str | None = None
    limitations: list[str] = Field(default_factory=list)
    source_url: str | None = None
    publication_references: list[str] = Field(default_factory=list)
    ingestion_status: IngestionStatus | None = None
    rejection_reason: str | None = None


class NasaDatasetRecord(ContractModel):
    """Проверяемая запись набора данных внутри исследования OSDR."""

    dataset_id: str = Field(..., min_length=1)
    study_id: str = Field(..., min_length=1)
    title: str | None
    modality: DataModality
    measurement_types: list[str]
    measurement_units: list[str]
    subject_count: Annotated[int, Field(ge=0)] | None
    timepoint_count: Annotated[int, Field(ge=0)] | None
    file_count: Annotated[int, Field(ge=0)] | None
    access_level: str | None
    verification_status: VerificationStatus
    source_url: str | None
    last_verified_utc: str | None
    continuous_telemetry: bool | None
    notes: str | None

    # Расширение каталога SPEC 1.
    category: DatasetCategory | None = None
    assay_types: list[str] = Field(default_factory=list)
    collection_timepoints: list[str] = Field(default_factory=list)
    public_files: Annotated[int, Field(ge=0)] | None = None
    restricted_files: Annotated[int, Field(ge=0)] | None = None
    downloaded_files: Annotated[int, Field(ge=0)] | None = None
    relevance_score: Annotated[float, Field(ge=0.0, le=100.0)] | None = None
    scientific_relevance: str | None = None
    limitations: list[str] = Field(default_factory=list)
    publication_references: list[str] = Field(default_factory=list)
    ingestion_status: IngestionStatus | None = None
    source_file_names: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Фазовые базовые линии (Phase 1 vs Phase 2)
# ---------------------------------------------------------------------------


class PhaseBaseline(ContractModel):
    """Базовая линия физиологии для конкретной фазы миссии.

    Фаза 1: дни 1-14. Фаза 2: дни 15-180+.
    """

    baseline_id: str = Field(..., min_length=1)
    astronaut_id: str = Field(..., min_length=1)
    mission_phase: MissionPhase
    window_start_day: Annotated[int, Field(ge=1, le=3650)]
    window_end_day: Annotated[int, Field(ge=1, le=3650)]
    sample_days: Annotated[int, Field(ge=1, le=3650)]

    mean_hr: Annotated[float, Field(ge=20.0, le=250.0)]
    sd_hr: Annotated[float, Field(ge=0.0, le=100.0)]
    mean_hrv_rmssd: Annotated[float, Field(ge=0.0, le=300.0)]
    sd_hrv_rmssd: Annotated[float, Field(ge=0.0, le=100.0)]
    mean_pvt_slowest10_rt: Annotated[float, Field(ge=100.0, le=1000.0)]
    sd_pvt_slowest10_rt: Annotated[float, Field(ge=0.0, le=300.0)]
    mean_sleep_efficiency_pct: Annotated[float, Field(ge=0.0, le=100.0)]
    mean_cabin_ppco2: Annotated[float, Field(ge=0.0, le=20.0)]
    generated_at_utc: str = Field(..., description="ISO-8601 UTC timestamp of baseline derivation")

    # Валидация базовой линии и происхождение опорных значений.
    baseline_source_ids: list[str] = Field(..., description="Provenance IDs used to derive this baseline")
    baseline_population: str = Field(..., min_length=1, description="English description of the reference population")
    baseline_sample_size: Annotated[int, Field(ge=0)]
    data_completeness_pct: Annotated[float, Field(ge=0.0, le=100.0)]
    missing_metrics: list[str]
    confidence_score: Annotated[float, Field(ge=0.0, le=1.0)]
    model_version: str = Field(..., min_length=1)
    threshold_source: ThresholdSource
    provenance_ids: list[str] = Field(..., min_length=1)

    # Расширение SPEC 1: per-metric statistics сохраняют null там, где
    # опубликованных данных недостаточно, вместо выдуманных значений.
    metric_statistics: list[dict[str, object]] = Field(default_factory=list)
    evidence_references: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Сортировка, детекторы, прогноз, SBAR
# ---------------------------------------------------------------------------


class TriageAssessment(ContractModel):
    """Результат фазо-зависимой сортировки (MFI + жёсткие RED-оверрайды)."""

    timestamp: str = Field(..., description="ISO-8601 UTC timestamp of assessment")
    astronaut_id: str = Field(..., min_length=1)
    mission_phase: MissionPhase
    mfi_risk_score: Annotated[float, Field(ge=0.0, le=100.0, description="Multi-Signal Fusion Index, 0-100")]
    triage_status: TriageStatus
    active_fusion_patterns: list[str] = Field(
        ...,
        description="Human-readable fusion patterns, e.g. HYPERCAPNIC_NEUROCOGNITIVE_TRIAD",
    )
    affected_systems: list[BodySystemId]
    recommended_protocol_ids: list[str]
    requires_eva_hold: bool = Field(..., description="EVA operations must be paused")

    # Качество данных и доверие к модели.
    data_completeness_pct: Annotated[float, Field(ge=0.0, le=100.0)]
    missing_metrics: list[str]
    confidence_score: Annotated[float, Field(ge=0.0, le=1.0)]
    model_version: str = Field(..., min_length=1)
    data_quality_status: QualityStatus
    requires_human_review: bool = Field(
        ...,
        description="True for INSUFFICIENT_DATA, low confidence, or any RED override",
    )
    provenance_ids: list[str] = Field(..., min_length=1)


class DetectorResult(ContractModel):
    """Срабатывание одного из семи детекторов NASA."""

    detector_id: DetectorId
    name: str = Field(..., min_length=1, description="Short English detector name")
    triggered: bool
    severity: DetectorSeverity
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    clinical_summary: str = Field(..., min_length=1, description="English plain-language summary")
    nasa_references: list[str] = Field(..., description="NASA report IDs and document codes")
    recommended_action: str = Field(..., min_length=1, description="English countermeasure recommendation")

    # Валидация порога и качества входных данных.
    threshold_source: ThresholdSource
    data_completeness_pct: Annotated[float, Field(ge=0.0, le=100.0)]
    model_version: str = Field(..., min_length=1)
    provenance_ids: list[str] = Field(..., min_length=1)


class ShortTermHorizonPrediction(ContractModel):
    """Прогноз потоковых метрик на горизонте +5 / +15 / +30 минут."""

    horizon_minutes: Literal[5, 15, 30]
    cabin_ppco2: Annotated[float, Field(ge=0.0, le=20.0)]
    hr: Annotated[float, Field(ge=20.0, le=250.0)]
    hrv_rmssd: Annotated[float, Field(ge=0.0, le=300.0)]
    spo2: Annotated[float, Field(ge=50.0, le=100.0)]
    pvt_slowest10_rt: Annotated[float, Field(ge=100.0, le=1000.0)]
    mfi_risk_score: Annotated[float, Field(ge=0.0, le=100.0)]

    # Интервалы неопределённости по именам метрик и доверие к прогнозу.
    prediction_lower_bound: dict[str, float]
    prediction_upper_bound: dict[str, float]
    confidence_score: Annotated[float, Field(ge=0.0, le=1.0)]
    provenance_ids: list[str] = Field(..., min_length=1)


class TimeToThresholdAlert(ContractModel):
    """Обратный отсчёт до пересечения клинического порога."""

    metric: ForecastMetric
    current_value: float
    target_threshold: float
    target_status: TriageStatus = Field(
        ...,
        description="GREEN, YELLOW, or RED; INSUFFICIENT_DATA is not a valid target status",
    )
    seconds_remaining: Annotated[
        int,
        Field(
            ge=-1,
            description="Seconds until threshold; 0 if already crossed; -1 if not projected",
        ),
    ]
    explanation: str = Field(..., min_length=1, description="English explanation of the alert")

    # Происхождение порога и неопределённость прогноза.
    threshold_source: ThresholdSource
    threshold_already_crossed: bool
    velocity_per_second: float
    confidence_score: Annotated[float, Field(ge=0.0, le=1.0)]
    prediction_lower_bound: float = Field(..., description="Lower bound for seconds_remaining")
    prediction_upper_bound: float = Field(..., description="Upper bound for seconds_remaining")
    provenance_ids: list[str] = Field(..., min_length=1)


class LongTermTrajectoryPoint(ContractModel):
    """Долгосрочная траектория миссии (+7 / +30 / +90 дней)."""

    horizon_days: Literal[7, 30, 90]
    vo2max_ml_kg_min: Annotated[float, Field(ge=0.0, le=100.0)]
    cumulative_radiation_msv: Annotated[float, Field(ge=0.0, le=5000.0)]
    radiation_budget_remaining_pct: Annotated[float, Field(ge=0.0, le=100.0)]
    sans_risk_probability: Annotated[float, Field(ge=0.0, le=1.0)]

    prediction_lower_bound: dict[str, float]
    prediction_upper_bound: dict[str, float]
    confidence_score: Annotated[float, Field(ge=0.0, le=1.0)]
    provenance_ids: list[str] = Field(..., min_length=1)


class ImpactForecast(ContractModel):
    """Полный прогноз IMPACT: поток, пороги и долгосрочная миссия."""

    astronaut_id: str = Field(..., min_length=1)
    generated_at_utc: str = Field(..., description="ISO-8601 UTC timestamp of forecast generation")
    short_term_horizons: list[ShortTermHorizonPrediction]
    time_to_threshold_alerts: list[TimeToThresholdAlert]
    long_term_trajectory: list[LongTermTrajectoryPoint]

    model_version: str = Field(..., min_length=1)
    confidence_score: Annotated[float, Field(ge=0.0, le=1.0)]
    is_low_confidence: bool = Field(
        ...,
        description="True when confidence_score is below the documented threshold",
    )
    data_completeness_pct: Annotated[float, Field(ge=0.0, le=100.0)]
    missing_metrics: list[str]
    provenance_ids: list[str] = Field(..., min_length=1)


class SbarMedicalReport(ContractModel):
    """Клинический SBAR-пакет для отложенной передачи дежурному врачу."""

    report_id: str = Field(..., min_length=1)
    generated_at_utc: str = Field(..., description="ISO-8601 UTC timestamp")
    comm_delay_profile: CommDelayProfile
    round_trip_latency_sec: Annotated[int, Field(ge=0, le=7200)]
    situation: str = Field(..., min_length=1)
    background: str = Field(..., min_length=1)
    assessment: str = Field(..., min_length=1)
    recommendation: str = Field(..., min_length=1)
    attached_telemetry_snapshot: StreamTick
    nasa_protocol_citations: list[str]
    model_version: str = Field(..., min_length=1)
    provenance_ids: list[str] = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Вспомогательные сущности офлайн-бандла (профили, аномалии, карточки, протоколы)
# ---------------------------------------------------------------------------


class AstronautProfile(ContractModel):
    """Профиль члена экипажа для демонстрации."""

    astronaut_id: str = Field(..., min_length=1)
    display_name: str = Field(..., min_length=1)
    mission_role: str = Field(..., min_length=1, description="e.g. Commander, Medical Officer")
    age: Annotated[int, Field(ge=18, le=80)]
    sex: BiologicalSex
    height_cm: Annotated[float, Field(ge=120.0, le=230.0)]
    mass_kg: Annotated[float, Field(ge=35.0, le=200.0)]
    mission_name: str = Field(..., min_length=1)
    mission_duration_days: Annotated[int, Field(ge=1, le=3650)]
    is_control: bool = Field(..., description="A2 healthy control flag")
    source_type: SourceType = Field(
        ...,
        description="SYNTHETIC demo crew must never be presented as real NASA astronauts",
    )
    provenance_ids: list[str] = Field(..., min_length=1)


class AnomalyManifestEntry(ContractModel):
    """Точные метки времени заложенных аномалий для демо и тестов."""

    anomaly_id: str = Field(..., min_length=1)
    astronaut_id: str = Field(..., min_length=1)
    detector_id: DetectorId
    label: str = Field(..., min_length=1, description="English anomaly label")
    onset_utc: str
    yellow_utc: str | None
    red_utc: str | None
    peak_utc: str | None
    recovery_utc: str | None
    affected_systems: list[BodySystemId]
    description: str = Field(..., min_length=1, description="English description of the seeded anomaly")
    source_type: SourceType
    provenance_ids: list[str] = Field(..., min_length=1)

    # Расширение SPEC 1: сценарий и ожидаемая реакция детекторов.
    scenario_id: str | None = None
    anomaly_type: str | None = None
    start_timestamp: str | None = None
    yellow_timestamp: str | None = None
    red_timestamp: str | None = None
    peak_timestamp: str | None = None
    recovery_timestamp: str | None = None
    affected_metrics: list[str] = Field(default_factory=list)
    expected_triage_status: TriageStatus | None = None
    expected_trigger_conditions: list[str] = Field(default_factory=list)
    scenario_configuration: dict[str, object] | None = None
    scientific_rationale: str | None = None
    evidence_references: list[str] = Field(default_factory=list)


class NasaEvidenceCard(ContractModel):
    """Карточка "Why This Happens in Space" с точной ссылкой на отчёт NASA."""

    card_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    body_system: BodySystemId
    phenomenon: str = Field(..., min_length=1, description="What the crew/operator observes")
    why_it_happens: str = Field(..., min_length=1, description="Spaceflight physiology explanation")
    countermeasure: str = Field(..., min_length=1)
    nasa_report_id: str = Field(..., min_length=1)
    source_url: str = Field(..., min_length=1)
    tags: list[str]
    provenance_ids: list[str] = Field(..., min_length=1)

    # Расширение SPEC 1: связь с детектором и прозрачная доказательная база.
    detector_id: str | None = None
    clinical_question: str | None = None
    scientific_mechanism: str | None = None
    observed_findings: str | None = None
    relevance_to_astronaut_health: str | None = None
    applicable_metrics: list[str] = Field(default_factory=list)
    threshold_evidence: str | None = None
    nasa_document_ids: list[str] = Field(default_factory=list)
    study_ids: list[str] = Field(default_factory=list)
    publication_title: str | None = None
    publication_doi: str | None = None
    publication_url: str | None = None
    official_nasa_url: str | None = None
    evidence_level: EvidenceLevel | None = None
    limitations: list[str] = Field(default_factory=list)
    data_type: str | None = None
    last_verified_at: str | None = None


class TriageProtocol(ContractModel):
    """Пошаговый протокол стабилизации для немадицинского экипажа."""

    protocol_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    severity: DetectorSeverity
    trigger_condition: str = Field(..., min_length=1, description="English trigger description")
    steps: list[str] = Field(..., min_length=1, description="Ordered plain-language steps")
    escalate_if: list[str]
    citation: str = Field(..., min_length=1, description="NASA source identifier")
    provenance_ids: list[str] = Field(..., min_length=1)

    # Расширение SPEC 1: structured protocol fields for offline triage UI.
    applicable_detector_ids: list[str] = Field(default_factory=list)
    applicable_body_systems: list[str] = Field(default_factory=list)
    trigger_conditions: list[str] = Field(default_factory=list)
    triage_status: TriageStatus | None = None
    immediate_actions: list[str] = Field(default_factory=list)
    monitoring_instructions: list[str] = Field(default_factory=list)
    escalation_conditions: list[str] = Field(default_factory=list)
    communication_requirements: list[str] = Field(default_factory=list)
    contraindications_if_known: list[str] = Field(default_factory=list)
    source_references: list[str] = Field(default_factory=list)
    evidence_level: EvidenceLevel | None = None
    limitations: list[str] = Field(default_factory=list)


class MedicalGuideline(ContractModel):
    """Структурированная запись клинического компендиума NASA."""

    guideline_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1, description="e.g. Environmental, Cardiovascular, SANS")
    summary: str = Field(..., min_length=1)
    key_values: dict[str, float] = Field(
        ...,
        description="Machine-readable thresholds, e.g. cabin_ppco2_red: 7.6",
    )
    threshold_source: ThresholdSource
    citation: str = Field(..., min_length=1)
    source_url: str = Field(..., min_length=1)
    provenance_ids: list[str] = Field(..., min_length=1)

    # Расширение SPEC 1: bibliographic traceability and applicability.
    organization: str | None = None
    document_id: str | None = None
    document_version: str | None = None
    publication_date: str | None = None
    applicable_body_systems: list[str] = Field(default_factory=list)
    relevant_metric: str | None = None
    threshold_if_explicitly_published: dict[str, float] | None = None
    recommendation: str | None = None
    scientific_rationale: str | None = None
    evidence_level: EvidenceLevel | None = None
    applicability: str | None = None
    limitations: list[str] = Field(default_factory=list)


class LaboratoryResult(ContractModel):
    """Одно лабораторное измерение с исходными и нормализованными единицами."""

    result_id: str = Field(..., min_length=1)
    test_name: str = Field(..., min_length=1, description="Original analyte/test name")
    value: float | None = Field(..., description="Normalized numeric value; null if missing")
    original_value: str | None = Field(..., description="Unmodified source value")
    unit: str | None = Field(..., description="Original reported unit")
    normalized_unit: str | None = Field(..., description="Documented normalized unit; null if ambiguous")
    sample_type: str | None = None
    collection_timepoint: str | None = None
    subject_id: str | None = None
    source_study_id: str | None = None
    source_file: str | None = None
    reference_interval_low: float | None = None
    reference_interval_high: float | None = None
    assay_method: str | None = None
    quality_status: QualityStatus
    provenance_id: str = Field(..., min_length=1)


class LaboratoryPanel(ContractModel):
    """Периодическая лабораторная панель (CBC, CMP, cytokines)."""

    panel_id: str = Field(..., min_length=1)
    astronaut_id: str = Field(..., min_length=1)
    collected_at_utc: str
    mission_day: Annotated[int, Field(ge=1, le=3650)]
    panel_type: str = Field(..., min_length=1, description="CBC | CMP | CYTOKINES")
    source_type: SourceType = Field(
        ...,
        description="NASA_REAL for published panels, SYNTHETIC for demo panels",
    )
    results: dict[str, float] = Field(..., description="Analyte -> normalized value in SI units")
    interpretation: str = Field(..., min_length=1, description="English clinical interpretation")
    data_completeness_pct: Annotated[float, Field(ge=0.0, le=100.0)]
    provenance_ids: list[str] = Field(..., min_length=1)

    # Расширение SPEC 1: individual results and real-source traceability.
    subject_id: str | None = None
    source_study_ids: list[str] = Field(default_factory=list)
    sample_type: str | None = None
    quality_status: QualityStatus | None = None
    results_detail: list[LaboratoryResult] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Экспорт: явный список контрактов для тестов паритета и JSON Schema
# ---------------------------------------------------------------------------

CANONICAL_CONTRACTS: tuple[type[ContractModel], ...] = (
    ProvenanceRecord,
    ProvenanceManifest,
    StreamTick,
    DailyTelemetryLog,
    NasaStudyRecord,
    NasaDatasetRecord,
    PhaseBaseline,
    TriageAssessment,
    DetectorResult,
    ImpactForecast,
    SbarMedicalReport,
    AstronautProfile,
    AnomalyManifestEntry,
    NasaEvidenceCard,
    TriageProtocol,
    MedicalGuideline,
    LaboratoryPanel,
)
