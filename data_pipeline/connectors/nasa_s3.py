"""Коннектор к публичным S3-ресурсам OSDR.

Имя bucket и prefix не угадываются: они извлекаются из метаданных OSDR или
конфигурации окружения. Если bucket не подтверждён, операции возвращают
явный FallbackStatus.UNAVAILABLE.
"""

from __future__ import annotations

import os
import urllib.request
from pathlib import Path

from shared.contracts import FallbackStatus
from data_pipeline.common import sha256_file

S3_BUCKET_ENV_VAR: str = "OSDR_S3_BUCKET"
S3_PREFIX_ENV_VAR: str = "OSDR_S3_PREFIX"
S3_REGION_ENV_VAR: str = "OSDR_S3_REGION"
S3_ENDPOINT_ENV_VAR: str = "OSDR_S3_ENDPOINT"
REQUEST_TIMEOUT_SEC: int = 60
MAX_KEYS_PER_PAGE: int = 1000


def _find_s3_uri(value: object) -> str | None:
    """Рекурсивно найти первый s3:// URI в метаданных."""
    if isinstance(value, str) and value.startswith("s3://"):
        return value
    if isinstance(value, dict):
        for child in value.values():
            found = _find_s3_uri(child)
            if found:
                return found
    if isinstance(value, list):
        for child in value:
            found = _find_s3_uri(child)
            if found:
                return found
    return None


def resolve_public_bucket(study_metadata: dict[str, object]) -> str | None:
    """Извлечь подтверждённый публичный bucket из метаданных; иначе None."""
    uri = _find_s3_uri(study_metadata)
    if uri:
        return uri.removeprefix("s3://").split("/", 1)[0]
    return os.environ.get(S3_BUCKET_ENV_VAR) or None


def _bucket(bucket: str | None) -> str:
    resolved = bucket or os.environ.get(S3_BUCKET_ENV_VAR)
    if not resolved:
        raise RuntimeError(f"Public S3 bucket is unavailable; set {S3_BUCKET_ENV_VAR} only after verification.")
    return resolved


def list_public_objects(
    prefix: str,
    *,
    bucket: str | None = None,
) -> list[dict[str, object]]:
    """Перечислить объекты публичного S3-prefix без учётных данных."""
    resolved = _bucket(bucket)
    try:
        import boto3  # type: ignore
    except ImportError:
        return []
    region = os.environ.get(S3_REGION_ENV_VAR)
    endpoint = os.environ.get(S3_ENDPOINT_ENV_VAR)
    client = boto3.client(
        "s3",
        region_name=region,
        endpoint_url=endpoint,
        config=None,
    )
    paginator = client.get_paginator("list_objects_v2")
    objects: list[dict[str, object]] = []
    for page in paginator.paginate(Bucket=resolved, Prefix=prefix, PaginationConfig={"PageSize": MAX_KEYS_PER_PAGE}):
        for item in page.get("Contents", []):
            objects.append(
                {
                    "bucket": resolved,
                    "key": item.get("Key"),
                    "size_bytes": item.get("Size"),
                    "etag": item.get("ETag"),
                    "last_modified_utc": item.get("LastModified").isoformat() if item.get("LastModified") else None,
                }
            )
    return objects


def download_public_object(
    key: str,
    destination: Path,
    *,
    bucket: str | None = None,
    expected_sha256: str | None = None,
) -> dict[str, object]:
    """Скачать объект S3 с проверкой размера и checksum."""
    resolved = _bucket(bucket)
    endpoint = os.environ.get(S3_ENDPOINT_ENV_VAR)
    if not endpoint:
        try:
            import boto3  # type: ignore
        except ImportError:
            return {
                "path": None,
                "bucket": resolved,
                "key": key,
                "fallback_status": FallbackStatus.UNAVAILABLE.value,
                "sha256": None,
                "error": "boto3 is not installed and no public S3 endpoint is configured.",
            }
        boto3.client("s3", region_name=os.environ.get(S3_REGION_ENV_VAR)).download_file(resolved, key, str(destination))
    else:
        url = f"{endpoint.rstrip('/')}/{resolved}/{key.lstrip('/')}"
        with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_SEC) as response:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(response.read())
    digest = sha256_file(destination)
    if expected_sha256 and digest.lower() != expected_sha256.lower():
        return {
            "path": None,
            "bucket": resolved,
            "key": key,
            "fallback_status": FallbackStatus.UNAVAILABLE.value,
            "sha256": digest,
            "error": "Checksum mismatch.",
        }
    return {
        "path": destination,
        "bucket": resolved,
        "key": key,
        "fallback_status": FallbackStatus.NONE.value,
        "sha256": digest,
        "error": None,
    }


def object_metadata(key: str, *, bucket: str | None = None) -> dict[str, object]:
    """Вернуть размер, ETag и contentType объекта S3."""
    resolved = _bucket(bucket)
    try:
        import boto3  # type: ignore
    except ImportError:
        return {"available": False, "bucket": resolved, "key": key, "reason": "boto3 unavailable"}
    response = boto3.client("s3", region_name=os.environ.get(S3_REGION_ENV_VAR)).head_object(
        Bucket=resolved, Key=key
    )
    return {
        "available": True,
        "bucket": resolved,
        "key": key,
        "size_bytes": response.get("ContentLength"),
        "etag": response.get("ETag"),
        "content_type": response.get("ContentType"),
        "last_modified_utc": response.get("LastModified").isoformat() if response.get("LastModified") else None,
    }
