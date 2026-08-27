#!/usr/bin/env python3
"""Render truthful open-intel gaps for the owner."""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import uuid


LANE_ORDER = ("app", "ebook", "content", "outreach")


def build_gap_report(playbook_rows, latest_run, enrichments=None):
    enrichment_urls = {}
    for row in enrichments or []:
        enrichment_urls.setdefault(row.get("tactic_id"), row.get("source_url"))
    open_rows = [
        row for row in playbook_rows
        if row.get("testable") is True and row.get("status") in {"new", "queued"}
    ]
    lines = [
        "🧠 MARKETING INTEL GAP",
        f"run={latest_run.get('run_id', 'none')} observed={latest_run.get('observed_at', 'unknown')}",
        f"open_tactics={len(open_rows)}",
    ]
    for lane in LANE_ORDER:
        lane_rows = [row for row in open_rows if lane in row.get("applies_to", [])]
        if not lane_rows:
            continue
        lines.extend(["", lane.upper()])
        for row in lane_rows:
            url = row.get("evidence_url") or row.get("source_url") or enrichment_urls.get(row.get("id"))
            if url:
                evidence = url
            else:
                reason = row.get("evidence_null_reason") or row.get("source_null_reason") or "not_captured"
                evidence = f"evidence unavailable: {reason}"
            lines.append(f"- {row['id']}: {row['claim']} — {evidence}")
    failures = [source for source in latest_run.get("sources", []) if source.get("status") in {"error", "unavailable"}]
    if failures:
        lines.extend(["", "SOURCE FAILURES"])
        for source in failures:
            lines.append(f"- {source['source_id']}: {source['status']} — {source.get('reason') or 'unspecified'}")
    return "\n".join(lines)


def latest_pull(path):
    path = pathlib.Path(path)
    if not path.exists() or not path.read_bytes():
        return {"run_id": "none", "observed_at": "unknown", "sources": []}
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows[-1]


def run_gap(*, playbook_rows, latest_run, evidence_root, sender=None, observed_at=None, enrichments=None):
    observed_at = observed_at or dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    report = build_gap_report(playbook_rows, latest_run, enrichments=enrichments)
    receipt = None
    if sender is not None:
        receipt = sender(report)
    result = {
        "schema_version": "marketing.intel-gap.v1",
        "gap_id": uuid.uuid4().hex,
        "observed_at": observed_at,
        "source_run_id": latest_run.get("run_id"),
        "open_tactics": sum(1 for row in playbook_rows if row.get("testable") is True and row.get("status") in {"new", "queued"}),
        "report": report,
        "telegram": receipt,
    }
    root = pathlib.Path(evidence_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{result['gap_id']}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    result["evidence_path"] = str(path)
    return result
