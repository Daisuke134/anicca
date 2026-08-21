#!/usr/bin/env python3
"""Validate and claim one Affiliate-owned Repost proposal without tracking URLs."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


PROPOSAL_ID = re.compile(r"^[0-9a-f]{64}$")
PLACEMENT_ID = re.compile(r"^[a-z0-9][a-z0-9-]{2,80}$")


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError("proposal unavailable") from error
    if not isinstance(value, dict):
        raise ValueError("proposal is not an object")
    return value


def valid(proposal: dict) -> bool:
    url = proposal.get("owned_article_url")
    parsed = urlparse(url) if isinstance(url, str) else None
    return all((
        proposal.get("receipt_type") == "AFFILIATE_REPOST_PROPOSAL",
        proposal.get("state") == "READY_FOR_EXISTING_REPOST_OWNER",
        isinstance(proposal.get("proposal_id"), str)
        and bool(PROPOSAL_ID.fullmatch(proposal["proposal_id"])),
        isinstance(proposal.get("placement_id"), str)
        and bool(PLACEMENT_ID.fullmatch(proposal["placement_id"])),
        proposal.get("language") == "en",
        proposal.get("disclosure_required") is True,
        proposal.get("tracking_link_state") == "NOT_INCLUDED",
        proposal.get("revenue_credit_state") == "NO_REVENUE_CREDIT",
        parsed is not None and parsed.scheme == "https"
        and parsed.hostname == "aniccaai.com" and parsed.path.startswith("/blog/"),
    ))


def rows(path: Path) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    values = []
    for line in lines:
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            values.append(value)
    return values


def select(proposal_path: Path, consumed_path: Path) -> dict:
    try:
        proposal = read_json(proposal_path)
    except ValueError:
        return {"state": "NO_PROPOSAL"}
    if not valid(proposal):
        return {"state": "INVALID_PROPOSAL"}
    if any(row.get("proposal_id") == proposal["proposal_id"] for row in rows(consumed_path)):
        return {"state": "ALREADY_CONSUMED", "proposal_id": proposal["proposal_id"]}
    return {
        "state": "READY",
        "proposal_id": proposal["proposal_id"],
        "placement_id": proposal["placement_id"],
        "owned_article_url": proposal["owned_article_url"],
        "language": "en",
    }


def record(consumed_path: Path, proposal: dict, state: str, post_url: str | None) -> dict:
    if state not in {"POSTED", "UNVERIFIED"}:
        raise ValueError("invalid consumption state")
    if not valid(proposal):
        raise ValueError("invalid proposal")
    existing = next((row for row in rows(consumed_path)
                     if row.get("proposal_id") == proposal["proposal_id"]), None)
    if existing is not None:
        return {**existing, "changed": False}
    if state == "POSTED":
        parsed = urlparse(post_url or "")
        if parsed.hostname != "x.com" or not re.fullmatch(r"/[A-Za-z0-9_]+/status/[0-9]+", parsed.path):
            raise ValueError("invalid published X URL")
    row = {
        "schema_version": 1,
        "receipt_type": "X_REPOST_AFFILIATE_PROPOSAL_CONSUMPTION",
        "proposal_id": proposal["proposal_id"],
        "placement_id": proposal["placement_id"],
        "state": state,
        "post_url": post_url if state == "POSTED" else None,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "revenue_credit_state": "NO_REVENUE_CREDIT_UNTIL_EXACT_AFFILIATE_JOIN",
    }
    consumed_path.parent.mkdir(parents=True, exist_ok=True)
    with consumed_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return {**row, "changed": True}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--consumed", type=Path, required=True)
    parser.add_argument("--record", choices=("POSTED", "UNVERIFIED"))
    parser.add_argument("--post-url")
    args = parser.parse_args()
    if not args.record:
        print(json.dumps(select(args.proposal, args.consumed), sort_keys=True))
        return 0
    proposal = read_json(args.proposal)
    print(json.dumps(record(args.consumed, proposal, args.record, args.post_url), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"affiliate proposal: {error}", file=sys.stderr)
        raise SystemExit(2)
