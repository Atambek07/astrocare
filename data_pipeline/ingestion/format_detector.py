"""Определение формата файлов и модальности данных.

OSDR содержит CSV/TSV, JSON, XLSX, архивы, FASTQ/матрицы и PDF. Код не
предполагает, что файл является таблицей витальных показателей.
"""

from __future__ import annotations

import csv
import io
import sys
import zipfile
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from shared.contracts import DataModality  # noqa: E402
from data_pipeline.common import sha256_file  # noqa: E402

SUPPORTED_FORMATS: tuple[str, ...] = (
    "csv",
    "tsv",
    "json",
    "jsonl",
    "xlsx",
    "parquet",
    "hdf5",
    "fastq",
    "mtx",
    "zip",
    "pdf",
    "unknown",
)
TABULAR_FORMATS: tuple[str, ...] = ("csv", "tsv", "xlsx", "parquet")
OMICS_FORMATS: tuple[str, ...] = ("fastq", "mtx", "hdf5", "csv", "tsv")
MAGIC_BYTES: dict[str, bytes] = {
    "zip": b"PK\x03\x04",
    "hdf5": b"\x89HDF\r\n\x1a\n",
    "pdf": b"%PDF-",
}
UNIT_TOKENS: tuple[str, ...] = (
    "bpm",
    "ms",
    "mmhg",
    "mm[hg]",
    "mg/dl",
    "mmol/l",
    "g/dl",
    "pg/ml",
    "ng/ml",
    "cells/ul",
    "10^3/ul",
    "10^6/ul",
    "percent",
    "%",
    "mSv/h",
    "ml/kg/min",
)


def detect_file_format(path: Path) -> str:
    """Определить формат по расширению и magic bytes; вернуть unknown при сомнении."""
    suffix = path.suffix.lower().lstrip(".")
    suffix_map = {
        "csv": "csv",
        "tsv": "tsv",
        "txt": "tsv" if path.name.lower().endswith((".tsv",)) else "unknown",
        "json": "json",
        "jsonl": "jsonl",
        "xlsx": "xlsx",
        "xls": "xlsx",
        "parquet": "parquet",
        "h5": "hdf5",
        "hdf5": "hdf5",
        "fastq": "fastq",
        "fq": "fastq",
        "mtx": "mtx",
        "zip": "zip",
        "pdf": "pdf",
    }
    if suffix in suffix_map:
        return suffix_map[suffix]
    try:
        head = path.open("rb").read(12)
    except OSError:
        return "unknown"
    for fmt, magic in MAGIC_BYTES.items():
        if head.startswith(magic):
            return fmt
    if head.lstrip().startswith((b"{", b"[")):
        return "json"
    return "unknown"


def detect_modality(file_name: str, metadata: dict[str, object] | None = None) -> DataModality:
    """Определить модальность по имени файла и метаданным, без догадок о содержимом."""
    text = file_name.lower()
    category = str((metadata or {}).get("category", "")).lower()
    subcategory = str((metadata or {}).get("subcategory", "")).lower()
    joined = f"{text} {category} {subcategory}"
    if any(token in joined for token in ("metagenomic", "microbiome", "metatranscriptomic", "taxonomy")):
        return DataModality.MICROBIOME
    if any(token in joined for token in ("radiation", "dosimetry", "dose")):
        return DataModality.RADIATION
    if any(token in joined for token in ("cabin", "environment", "co2", "temperature", "humidity")):
        return DataModality.ENVIRONMENTAL
    if any(token in joined for token in ("questionnaire", "survey", "mood", "sleep log")):
        return DataModality.QUESTIONNAIRE
    if any(token in joined for token in ("mri", "imaging", "photography", "oct", "ultrasound")):
        return DataModality.IMAGING
    if any(token in joined for token in ("rna-seq", "rnaseq", "wgs", "proteomic", "metabolomic", "sequencing")):
        return DataModality.OMICS
    if any(
        token in joined
        for token in (
            "cbc",
            "complete blood",
            "comprehensive metabolic",
            "cytokine",
            "multiplex",
            "immune panel",
            "urine",
            "laboratory",
        )
    ):
        return DataModality.LAB_PANEL
    if any(token in joined for token in ("daily", "telemetry", "vital", "heart rate", "spo2")):
        return DataModality.DAILY_AGGREGATE
    return DataModality.OTHER


def extract_units_hint(path: Path) -> list[str]:
    """Извлечь подсказки о единицах из заголовков/метаданных, ничего не выдумывая."""
    fmt = detect_file_format(path)
    if fmt not in {"csv", "tsv"}:
        return []
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")[:200_000]
    except OSError:
        return []
    delimiter = "\t" if fmt == "tsv" else ","
    header = text.splitlines()[0] if text.splitlines() else ""
    cells = next(csv.reader(io.StringIO(header), delimiter=delimiter), [])
    hints: list[str] = []
    for cell in cells:
        lowered = cell.strip().lower()
        if any(token in lowered for token in UNIT_TOKENS):
            hints.append(cell.strip())
    return sorted(set(hints))


def is_text_tabular(path: Path) -> bool:
    """Проверить, является ли файл текстовой таблицей с разделителем."""
    if detect_file_format(path) not in {"csv", "tsv"}:
        return False
    try:
        sample = path.read_text(encoding="utf-8-sig", errors="replace")[:4096]
    except OSError:
        return False
    first = sample.splitlines()[0] if sample.splitlines() else ""
    return ("\t" in first) or ("," in first)


def describe_file(path: Path) -> dict[str, object]:
    """Вернуть формат, размер, checksum и предполагаемую модальность."""
    fmt = detect_file_format(path)
    return {
        "file_name": path.name,
        "format": fmt,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "modality": detect_modality(path.name).value,
        "units_hint": extract_units_hint(path),
    }


def inspect_archive(path: Path, *, max_entries: int = 200) -> list[dict[str, object]]:
    """Рекурсивно перечислить первые записи ZIP-архива без распаковки."""
    if not zipfile.is_zipfile(path):
        return []
    entries: list[dict[str, object]] = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist()[:max_entries]:
            entries.append(
                {
                    "name": info.filename,
                    "size_bytes": info.file_size,
                    "compressed_size_bytes": info.compress_size,
                    "is_directory": info.is_dir(),
                    "format": detect_file_format(Path(info.filename)),
                }
            )
    return entries
