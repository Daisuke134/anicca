"""Storefront agent schemas must be ones the structured-output provider will accept.

`storefront_category_child.schema.json` expressed a nullable field as
`oneOf: [string, null]`. That is valid JSON Schema and every local test passed, but the
provider answered

    Invalid schema for response_format 'codex_output_schema':
    In context=('properties', 'type_value'), 'oneOf' is not permitted.

so the call returned rc=1 and the wake died with `storefront_category_child_failed:1`.
Only production said no. These checks encode the restriction the provider actually
enforces, measured from that error and from the schemas it does accept:
`storefront_judgement.schema.json` uses `anyOf` and runs in production, so `anyOf` stays
allowed. A nullable field is written the way the rest of this directory already writes
one -- `"type": ["string", "null"]`.

Scope is deliberately the schemas storefront passes to an agent via `--schema`. Schemas
used only for local record validation (`kpi-record`, `market_product_contract`) never
reach the provider and are free to use the full vocabulary.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

GIG_DIR = Path(__file__).resolve().parents[1]
SCHEMA_DIR = GIG_DIR / "schemas"
DIRECT = GIG_DIR / "scripts" / "storefront_direct.py"

# Combinators the provider rejects inside a response_format schema. `anyOf` is absent on
# purpose: it is accepted, and storefront_judgement.schema.json relies on it in production.
UNSUPPORTED = ("oneOf", "allOf", "not")

AGENT_SCHEMAS = sorted({
    SCHEMA_DIR / name
    for name in re.findall(r'SCHEMA = GIG_DIR / "schemas" / "([^"]+)"',
                           DIRECT.read_text(encoding="utf-8"))
})


def _walk(node, path="$"):
    if isinstance(node, dict):
        for key, value in node.items():
            yield f"{path}.{key}", key
            yield from _walk(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk(value, f"{path}[{index}]")


def test_agent_schema_list_is_not_empty():
    # A regex that silently stops matching would turn every check below into a no-op.
    assert len(AGENT_SCHEMAS) >= 8
    assert all(path.is_file() for path in AGENT_SCHEMAS)


@pytest.mark.parametrize("schema_path", AGENT_SCHEMAS, ids=lambda p: p.name)
def test_agent_schema_uses_no_provider_rejected_combinator(schema_path):
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    found = [where for where, key in _walk(schema) if key in UNSUPPORTED]
    assert not found, (
        f"{schema_path.name} uses {found}, which the structured-output provider rejects. "
        'Express a nullable field as {"type": ["string", "null"]} instead.'
    )


def test_category_child_type_value_is_nullable_the_supported_way():
    schema = json.loads(
        (SCHEMA_DIR / "storefront_category_child.schema.json").read_text(encoding="utf-8"))
    type_value = schema["properties"]["type_value"]
    assert type_value["type"] == ["string", "null"]
    assert type_value["pattern"] == "^[0-9]+$"
    assert "type_value" in schema["required"]
