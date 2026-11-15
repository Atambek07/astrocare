"""Legacy-обёртка ETL для NASA OSDR GLOpenAPI.

Семь исследований Inspiration4 подтверждены 2026-11-14 по метаданным OSDR:
OSD-569, OSD-570, OSD-571, OSD-572, OSD-573, OSD-575, OSD-656.
Это молекулярные, лабораторные и микробиомные исследования с pre/post-flight
образцами, а НЕ непрерывная 180-дневная телеметрия.

Новый код должен использовать data_pipeline/connectors/osdr_api.py.
Реализация — Data-agent (SPEC 1).
"""

from __future__ import annotations

import json
from pathlib import Path

# Все подтверждённые исследования Inspiration4.
INSPIRATION4_STUDY_IDS: tuple[str, ...] = (
    "OSD-569",
    "OSD-570",
    "OSD-571",
    "OSD-572",
    "OSD-573",
    "OSD-575",
    "OSD-656",
)

# Проверенный endpoint принимает числовой ID (без префикса OSD-).
OSDR_API_BASE: str = "https://osdr.nasa.gov/osdr/data"
STUDY_META_PATH: str = "/osd/meta/{study_number}"
STUDY_FILES_PATH: str = "/osd/files/{study_number}"
REQUEST_TIMEOUT_SEC: int = 30
MAX_RETRIES: int = 3

# Локальный кэш: data_pipeline/cache/osdr/<study_id>.json
CACHE_DIR: Path = Path(__file__).resolve().parent / "cache" / "osdr"


def fetch_study(study_id: str, force_refresh: bool = False) -> dict[str, object]:
    """Скачать одно исследование OSDR или вернуть кэш при сетевой ошибке.

    Args:
        study_id: Идентификатор вида "OSD-569".
        force_refresh: Игнорировать существующий кэш.

    Returns:
        Словарь с сырым ответом OSDR и метаданными источника.
    """
    raise NotImplementedError("SPEC 1: implement OSDR GLOpenAPI fetch.")


def load_cached_study(study_id: str) -> dict[str, object] | None:
    """Прочитать кэш исследования; None, если кэша нет."""
    raise NotImplementedError("SPEC 1: implement cache read.")


def save_cached_study(study_id: str, payload: dict[str, object]) -> Path:
    """Атомарно сохранить ответ OSDR в CACHE_DIR."""
    raise NotImplementedError("SPEC 1: implement cache write.")


def normalize_study(study_id: str, payload: dict[str, object]) -> dict[str, object]:
    """Привести ответ OSDR к плоской структуре для build_offline_bundle.py."""
    raise NotImplementedError("SPEC 1: implement OSDR normalization.")


def fetch_all_studies(
    study_ids: tuple[str, ...] = INSPIRATION4_STUDY_IDS,
    force_refresh: bool = False,
) -> dict[str, dict[str, object]]:
    """Скачать/загрузить все исследования Inspiration4."""
    raise NotImplementedError("SPEC 1: implement multi-study fetch.")


def main() -> None:
    """CLI: python -m data_pipeline.fetch_osdr_glopenapi [--force]."""
    raise NotImplementedError("SPEC 1: implement CLI entrypoint.")


if __name__ == "__main__":
    main()
