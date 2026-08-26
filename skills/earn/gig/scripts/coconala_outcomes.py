#!/usr/bin/env python3
"""Summarize Coconala business receipts without exposing customer or account data."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path.home() / "gig"


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _receipt(receipt_id: str, count: int, evidence: dict[str, Any], *, waiting: str) -> dict[str, Any]:
    digest = hashlib.sha256(
        json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "receipt_id": receipt_id,
        "state": "proven" if count > 0 else "waiting",
        "verified_count": count,
        "evidence_sha256": digest if count > 0 else None,
        "waiting_for": None if count > 0 else waiting,
    }


def outcomes(root: Path = ROOT) -> dict[str, Any]:
    applications = [
        row for row in _jsonl(root / "applied.jsonl")
        if row.get("status") == "applied" and row.get("submit_verified") is True
        and row.get("applied_page_verified") is True
    ]
    application = _receipt(
        "application", len(applications), {"count": len(applications), "latest": applications[-1].get("ts") if applications else None},
        waiting="official application readback",
    )

    replied = 0
    database = root / "connector-outbox.sqlite3"
    if database.is_file():
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
            replied = int(connection.execute(
                """SELECT COUNT(*) FROM connector_actions
                   WHERE state='replied' AND verified_outgoing_hash IS NOT NULL
                     AND seller_sent_at > 0 AND dlq_at IS NULL"""
            ).fetchone()[0])
    negotiation = _receipt(
        "negotiation", replied, {"verified_replies": replied},
        waiting="official seller reply or estimate readback",
    )

    storefront_rows = _jsonl(root / "storefront-direct" / "wakes.jsonl")
    storefront_count = sum(
        int(row.get("effect") or 0) > 0 and int(row.get("readback") or 0) > 0
        and int(row.get("duplicate") or 0) == 0 for row in storefront_rows
    )
    listing = _receipt(
        "listing", storefront_count, {"verified_mutations": storefront_count},
        waiting="official listing create or update readback",
    )

    paid = _json(root / "evidence" / "paid-direct-live" / "latest.json")
    completed_items = sum(
        row.get("status") == "completed"
        and (row.get("send_performed") is True or row.get("deduplicated") is True)
        for row in paid.get("items", []) if isinstance(row, dict)
    )
    paid_count = min(completed_items, int(paid.get("readback") or 0))
    delivery = _receipt(
        "delivery", paid_count, {"verified_deliveries": paid_count},
        waiting="official paid delivery readback",
    )

    bank = _receipt(
        "bank_arrival", 0, {}, waiting="bank-owned arrival receipt (payout request is not arrival)",
    )
    receipts = [application, negotiation, listing, delivery, bank]
    return {
        "status": "ready" if all(row["state"] == "proven" for row in receipts) else "waiting",
        "receipts": receipts,
    }


def main() -> int:
    print(json.dumps(outcomes(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
