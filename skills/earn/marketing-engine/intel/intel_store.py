#!/usr/bin/env python3
"""Validate the four canonical Marketing Engine JSON Lines intel stores."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys


STORES = {
    "playbook": "playbook.jsonl",
    "hook-library": "hook-library.jsonl",
    "creators": "creators.jsonl",
    "ad-swipe": "ad-swipe.jsonl",
}
STATUS = {"new", "queued", "running", "won", "lost", "done", "retired"}
LANES = {"app", "ebook", "content", "outreach"}
LANGUAGES = {"en", "ja", "es", "multi", "unknown"}
ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)+$")


class StoreError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise StoreError(message)


def _timestamp(value, field: str) -> None:
    _require(isinstance(value, str) and value, f"{field} is required")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StoreError(f"{field} must be RFC3339") from exc
    _require(parsed.tzinfo is not None, f"{field} requires timezone")


def _url_or_null(row: dict, url_field: str, reason_field: str) -> None:
    url = row.get(url_field)
    if url is None:
        _require(isinstance(row.get(reason_field), str) and row[reason_field],
                 f"{reason_field} required when {url_field} is null")
    else:
        _require(isinstance(url, str) and url.startswith("https://"),
                 f"{url_field} must be https URL or null")
        _require(row.get(reason_field) is None,
                 f"{reason_field} must be null when {url_field} exists")


def _base(row: dict, schema_version: str) -> None:
    _require(row.get("schema_version") == schema_version, "invalid schema_version")
    _require(isinstance(row.get("id"), str) and ID_RE.fullmatch(row["id"]) is not None,
             "id has invalid format")
    _timestamp(row.get("captured_at"), "captured_at")


def _playbook(row: dict) -> None:
    required = {
        "schema_version", "id", "source_type", "source_url", "source_handle",
        "source_null_reason", "captured_at", "provenance", "claim", "mechanism",
        "applies_to", "testable", "status", "evidence_url",
        "evidence_null_reason", "our_result", "result_evidence",
    }
    _require(set(row) == required, "playbook fields do not match schema")
    _base(row, "marketing.tactic.v1")
    _url_or_null(row, "source_url", "source_null_reason")
    _url_or_null(row, "evidence_url", "evidence_null_reason")
    _require(row["source_type"] in {"x_article", "owner_observation", "oss", "web", "video", "ad"},
             "invalid source_type")
    _require(row["provenance"] in {"owner_supplied_summary", "live_observed", "imported_oss"},
             "invalid provenance")
    _require(row["source_handle"] is None or
             (isinstance(row["source_handle"], str) and row["source_handle"]),
             "source_handle must be string or null")
    _require(isinstance(row["claim"], str) and row["claim"], "claim required")
    _require(isinstance(row["mechanism"], str) and row["mechanism"], "mechanism required")
    _require(isinstance(row["applies_to"], list) and row["applies_to"] and
             set(row["applies_to"]) <= LANES and len(row["applies_to"]) == len(set(row["applies_to"])),
             "applies_to invalid")
    _require(isinstance(row["testable"], bool), "testable must be boolean")
    _require(row["status"] in STATUS, "invalid status")
    if row["status"] in {"new", "queued", "running"}:
        _require(row["our_result"] is None and row["result_evidence"] is None,
                 "our_result must be null before a completed result")
    if row["status"] in {"won", "lost", "done"}:
        _require(isinstance(row["our_result"], str) and row["our_result"] and
                 isinstance(row["result_evidence"], str) and row["result_evidence"],
                 "our_result and result_evidence required for completed status")


def _hook(row: dict) -> None:
    required = {
        "schema_version", "id", "text", "language", "product_ids", "source_type",
        "source_url", "source_null_reason", "captured_at", "provenance", "rubric",
        "status", "ewma_score", "observations", "evidence_url", "evidence_null_reason",
    }
    _require(set(row) == required, "hook fields do not match schema")
    _base(row, "marketing.hook.v1")
    _url_or_null(row, "source_url", "source_null_reason")
    _url_or_null(row, "evidence_url", "evidence_null_reason")
    _require(isinstance(row["text"], str) and row["text"].strip(), "hook text required")
    _require(row["language"] in LANGUAGES, "invalid hook language")
    _require(isinstance(row["product_ids"], list), "product_ids must be array")
    _require(row["status"] in {"active", "retired"}, "invalid hook status")
    _require(row["ewma_score"] is None or isinstance(row["ewma_score"], (int, float)),
             "ewma_score must be number or null")
    _require(isinstance(row["observations"], int) and row["observations"] >= 0,
             "observations must be non-negative integer")
    rubric = row["rubric"]
    _require(isinstance(rubric, dict) and set(rubric) == {
        "hook", "emotional_peak", "conflict", "quotability", "practical_value", "total"},
        "invalid hook rubric")
    _require(all(value is None or isinstance(value, (int, float)) for value in rubric.values()),
             "hook rubric values must be numeric or null")


def _creator(row: dict) -> None:
    required = {
        "schema_version", "id", "platform", "handle", "language", "product_id",
        "source_url", "source_null_reason", "captured_at", "metrics", "green_flags",
        "red_flags", "verdict", "evidence_url", "evidence_null_reason",
    }
    _require(set(row) == required, "creator fields do not match schema")
    _base(row, "marketing.creator.v1")
    _url_or_null(row, "source_url", "source_null_reason")
    _url_or_null(row, "evidence_url", "evidence_null_reason")
    _require(row["platform"] in {"tiktok", "instagram", "youtube", "x"},
             "invalid creator platform")
    _require(isinstance(row["handle"], str) and row["handle"], "creator handle required")
    _require(row["language"] in LANGUAGES, "invalid creator language")
    _require(row["product_id"] is None or isinstance(row["product_id"], str),
             "product_id must be string or null")
    _require(isinstance(row["metrics"], list), "creator metrics must be array")
    _require(isinstance(row["green_flags"], list) and isinstance(row["red_flags"], list),
             "creator flags must be arrays")
    _require(row["verdict"] in {"green", "red", "unknown"}, "invalid creator verdict")


def _ad(row: dict) -> None:
    required = {
        "schema_version", "id", "platform", "advertiser", "product_id", "source_url",
        "source_null_reason", "captured_at", "first_seen_at", "last_seen_at",
        "impressions", "impressions_null_reason", "why_it_works", "replication_plan",
        "status", "evidence_url", "evidence_null_reason",
    }
    _require(set(row) == required, "ad fields do not match schema")
    _base(row, "marketing.ad-swipe.v1")
    _url_or_null(row, "source_url", "source_null_reason")
    _url_or_null(row, "evidence_url", "evidence_null_reason")
    _require(row["platform"] in {"meta", "tiktok", "youtube", "app_store", "web"},
             "invalid ad platform")
    _require(isinstance(row["advertiser"], str) and row["advertiser"], "advertiser required")
    _require(row["impressions"] is None or
             (isinstance(row["impressions"], int) and row["impressions"] >= 0),
             "impressions must be non-negative integer or null")
    if row["impressions"] is None:
        _require(isinstance(row["impressions_null_reason"], str) and row["impressions_null_reason"],
                 "impressions_null_reason required")
    _require(row["status"] in {"new", "queued", "tested", "won", "lost", "retired"},
             "invalid ad status")


VALIDATORS = {
    "playbook": _playbook,
    "hook-library": _hook,
    "creators": _creator,
    "ad-swipe": _ad,
}


def read_jsonl(path: pathlib.Path) -> list[dict]:
    path = pathlib.Path(path)
    payload = path.read_bytes()
    _require(not payload.startswith(b"\xef\xbb\xbf"), f"BOM forbidden: {path}")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StoreError(f"not UTF-8: {path}") from exc
    if payload:
        _require(payload.endswith(b"\n"), f"final newline required: {path}")
    rows = []
    for line_no, line in enumerate(text.splitlines(), 1):
        _require(bool(line.strip()), f"blank line forbidden at {path}:{line_no}")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise StoreError(f"invalid JSON at {path}:{line_no}") from exc
        _require(isinstance(row, dict), f"record must be object at {path}:{line_no}")
        rows.append(row)
    return rows


def validate_store(path: pathlib.Path, store_name: str) -> dict:
    _require(store_name in STORES, f"unknown store {store_name}")
    rows = read_jsonl(path)
    seen = set()
    for line_no, row in enumerate(rows, 1):
        try:
            VALIDATORS[store_name](row)
        except StoreError as exc:
            raise StoreError(f"{path}:{line_no}: {exc}") from exc
        _require(row["id"] not in seen, f"duplicate id {row['id']} in {path}")
        seen.add(row["id"])
    payload = pathlib.Path(path).read_bytes()
    return {"count": len(rows), "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}


def validate_all(root: pathlib.Path) -> dict:
    root = pathlib.Path(root)
    stores = {}
    counts = {}
    for name, filename in STORES.items():
        stores[name] = validate_store(root / filename, name)
        counts[name] = stores[name]["count"]
    return {
        "schema_version": "marketing.intel-verification.v1",
        "passed": True,
        "counts": counts,
        "stores": stores,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path(__file__).parent)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        result = validate_all(args.root)
    except (OSError, StoreError) as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    rendered = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
