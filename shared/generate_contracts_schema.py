"""Генератор канонической JSON Schema из Pydantic-контрактов.

Запуск:
    python shared/generate_contracts_schema.py
    python shared/generate_contracts_schema.py --check

Генератор намеренно удаляет русские docstring-описания моделей: JSON Schema
предназначена для международной проверки и должна содержать только английский
текст. Описания полей (Field(description=...)) уже английские и сохраняются.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Корень репозитория нужен для импорта backend.app.schemas при прямом запуске.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from pydantic.json_schema import models_json_schema  # noqa: E402

from backend.app.schemas import CANONICAL_CONTRACTS  # noqa: E402

SCHEMA_PATH = Path(__file__).resolve().parent / "contracts.schema.json"
CYRILLIC = re.compile(r"[\u0400-\u04FF]")

TOP_LEVEL = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://astralis.space/contracts.schema.json",
    "title": "ASTRALIS + IMPACT Canonical Data Contracts",
    "description": (
        "Single cross-language contract for Python (Pydantic v2), TypeScript, and offline "
        "data bundles. Every measurement and derived feature references provenance records. "
        "Field names and descriptions are English; Russian is allowed only in source comments."
    ),
}


def remove_non_english_descriptions(node: Any) -> None:
    """Рекурсивно удалить описания, содержащие кириллицу."""
    if isinstance(node, dict):
        description = node.get("description")
        if isinstance(description, str) and CYRILLIC.search(description):
            del node["description"]
        for value in node.values():
            remove_non_english_descriptions(value)
    elif isinstance(node, list):
        for item in node:
            remove_non_english_descriptions(item)


def build_schema() -> dict[str, Any]:
    """Собрать JSON Schema Draft 2020-12 из CANONICAL_CONTRACTS."""
    _, generated = models_json_schema(
        [(model, "validation") for model in CANONICAL_CONTRACTS],
        ref_template="#/$defs/{model}",
    )
    definitions = generated["$defs"]
    remove_non_english_descriptions(definitions)

    schema: dict[str, Any] = dict(TOP_LEVEL)
    schema["oneOf"] = [
        {"$ref": f"#/$defs/{model.__name__}"} for model in CANONICAL_CONTRACTS
    ]
    schema["$defs"] = definitions
    return schema


def serialized(schema: dict[str, Any]) -> str:
    """Детерминированная сериализация с завершающим переводом строки."""
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    """CLI: записать схему или проверить, что файл не устарел."""
    parser = argparse.ArgumentParser(description="Generate or check contracts.schema.json")
    parser.add_argument("--check", action="store_true", help="Fail if the file is out of date")
    args = parser.parse_args()

    schema = build_schema()
    expected = serialized(schema)

    if args.check:
        if not SCHEMA_PATH.exists():
            print("Schema file is missing.")
            return 1
        if SCHEMA_PATH.read_text(encoding="utf-8") != expected:
            print("Schema file is out of date. Run: python shared/generate_contracts_schema.py")
            return 1
        print("Schema file is up to date.")
        return 0

    SCHEMA_PATH.write_text(expected, encoding="utf-8")
    print(f"Wrote {SCHEMA_PATH} with {len(schema['$defs'])} definitions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
