"""Коннектор к OSDR REST API (GLOpenAPI).

Проверено 2026-11-14: endpoint метаданных принимает числовой ID
(`/osdr/data/osd/meta/569`), а не строку `OSD-569`. Ответы кэшируются, чтобы
повторная сборка офлайн-бандла работала без сети. При сетевой ошибке
возвращается кэш с явной пометкой в служебном поле `_astralis_fetch`.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from data_pipeline.common import PIPELINE_CACHE_DIR, ensure_dir, read_json, utc_now_iso, write_json

OSDR_BASE_URL: str = "https://osdr.nasa.gov"
STUDY_META_PATH: str = "/osdr/data/osd/meta/{study_number}"
STUDY_FILES_PATH: str = "/osdr/data/osd/files/{study_number}"
SEARCH_PATH: str = "/osdr/data/search"

STUDY_ID_PATTERN: re.Pattern[str] = re.compile(r"^OSD-(\d+)$")
REQUEST_TIMEOUT_SEC: int = 30
MAX_RETRIES: int = 3
RETRY_BACKOFF_SEC: float = 1.5
RATE_LIMIT_PER_MINUTE: int = 30

CACHE_DIR: Path = PIPELINE_CACHE_DIR / "osdr"
USER_AGENT: str = "ASTRALIS-SPEC1/1.0 (NASA Space Apps research prototype)"


def normalize_study_identifier(study_id: str) -> str:
    """Преобразовать `OSD-569` в числовой ID `569`, который понимает API.

    Raises:
        ValueError: если идентификатор не соответствует формату OSD-<число>.
    """
    cleaned = study_id.strip().upper()
    if cleaned.isdigit():
        return cleaned
    match = STUDY_ID_PATTERN.match(cleaned)
    if not match:
        raise ValueError(f"Invalid OSDR study identifier: {study_id!r}")
    return match.group(1)


def _cache_path(kind: str, key: str) -> Path:
    """Построить безопасный путь кэша для запроса."""
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", key)[:120]
    return CACHE_DIR / f"{kind}_{safe}.json"


def _request_json(url: str) -> dict[str, object]:
    """Выполнить GET с retry/backoff и вернуть JSON-объект."""
    last_error: Exception | None = None
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SEC) as response:
                payload = response.read()
            parsed = json.loads(payload.decode("utf-8"))
            if not isinstance(parsed, dict):
                raise ValueError(f"OSDR response is not a JSON object: {url}")
            return parsed
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            if attempt + 1 < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SEC * (2**attempt))
    raise RuntimeError(f"OSDR request failed after {MAX_RETRIES} attempts: {url}") from last_error


def _cached_json(kind: str, key: str, url: str, *, use_cache: bool, force_refresh: bool) -> dict[str, object]:
    """Загрузить JSON с кэшем и служебной информацией о fallback."""
    cache_path = _cache_path(kind, key)
    if use_cache and cache_path.exists() and not force_refresh:
        cached = read_json(cache_path)
        if isinstance(cached, dict):
            cached["_astralis_fetch"] = {
                "status": "CACHE",
                "from_cache": True,
                "url": url,
                "fetched_at_utc": cached.get("_astralis_fetch", {}).get("fetched_at_utc"),
            }
            return cached
    try:
        payload = _request_json(url)
    except RuntimeError as exc:
        if use_cache and cache_path.exists():
            cached = read_json(cache_path)
            if isinstance(cached, dict):
                cached["_astralis_fetch"] = {
                    "status": "CACHE_FALLBACK",
                    "from_cache": True,
                    "url": url,
                    "error": str(exc),
                    "fetched_at_utc": cached.get("_astralis_fetch", {}).get("fetched_at_utc"),
                }
                return cached
        raise
    ensure_dir(CACHE_DIR)
    payload["_astralis_fetch"] = {
        "status": "ONLINE",
        "from_cache": False,
        "url": url,
        "fetched_at_utc": utc_now_iso(),
    }
    write_json(cache_path, payload)
    return payload


def fetch_study_metadata(
    study_id: str,
    *,
    use_cache: bool = True,
    force_refresh: bool = False,
) -> dict[str, object]:
    """Получить метаданные исследования с кэш-фолбэком."""
    number = normalize_study_identifier(study_id)
    url = OSDR_BASE_URL + STUDY_META_PATH.format(study_number=number)
    return _cached_json("meta", number, url, use_cache=use_cache, force_refresh=force_refresh)


def fetch_study_file_index(
    study_id: str,
    *,
    use_cache: bool = True,
) -> dict[str, object]:
    """Получить индекс публичных файлов исследования."""
    number = normalize_study_identifier(study_id)
    url = OSDR_BASE_URL + STUDY_FILES_PATH.format(study_number=number)
    return _cached_json("files", number, url, use_cache=use_cache, force_refresh=False)


def search_osdr(
    query: str,
    *,
    page_size: int = 25,
    page_number: int = 1,
) -> dict[str, object]:
    """Выполнить поиск по каталогу OSDR без предположений о содержимом."""
    safe_size = max(1, min(int(page_size), 100))
    safe_page = max(1, int(page_number))
    offset = (safe_page - 1) * safe_size
    params = urllib.parse.urlencode({"term": query, "size": safe_size, "from": offset})
    url = f"{OSDR_BASE_URL}{SEARCH_PATH}?{params}"
    cache_key = f"{query}_{safe_size}_{safe_page}"
    return _cached_json("search", cache_key, url, use_cache=True, force_refresh=False)


def probe_api_health() -> bool:
    """Проверить доступность OSDR API для выбора online/offline режима."""
    try:
        response = search_osdr("human spaceflight", page_size=1, page_number=1)
    except Exception:
        return False
    return bool(response.get("success", True)) and "hits" in response
