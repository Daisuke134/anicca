#!/usr/bin/env python3
"""Build an evidence-first investigation receipt for one UNKNOWN Writer incident."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any


def _read(path: Path, schema: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != schema or value.get("version") != 1:
        raise ValueError(f"unsupported {schema}")
    return value


def _jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _pair(phase: str) -> tuple[str, str] | None:
    if not phase.startswith("destination:"):
        return None
    platform, lang = phase.removeprefix("destination:").split("/", 1)
    return platform, lang


def _last_good(state_dir: Path, phase: str, bad_run_id: str) -> dict[str, Any] | None:
    pair = _pair(phase)
    if pair is None:
        return None
    platform, lang = pair
    aliases = {"x-article": "x", "zenn-article": "zenn"}
    candidates = []
    for row in _jsonl(state_dir / "articles.jsonl"):
        row_platform = str(row.get("platform") or "")
        platform_match = row_platform in {platform, aliases.get(platform, platform)}
        if (
            platform_match and str(row.get("lang") or row.get("language")) == lang
            and row.get("published") is True and row.get("live_url")
            and str(row.get("run_id")) != bad_run_id
        ):
            candidates.append(row)
    if not candidates:
        return None
    row = max(candidates, key=lambda value: str(value.get("published_at") or value.get("ts") or ""))
    run_id = str(row.get("run_id"))
    git_hash = state_dir / "runs" / run_id / "git-hash.txt"
    return {
        "run_id": run_id,
        "live_url": row.get("live_url"),
        "published_at": row.get("published_at") or row.get("ts"),
        "artifact_sha256": row.get("artifact_sha256"),
        "release_receipt": (
            {"path": str(git_hash), "sha256": hashlib.sha256(git_hash.read_bytes()).hexdigest()}
            if git_hash.is_file() else None
        ),
    }


def investigate(
    queue: dict[str, Any], fingerprint: str, evidence: dict[str, Any],
    state_dir: Path, observed_at: str, primary_research_path: Path | None = None,
    preexisting_effect_path: Path | None = None,
) -> dict[str, Any]:
    item = queue.get("items", {}).get(fingerprint)
    if not isinstance(item, dict) or item.get("state") != "CLAIMED":
        raise ValueError("UNKNOWN investigation requires a CLAIMED incident")
    # The incident's recorded `run_id` wins over parsing an execution id: a
    # worker label such as `publisher-repair:daily-2026-08-07` is not a run id.
    run_id = str(item.get("run_id") or "")
    if not run_id:
        occurrences = item.get("occurrences") or []
        execution_id = str(occurrences[-1].get("execution_id") or "") if occurrences else ""
        run_id = (
            execution_id.removeprefix("publisher-")
            if execution_id.startswith("publisher-") else ""
        )
    if not run_id:
        raise ValueError("latest occurrence is not bound to a publisher run")
    if evidence.get("run_id") != run_id:
        raise ValueError("evidence index run does not match incident occurrence")
    matched = next(
        (
            row for row in evidence.get("incidents", [])
            if row.get("phase") == item.get("phase") and row.get("reason") == item.get("reason")
        ),
        None,
    )
    if not isinstance(matched, dict):
        raise ValueError("incident is absent from evidence index")
    browser = matched.get("browser_evidence") or []
    safe_logs = matched.get("safe_logs") or []
    gaps = []
    if not browser:
        gaps.append("browser_evidence_missing")
    if not safe_logs:
        gaps.append("safe_log_missing")
    primary_research = None
    if primary_research_path is None:
        gaps.append("official_primary_document_research_required")
    else:
        if primary_research_path.is_symlink() or not primary_research_path.is_file():
            raise ValueError("primary research receipt is required")
        research = _read(primary_research_path, "writer.self-heal.primary-research")
        sources = research.get("sources")
        if not isinstance(sources, list) or not sources:
            raise ValueError("primary research requires at least one source")
        for source in sources:
            if (
                not isinstance(source, dict)
                or not str(source.get("url") or "").startswith("https://")
                or not str(source.get("title") or "").strip()
                or not str(source.get("quote") or "").strip()
            ):
                raise ValueError("primary research source requires https URL, title, and quote")
        primary_research = {
            "path": str(primary_research_path.resolve()),
            "sha256": hashlib.sha256(primary_research_path.read_bytes()).hexdigest(),
            "sources": sources,
            "finding": research.get("finding"),
        }
    last_good = _last_good(state_dir, str(item["phase"]), run_id)
    if last_good is None:
        gaps.append("last_good_destination_receipt_missing")
    preexisting_effect = None
    if preexisting_effect_path is not None:
        if preexisting_effect_path.is_symlink() or not preexisting_effect_path.is_file():
            raise ValueError("preexisting effect receipt is required")
        effect = _read(preexisting_effect_path, "writer.self-heal.preexisting-effect")
        if effect.get("effect_kind") != "draft" or effect.get("public") is not False:
            raise ValueError("preexisting effect must be a non-public draft")
        try:
            effect_at = datetime.fromisoformat(str(effect["effect_at"]))
            failure_at = datetime.fromisoformat(str(effect["failure_at"]))
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("preexisting effect timestamps are invalid") from error
        if effect_at >= failure_at:
            raise ValueError("preexisting effect must precede the classified failure")
        receipts = effect.get("effect_receipts")
        if not isinstance(receipts, list) or not receipts:
            raise ValueError("preexisting effect requires effect receipts")
        for receipt in receipts:
            if (
                not isinstance(receipt, dict)
                or not str(receipt.get("kind") or "").strip()
                or not str(receipt.get("value") or "").strip()
                or len(str(receipt.get("sha256") or "")) != 64
            ):
                raise ValueError("preexisting effect receipt is malformed")
        preexisting_effect = {
            "path": str(preexisting_effect_path.resolve()),
            "sha256": hashlib.sha256(preexisting_effect_path.read_bytes()).hexdigest(),
            "effect_at": effect["effect_at"],
            "failure_at": effect["failure_at"],
            "effect_kind": effect["effect_kind"],
            "target": effect.get("target"),
            "public": effect["public"],
            "effect_receipts": receipts,
        }
    result = {
        "schema": "writer.self-heal.unknown-investigation",
        "version": 1,
        "observed_at": observed_at,
        "fingerprint": fingerprint,
        "run_id": run_id,
        "phase": item["phase"],
        "observed_reason": item["reason"],
        "classification": item["classification"],
        "first_bad": {
            "trace_id": matched.get("trace_id"),
            "span_id": matched.get("span_id"),
            "source_receipt": matched.get("source_receipt"),
            "source_release": matched.get("source_release"),
            "safe_logs": safe_logs,
            "browser_evidence": browser,
        },
        "last_good": last_good,
        "evidence_gaps": gaps,
        "cause_status": "UNDETERMINED",
        "next_action": "COLLECT_GAPS_THEN_SEARCH_OFFICIAL_PRIMARY_DOCS",
    }
    if primary_research is not None:
        result["primary_research"] = primary_research
    if preexisting_effect is not None:
        result["preexisting_effect"] = preexisting_effect
        result["cause_status"] = "EVIDENCE_BACKED_HYPOTHESIS"
        result["cause_hypothesis"] = (
            "preexisting_draft_was_not_reconciled_before_timeout_classification"
        )
        result["next_action"] = "CHARACTERIZE_PREEXISTING_EFFECT_RECONCILIATION"
    return result


def _atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", required=True, type=Path)
    parser.add_argument("--fingerprint", required=True)
    parser.add_argument("--evidence-index", required=True, type=Path)
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--primary-research-receipt", type=Path)
    parser.add_argument("--preexisting-effect-receipt", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    queue = _read(args.queue, "writer.self-heal.incident-queue")
    evidence = _read(args.evidence_index, "writer.observability.evidence-index")
    value = investigate(
        queue, args.fingerprint, evidence, args.state_dir.resolve(), args.observed_at,
        args.primary_research_receipt, args.preexisting_effect_receipt,
    )
    _atomic(args.out, value)
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
