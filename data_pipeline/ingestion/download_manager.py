"""Менеджер загрузки с обязательным кэш-фолбэком.

Если сеть или файл недоступны, используются кэшированные данные, а результат
явно помечается FallbackStatus. Молчаливая подмена запрещена.
"""

from __future__ import annotations

import os
import shutil
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from shared.contracts import FallbackStatus  # noqa: E402
from data_pipeline.common import sha256_file, sha256_text  # noqa: E402

DOWNLOAD_CACHE_DIR: Path = Path(__file__).resolve().parents[1] / "cache" / "downloads"
MAX_CONCURRENT_DOWNLOADS: int = 4
MAX_RETRIES: int = 3
RETRY_BACKOFF_SEC: float = 2.0
CHUNK_SIZE_BYTES: int = 1024 * 1024
USER_AGENT: str = "ASTRALIS-SPEC1/1.0"


@dataclass(frozen=True)
class DownloadResult:
    """Результат загрузки с явным статусом деградации."""

    path: Path | None
    source_url: str
    fallback_status: FallbackStatus
    sha256: str | None
    from_cache: bool
    error: str | None


def atomic_write_bytes(destination: Path, payload: bytes) -> Path:
    """Записать файл через временный путь и атомарное переименование."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.part")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, destination)
    return destination


def _cache_path(source_url: str) -> Path:
    """Детерминированный путь кэша по URL."""
    suffix = Path(source_url.split("?", 1)[0]).suffix or ".bin"
    return DOWNLOAD_CACHE_DIR / f"{sha256_text(source_url)}{suffix}"


def _stream_download(
    source_url: str,
    destination: Path,
    *,
    resume_from: int = 0,
) -> tuple[str, int]:
    """Скачать URL потоково; при поддержке сервера продолжить с resume_from."""
    import hashlib

    request = urllib.request.Request(source_url, headers={"User-Agent": USER_AGENT})
    mode = "wb"
    if resume_from > 0:
        request.add_header("Range", f"bytes={resume_from}-")
        mode = "ab"
    digest = hashlib.sha256()
    total = 0
    with urllib.request.urlopen(request, timeout=120) as response, destination.open(mode) as handle:
        if resume_from > 0 and response.status != 206:
            raise OSError("Server did not honor the Range header; resume is unavailable.")
        while True:
            chunk = response.read(CHUNK_SIZE_BYTES)
            if not chunk:
                break
            handle.write(chunk)
            digest.update(chunk)
            total += len(chunk)
    return digest.hexdigest(), total


def download_with_cache(
    source_url: str,
    destination: Path,
    *,
    expected_sha256: str | None = None,
    allow_cache: bool = True,
) -> DownloadResult:
    """Скачать файл; при ошибке вернуть кэш с CACHE_FALLBACK или UNAVAILABLE."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    cache_path = _cache_path(source_url)
    cached_valid = False
    if allow_cache and cache_path.exists() and cache_path.stat().st_size > 0:
        cached_valid = expected_sha256 is None or sha256_file(cache_path) == expected_sha256

    last_error: str | None = None
    resume_temporary = destination.with_name(f".{destination.name}.resume.part")
    existing_resume_bytes = resume_temporary.stat().st_size if resume_temporary.exists() else 0
    for attempt in range(MAX_RETRIES):
        temporary = resume_temporary
        try:
            digest, size = _stream_download(source_url, temporary, resume_from=existing_resume_bytes)
            if expected_sha256 is not None and digest != expected_sha256:
                raise ValueError(
                    f"Checksum mismatch for {source_url}: expected {expected_sha256}, got {digest}"
                )
            os.replace(temporary, destination)
            DOWNLOAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(destination, cache_path)
            return DownloadResult(
                path=destination,
                source_url=source_url,
                fallback_status=FallbackStatus.NONE,
                sha256=digest,
                from_cache=False,
                error=None,
            )
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, OSError) as exc:
            last_error = str(exc)
            # Частичный файл сохраняется для продолжения; при checksum mismatch сбрасываем.
            if "Checksum mismatch" in last_error or "Range header" in last_error:
                try:
                    temporary.unlink(missing_ok=True)
                    existing_resume_bytes = 0
                except OSError:
                    pass
            else:
                existing_resume_bytes = temporary.stat().st_size if temporary.exists() else 0
            if attempt + 1 < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SEC * (2**attempt))

    if cached_valid:
        shutil.copyfile(cache_path, destination)
        return DownloadResult(
            path=destination,
            source_url=source_url,
            fallback_status=FallbackStatus.CACHE_FALLBACK,
            sha256=sha256_file(destination),
            from_cache=True,
            error=last_error,
        )
    return DownloadResult(
        path=None,
        source_url=source_url,
        fallback_status=FallbackStatus.UNAVAILABLE,
        sha256=None,
        from_cache=False,
        error=last_error,
    )


def download_many(
    requests: list[tuple[str, Path]],
    *,
    allow_cache: bool = True,
) -> list[DownloadResult]:
    """Загрузить несколько файлов с ограничением параллелизма."""
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DOWNLOADS) as pool:
        futures = [
            pool.submit(download_with_cache, url, destination, allow_cache=allow_cache)
            for url, destination in requests
        ]
        return [future.result() for future in futures]


def report_fallback(results: list[DownloadResult]) -> FallbackStatus:
    """Свести статусы загрузки в один статус для манифеста бандла."""
    statuses = {result.fallback_status for result in results}
    if FallbackStatus.UNAVAILABLE in statuses:
        return FallbackStatus.UNAVAILABLE
    if FallbackStatus.SYNTHETIC_FALLBACK in statuses:
        return FallbackStatus.SYNTHETIC_FALLBACK
    if FallbackStatus.CACHE_FALLBACK in statuses:
        return FallbackStatus.CACHE_FALLBACK
    return FallbackStatus.NONE
