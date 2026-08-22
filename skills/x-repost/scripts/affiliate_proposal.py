#!/usr/bin/env python3
"""Validate and claim one Affiliate-owned Repost proposal without tracking URLs."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse


PROPOSAL_ID = re.compile(r"^[0-9a-f]{64}$")
PLACEMENT_ID = re.compile(r"^[a-z0-9][a-z0-9-]{2,80}$")
CONSUMPTION_STATES = {"EFFECT_STARTED", "POSTED", "UNVERIFIED", "NO_EFFECT"}
SAFE_FIELDS = (
    "receipt_type", "state", "proposal_id", "placement_id", "owned_article_url",
    "language", "disclosure_required", "tracking_link_state", "revenue_credit_state",
    "article_title", "buyer_intent",
)
X_TRANSFORMED_URL_LENGTH = 23
UNVERIFIED_RECOVERY_WINDOW = timedelta(hours=6)
URL = re.compile(r"https?://\S+")


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError("proposal unavailable") from error
    if not isinstance(value, dict):
        raise ValueError("proposal is not an object")
    return value


def valid(proposal: dict) -> bool:
    if not isinstance(proposal, dict):
        return False
    url = proposal.get("owned_article_url")
    if not isinstance(url, str) or any(char.isspace() or ord(char) < 32 for char in url):
        return False
    for field in ("article_title", "buyer_intent"):
        value = proposal.get(field)
        if value is not None and (
            not isinstance(value, str) or not 0 < len(value) <= 240
            or any(char in value for char in "\r\n")
            or "http" in value.casefold()
        ):
            return False
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError:
        return False
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
        parsed.scheme == "https"
        and parsed.hostname == "aniccaai.com"
        and bool(re.fullmatch(r"/blog/[a-z0-9][a-z0-9-]*", parsed.path))
        and not parsed.username and not parsed.password and port is None
        and not parsed.query and not parsed.fragment
    ))


def canonical(proposal: dict) -> dict:
    if not valid(proposal):
        raise ValueError("invalid proposal")
    return {field: proposal.get(field) for field in SAFE_FIELDS}


def post_text(proposal: dict) -> str:
    proposal = canonical(proposal)
    url = proposal["owned_article_url"]
    disclosure = "Affiliate disclosure: I may earn a commission if you subscribe through this link."
    intent = " ".join((proposal.get("buyer_intent") or "").split())
    title = " ".join((proposal.get("article_title") or "").split())
    match = re.fullmatch(r"Creators evaluating (.+?) before paying", intent, re.I)
    product = match.group(1).strip() if match else ""
    if not product:
        product = re.sub(r"^(?:Is|How to Evaluate)\s+", "", title, flags=re.I)
        product = re.split(r"(?:\?|:|\s+(?:a|the)\s+(?:right\s+)?fit\b|\s+before\b)", product,
                           maxsplit=1, flags=re.I)[0].strip()

    # Never slice prose to fit. The old renderer cut both the hook and title in the middle of
    # words, producing visibly broken public posts. Try complete-sentence variants and fall back
    # to a truthful generic noun when a provider-supplied product label is unusually long.
    for subject in (product, "this AI tool"):
        if not subject:
            continue
        text = (
            f"Considering {subject}? Check workflow fit, limits, and total price before you "
            f"subscribe. Use this decision checklist to compare the trade-offs.\n\n"
            f"{disclosure}\n{url}"
        )
        # Match twitter/twitter-text v3: each extracted URL contributes the
        # transformed URL length (23), not its raw display length.
        weighted_length = len(URL.sub("x" * X_TRANSFORMED_URL_LENGTH, text))
        if weighted_length <= 280:
            return text
    raise ValueError("affiliate proposal copy exceeds X limit")


def rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ValueError("consumption ledger unavailable") from error
    values = []
    for line in lines:
        try:
            value = json.loads(line)
        except ValueError as error:
            raise ValueError("consumption ledger invalid") from error
        if not isinstance(value, dict):
            raise ValueError("consumption ledger invalid")
        if (
            value.get("schema_version") != 1
            or value.get("receipt_type") != "X_REPOST_AFFILIATE_PROPOSAL_CONSUMPTION"
            or not isinstance(value.get("proposal_id"), str)
            or not PROPOSAL_ID.fullmatch(value["proposal_id"])
            or not isinstance(value.get("placement_id"), str)
            or not PLACEMENT_ID.fullmatch(value["placement_id"])
            or value.get("state") not in CONSUMPTION_STATES
            or not isinstance(value.get("observed_at"), str)
        ):
            raise ValueError("consumption ledger invalid")
        try:
            observed = datetime.fromisoformat(value["observed_at"].replace("Z", "+00:00"))
            if observed.tzinfo is None:
                raise ValueError
        except ValueError as error:
            raise ValueError("consumption ledger invalid") from error
        values.append(value)
    return values


def select(proposal_path: Path, consumed_path: Path, posted_path: Path | None = None) -> dict:
    try:
        all_rows = rows(consumed_path)
    except ValueError:
        return {"state": "BLOCKED_CONSUMPTION_LEDGER"}
    latest_by_proposal = {}
    for row in all_rows:
        proposal_id = row.get("proposal_id")
        if isinstance(proposal_id, str):
            latest_by_proposal[proposal_id] = row
    posted_ids = set()
    if posted_path is not None and posted_path.exists():
        try:
            for line in posted_path.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                proposal_id = row.get("affiliate_proposal_id")
                if isinstance(proposal_id, str):
                    posted_ids.add(proposal_id)
        except (OSError, ValueError, AttributeError):
            return {"state": "BLOCKED_CONSUMPTION_LEDGER"}
    legacy = [row for row in latest_by_proposal.values()
              if row.get("state") == "EFFECT_STARTED" and not valid(row.get("proposal"))]
    if legacy:
        return {"state": "BLOCKED_LEGACY_CLAIM"}
    unresolved = [row for row in latest_by_proposal.values()
                  if row.get("state") == "EFFECT_STARTED"]
    if unresolved:
        pending = min(unresolved, key=lambda row: row.get("observed_at", ""))
        snapshot = pending["proposal"]
        return {
            "state": "RECONCILE",
            "proposal": canonical(snapshot),
            "proposal_id": snapshot["proposal_id"],
            "placement_id": snapshot["placement_id"],
            "owned_article_url": snapshot["owned_article_url"],
            "language": "en",
        }
    try:
        proposal = read_json(proposal_path)
    except ValueError:
        proposal = None
    if proposal is not None and not valid(proposal):
        return {"state": "INVALID_PROPOSAL"}
    prior = [row for row in all_rows
             if proposal is not None and row.get("proposal_id") == proposal["proposal_id"]]
    if proposal is not None and not prior:
        return {
            "state": "READY",
            "proposal": canonical(proposal),
            "proposal_id": proposal["proposal_id"],
            "placement_id": proposal["placement_id"],
            "owned_article_url": proposal["owned_article_url"],
            "language": "en",
        }
    recoverable = []
    now = datetime.now(timezone.utc)
    for proposal_id, terminal in latest_by_proposal.items():
        if terminal.get("state") != "UNVERIFIED" or proposal_id in posted_ids:
            continue
        terminal_at = datetime.fromisoformat(terminal["observed_at"].replace("Z", "+00:00"))
        if now - terminal_at.astimezone(timezone.utc) > UNVERIFIED_RECOVERY_WINDOW:
            continue
        claim_row = next((row for row in reversed(all_rows)
                          if row.get("proposal_id") == proposal_id
                          and row.get("state") == "EFFECT_STARTED"
                          and valid(row.get("proposal"))), None)
        if claim_row:
            recoverable.append(claim_row)
    if recoverable:
        pending = max(recoverable, key=lambda row: row.get("observed_at", ""))
        snapshot = pending["proposal"]
        return {
            "state": "VERIFY_UNVERIFIED",
            "proposal": canonical(snapshot),
            "proposal_id": snapshot["proposal_id"],
            "placement_id": snapshot["placement_id"],
            "owned_article_url": snapshot["owned_article_url"],
            "language": "en",
        }
    if proposal is None:
        return {"state": "NO_PROPOSAL"}
    if any(row.get("state") in {"POSTED", "UNVERIFIED", "NO_EFFECT"} for row in prior):
        return {"state": "ALREADY_CONSUMED", "proposal_id": proposal["proposal_id"]}
    if any(row.get("state") == "EFFECT_STARTED" for row in prior):
        return {
            "state": "RECONCILE",
            "proposal_id": proposal["proposal_id"],
            "placement_id": proposal["placement_id"],
            "owned_article_url": proposal["owned_article_url"],
            "language": "en",
        }
    return {"state": "BLOCKED_CONSUMPTION_LEDGER"}


def _append_once(consumed_path: Path, proposal_id: str, row: dict, *, require_claim: bool) -> dict:
    consumed_path.parent.mkdir(parents=True, exist_ok=True)
    with consumed_path.open("a+", encoding="utf-8") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.seek(0)
        prior = []
        for line in stream:
            try:
                value = json.loads(line)
            except ValueError as error:
                raise ValueError("consumption ledger invalid") from error
            if not isinstance(value, dict):
                raise ValueError("consumption ledger invalid")
            if value.get("proposal_id") == proposal_id:
                prior.append(value)
        terminal = next((value for value in reversed(prior)
                         if value.get("state") in {"POSTED", "UNVERIFIED", "NO_EFFECT"}), None)
        if terminal is not None:
            return {**terminal, "changed": False}
        if require_claim and not any(value.get("state") == "EFFECT_STARTED" for value in prior):
            raise ValueError("proposal was not claimed")
        if not require_claim and prior:
            return {**prior[-1], "changed": False}
        stream.seek(0, os.SEEK_END)
        stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return {**row, "changed": True}


def claim(consumed_path: Path, proposal: dict) -> dict:
    if not valid(proposal):
        raise ValueError("invalid proposal")
    row = {
        "schema_version": 1,
        "receipt_type": "X_REPOST_AFFILIATE_PROPOSAL_CONSUMPTION",
        "proposal_id": proposal["proposal_id"],
        "placement_id": proposal["placement_id"],
        "state": "EFFECT_STARTED",
        "proposal": canonical(proposal),
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "revenue_credit_state": "NO_REVENUE_CREDIT_UNTIL_EXACT_AFFILIATE_JOIN",
    }
    return _append_once(consumed_path, proposal["proposal_id"], row, require_claim=False)


def record(consumed_path: Path, proposal: dict, state: str, post_url: str | None) -> dict:
    if state not in {"POSTED", "UNVERIFIED", "NO_EFFECT"}:
        raise ValueError("invalid consumption state")
    if not valid(proposal):
        raise ValueError("invalid proposal")
    if state == "POSTED":
        if not isinstance(post_url, str) or any(char.isspace() or ord(char) < 32 for char in post_url):
            raise ValueError("invalid published X URL")
        try:
            parsed = urlparse(post_url)
            port = parsed.port
        except ValueError:
            raise ValueError("invalid published X URL")
        if not (
            parsed.scheme == "https" and parsed.hostname == "x.com"
            and not parsed.username and not parsed.password and port is None
            and not parsed.query and not parsed.fragment
            and re.fullmatch(r"/[A-Za-z0-9_]+/status/[0-9]+", parsed.path)
        ):
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
    return _append_once(consumed_path, proposal["proposal_id"], row, require_claim=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--consumed", type=Path, required=True)
    parser.add_argument("--posted", type=Path)
    parser.add_argument("--record", choices=("POSTED", "UNVERIFIED", "NO_EFFECT"))
    parser.add_argument("--claim", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--post-url")
    args = parser.parse_args()
    if args.claim:
        print(json.dumps(claim(args.consumed, read_json(args.proposal)), sort_keys=True))
        return 0
    if args.render:
        print(post_text(read_json(args.proposal)), end="")
        return 0
    if not args.record:
        print(json.dumps(select(args.proposal, args.consumed, args.posted), sort_keys=True))
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
