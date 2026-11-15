"""Общие утилиты SPEC 1: пути, JSON, checksums и детерминированное время.

Модуль не содержит клинической логики. Все текстовые поля, попадающие в
артефакты, формируются на английском; комментарии и docstrings — на русском.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
BUNDLE_DIR: Path = PROJECT_ROOT / "data_bundle"
PIPELINE_CACHE_DIR: Path = PROJECT_ROOT / "data_pipeline" / "cache"
PIPELINE_VERSION: str = "astralis-data-1.0.0"
BUNDLE_ID: str = "astralis-offline-2026-11-14"
BUILD_TIMESTAMP_UTC: str = "2026-11-14T00:00:00Z"


def utc_now_iso() -> str:
    """Вернуть текущее UTC-время в ISO-8601 с суффиксом Z."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_dir(path: Path) -> Path:
    """Создать каталог, если его нет, и вернуть путь."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Посчитать SHA-256 файла потоково, не загружая его целиком в память."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    """Посчитать SHA-256 строки в UTF-8."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def atomic_write_bytes(destination: Path, payload: bytes) -> Path:
    """Записать файл атомарно через временный файл в том же каталоге."""
    ensure_dir(destination.parent)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=str(destination.parent),
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, destination)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    return destination


def atomic_write_text(destination: Path, text: str) -> Path:
    """Записать UTF-8 текст атомарно."""
    return atomic_write_bytes(destination, text.encode("utf-8"))


def write_json(destination: Path, payload: Any) -> Path:
    """Записать JSON с детерминированным форматированием и переводом строки."""
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    return atomic_write_text(destination, text)


def write_jsonl(destination: Path, rows: list[dict[str, Any]]) -> int:
    """Записать JSONL и вернуть число строк."""
    lines = [json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows]
    atomic_write_text(destination, "\n".join(lines) + ("\n" if lines else ""))
    return len(lines)


def read_json(path: Path) -> Any:
    """Прочитать JSON из файла."""
    return json.loads(path.read_text(encoding="utf-8"))


def stable_sort_dicts(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    """Отсортировать словари по строковому ключу без зависимости от локали."""
    return sorted(rows, key=lambda row: str(row.get(key, "")))


def finite_float(value: float | int | None, *, digits: int = 3) -> float | None:
    """Округлить число half-away-from-zero и вернуть None для NaN/Infinity."""
    if value is None:
        return None
    numeric = float(value)
    if not math.isfinite(numeric):
        return None
    factor = 10**digits
    scaled = abs(numeric) * factor
    rounded = math.floor(scaled + 0.5) / factor
    return math.copysign(rounded, numeric)


def compute_statistics(values: list[float | None]) -> dict[str, float | int | None]:
    """Рассчитать описательные статистики, сохраняя null при отсутствии данных."""
    clean = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if not clean:
        return {
            "n": 0,
            "mean": None,
            "sd": None,
            "median": None,
            "min": None,
            "max": None,
        }
    count = len(clean)
    mean = sum(clean) / count
    variance = sum((value - mean) ** 2 for value in clean) / count if count > 1 else 0.0
    ordered = sorted(clean)
    middle = count // 2
    median = ordered[middle] if count % 2 else (ordered[middle - 1] + ordered[middle]) / 2
    return {
        "n": count,
        "mean": finite_float(mean),
        "sd": finite_float(math.sqrt(variance)),
        "median": finite_float(median),
        "min": finite_float(min(clean)),
        "max": finite_float(max(clean)),
    }


def relative_path(path: Path) -> str:
    """Вернуть путь относительно корня проекта в POSIX-формате."""
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()
