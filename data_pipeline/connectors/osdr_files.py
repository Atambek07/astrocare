"""Доступ к публичным файлам OSDR и локальному кэшу.

Оригинальные файлы NASA сохраняются отдельно от обработанных и синтетических
данных: `data_bundle/raw/nasa/`.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from data_pipeline.common import ensure_dir, sha256_file, utc_now_iso  # noqa: E402
from data_pipeline.connectors import osdr_api  # noqa: E402
from data_pipeline.ingestion.download_manager import download_with_cache  # noqa: E402

RAW_NASA_DIR: Path = Path(__file__).resolve().parents[2] / "data_bundle" / "raw" / "nasa"
CACHE_DIR: Path = Path(__file__).resolve().parents[1] / "cache" / "osdr_files"

REQUEST_TIMEOUT_SEC: int = 60
CHUNK_SIZE_BYTES: int = 1024 * 1024
MAX_FILE_SIZE_BYTES: int = 20 * 1024 * 1024 * 1024
ALLOWED_SCHEMES: tuple[str, ...] = ("https",)


def list_public_files(study_id: str) -> list[dict[str, object]]:
    """Вернуть публичные файлы исследования с метаданными и checksum."""
    index = osdr_api.fetch_study_file_index(study_id)
    key = f"OSD-{osdr_api.normalize_study_identifier(study_id)}"
    study = (index.get("studies") or {}).get(key, {}) if isinstance(index.get("studies"), dict) else {}
    files = study.get("study_files", []) if isinstance(study, dict) else []
    public: list[dict[str, object]] = []
    for raw in files:
        if not isinstance(raw, dict):
            continue
        if raw.get("restricted") or not raw.get("visible", True):
            continue
        remote_url = str(raw.get("remote_url") or "")
        public.append(
            {
                **raw,
                "file_name": str(raw.get("file_name") or ""),
                "file_size": int(raw.get("file_size") or 0),
                "category": str(raw.get("category") or "").strip(),
                "subcategory": str(raw.get("subcategory") or "").strip(),
                "restricted": bool(raw.get("restricted", False)),
                "visible": bool(raw.get("visible", True)),
                "source_url": osdr_api.OSDR_BASE_URL + remote_url if remote_url.startswith("/") else remote_url,
                "verified_at_utc": utc_now_iso(),
            }
        )
    return public


def download_file(
    source_url: str,
    destination: Path,
    *,
    expected_sha256: str | None = None,
    use_cache: bool = True,
) -> dict[str, object]:
    """Скачать файл атомарно, проверить checksum и сообщить FallbackStatus."""
    if not source_url.lower().startswith(tuple(f"{scheme}://" for scheme in ALLOWED_SCHEMES)):
        raise ValueError(f"Only public HTTPS URLs are allowed: {source_url}")
    result = download_with_cache(
        source_url,
        destination,
        expected_sha256=expected_sha256,
        allow_cache=use_cache,
    )
    return {
        "path": result.path,
        "source_url": source_url,
        "fallback_status": result.fallback_status.value,
        "sha256": result.sha256,
        "from_cache": result.from_cache,
        "error": result.error,
    }


def verify_checksum(path: Path, expected_sha256: str) -> bool:
    """Проверить SHA-256 файла; не изменять оригинал."""
    return path.exists() and sha256_file(path).lower() == expected_sha256.lower()


def build_file_manifest(study_id: str) -> list[dict[str, object]]:
    """Собрать манифест файлов: URL, размер, checksum, формат, статус."""
    from data_pipeline.ingestion.format_detector import detect_file_format, detect_modality

    manifest: list[dict[str, object]] = []
    for record in list_public_files(study_id):
        file_name = str(record["file_name"])
        local = RAW_NASA_DIR / f"OSD-{osdr_api.normalize_study_identifier(study_id)}" / file_name
        manifest.append(
            {
                "study_id": f"OSD-{osdr_api.normalize_study_identifier(study_id)}",
                "file_name": file_name,
                "file_size": record["file_size"],
                "category": record["category"],
                "subcategory": record["subcategory"],
                "source_url": record["source_url"],
                "format": detect_file_format(local) if local.exists() else detect_file_format(Path(file_name)),
                "modality": detect_modality(file_name, record).value,
                "downloaded": local.exists() and local.stat().st_size == int(record["file_size"]),
                "local_path": str(local.relative_to(_PROJECT_ROOT)) if local.exists() else None,
                "sha256": sha256_file(local) if local.exists() else None,
                "restricted": False,
                "visible": True,
            }
        )
    return manifest


def copy_redistributable_raw_files(study_id: str) -> list[Path]:
    """Скопировать в raw/nasa только файлы, разрешённые к распространению."""
    copied: list[Path] = []
    target_dir = ensure_dir(RAW_NASA_DIR / f"OSD-{osdr_api.normalize_study_identifier(study_id)}")
    for record in list_public_files(study_id):
        if record.get("restricted") or not record.get("visible", True):
            continue
        source = CACHE_DIR / str(record["file_name"])
        if source.exists():
            destination = target_dir / str(record["file_name"])
            if not destination.exists():
                shutil.copy2(source, destination)
            copied.append(destination)
    return copied
