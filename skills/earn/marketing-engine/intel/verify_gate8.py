#!/usr/bin/env python3
"""Fail-closed verifier for the completed Gate 8 daily-intel contract."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re

from intel_store import read_jsonl, validate_all


X_STATUS = re.compile(r"^https://x\.com/[^/]+/status/[0-9]+$")


class Gate8Error(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Gate8Error(message)


def load_json(path: pathlib.Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"expected JSON object: {path}")
    return value


def validate_enrichments(path: pathlib.Path) -> dict:
    required = {
        "schema_version", "id", "tactic_id", "source_id", "item_id",
        "source_url", "captured_at", "evidence_path", "evidence_sha256",
    }
    rows = read_jsonl(path)
    ids: set[str] = set()
    for line_no, row in enumerate(rows, 1):
        require(set(row) == required, f"enrichment fields invalid at line {line_no}")
        require(row["schema_version"] == "marketing.source-enrichment.v1",
                f"enrichment schema invalid at line {line_no}")
        require(row["id"] not in ids, f"duplicate enrichment id {row['id']}")
        ids.add(row["id"])
        require(row["tactic_id"].startswith("tactic."),
                f"invalid tactic id at line {line_no}")
        require(row["item_id"].startswith("x:"), f"invalid item id at line {line_no}")
        require(X_STATUS.fullmatch(row["source_url"]) is not None,
                f"source URL is not an exact X status at line {line_no}")
        try:
            captured = dt.datetime.fromisoformat(row["captured_at"].replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise Gate8Error(f"captured_at invalid at line {line_no}") from exc
        require(captured.tzinfo is not None, f"captured_at timezone missing at line {line_no}")
        evidence = pathlib.Path(row["evidence_path"])
        require(evidence.is_file(), f"enrichment evidence missing at line {line_no}")
        actual = hashlib.sha256(evidence.read_bytes()).hexdigest()
        require(actual == row["evidence_sha256"], f"enrichment evidence hash mismatch at line {line_no}")
    return {"count": len(rows), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _sha_file(path: pathlib.Path) -> dict[str, str]:
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, filename = line.split(maxsplit=1)
        rows[filename] = digest
    return rows


def verify_gate8(engine: pathlib.Path) -> dict:
    engine = pathlib.Path(engine)
    intel = engine / "intel"
    evidence = engine / "evidence"

    canonical = validate_all(intel)
    source_rows = read_jsonl(intel / "source-items.jsonl")
    judged_rows = read_jsonl(intel / "judged-items.jsonl")
    source_keys = {(row["source_id"], row["item_id"]) for row in source_rows}
    judged_keys = {(row["source_id"], row["item_id"]) for row in judged_rows}
    require(len(source_keys) == len(source_rows), "duplicate source items")
    require(len(judged_keys) == len(judged_rows), "duplicate judged items")
    require(source_keys == judged_keys, "source and judged item sets differ")
    require(len(source_rows) >= 75, "Gate 8 baseline of 75 source items not reached")
    enrichment = validate_enrichments(intel / "source-enrichments.jsonl")
    require(enrichment["count"] >= 11, "Gate 8 baseline of 11 source enrichments not reached")

    live_pull = load_json(evidence / "intel" / "pulls" /
                          "e736d6f93cef4c17bee50b6558617f81" / "run.json")
    adapters = {row["adapter"]: row["status"] for row in live_pull["sources"]}
    for adapter in ("x_articles", "rss", "github_repo", "github_search",
                    "apple_lookup", "apple_search"):
        require(adapters.get(adapter) in {"success", "unchanged"},
                f"required live adapter did not succeed: {adapter}")
    meta = next(row for row in live_pull["sources"] if row["adapter"] == "meta_ad_library")
    require(meta["status"] == "unavailable" and bool(meta["reason"]),
            "Meta unavailability must be explicit")

    rerun = load_json(evidence / "intel" / "gate8" / "rerun.stdout.json")
    require(rerun["new_source_items"] == 0 and rerun["pending_judgment"] == 0,
            "idempotent rerun produced work")
    require(all(value == 0 for value in rerun["accepted"].values()),
            "idempotent rerun appended canonical rows")
    before = _sha_file(evidence / "intel" / "gate8" / "before-rerun.sha256")
    after = _sha_file(evidence / "intel" / "gate8" / "after-rerun.sha256")
    require(before == after, "canonical hashes changed during idempotent rerun")

    schedule = load_json(evidence / "schedulers" / "2026-08-01-gate8-readback-plan.json")
    require(schedule["daily"]["would_change"] is False, "daily schedule readback differs")
    require(schedule["weekly"]["would_change"] is False, "weekly schedule readback differs")
    require(schedule["weekly"]["program_arguments"][-3:] == ["intel", "gap", "--telegram"],
            "weekly schedule is not wired to lm intel gap --telegram")

    weekly = load_json(evidence / "intel" / "gaps" /
                       "739d8f8b87d74a608b25f9dceaea9a23.json")
    daily = load_json(evidence / "intel" / "gate8" / "scheduled-mine-live.stdout.json")
    require(weekly["telegram"]["status"] == "delivered", "weekly Telegram not delivered")
    require(daily["delivery"]["status"] == "delivered", "daily Telegram not delivered")

    return {
        "schema_version": "marketing.gate8-verification.v1",
        "passed": True,
        "source_pipeline": {
            "source_items": len(source_rows),
            "judged_items": len(judged_rows),
            "pending_items": len(source_keys - judged_keys),
            "enrichments": enrichment["count"],
        },
        "canonical_stores": canonical,
        "live_sources": {"adapters": adapters, "meta_reason": meta["reason"]},
        "idempotency": {"run_id": rerun["run_id"], "hashes_match": before == after},
        "schedules": {"daily": schedule["daily"], "weekly": schedule["weekly"]},
        "telegram": {
            "weekly_message_ids": weekly["telegram"]["message_ids"],
            "daily_message_ids": daily["delivery"]["message_ids"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=pathlib.Path,
                        default=pathlib.Path(__file__).resolve().parent.parent)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        result = verify_gate8(args.engine)
    except (OSError, ValueError, KeyError, StopIteration) as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    rendered = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
