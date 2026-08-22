#!/usr/bin/env python3
"""Read authenticated Upwork zero-spend state through the existing CloakBrowser CDP helper."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from cdp_nav_snapshot import navigate_and_snapshot  # noqa: E402


CONNECTS_URL = "https://www.upwork.com/nx/plans/connects/history"
INVITES_URL = "https://www.upwork.com/nx/find-work/invites"
PROPOSALS_URL = "https://www.upwork.com/nx/proposals/"
CATALOG_URL = "https://www.upwork.com/nx/project-dashboard/?step=approved"
CONTRACTS_URL = "https://www.upwork.com/nx/wm/freelancer/home"
MESSAGES_URL = "https://www.upwork.com/ab/messages/rooms/"
_COUNT_LABELS = {
    "offers": r"Offers\s*\((\d+)\)",
    "invites": r"Invites from clients\s*\((\d+)\)",
    "active_proposals": r"Active proposals\s*\((\d+)\)",
    "submitted_proposals": r"Submitted proposals\s*\((\d+)\)",
}


def parse_connects(text: str) -> dict[str, Any]:
    match = re.search(r"My balance\s+(\d+)\s+Connects\b", text or "", re.IGNORECASE)
    if match is None:
        raise ValueError("upwork_readback_incomplete")
    return {
        "balance": int(match.group(1)),
        "transactions_empty": "No Connects transactions." in text,
    }


def parse_inventory(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field, pattern in _COUNT_LABELS.items():
        match = re.search(pattern, text or "", re.IGNORECASE)
        if match is None:
            raise ValueError("upwork_readback_incomplete")
        result[field] = int(match.group(1))
    tasks: list[str] = []
    if re.search(r"Take the working style assessment", text, re.IGNORECASE):
        tasks.append("working_style_assessment")
    result["account_tasks"] = tasks
    return result


def parse_catalog(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field, label in (
        ("catalog_approved", "Approved"),
        ("catalog_under_review", "Under Review"),
        ("catalog_drafts", "Drafts"),
    ):
        match = re.search(rf"{label}\s*\((\d+)\)", text or "", re.IGNORECASE)
        if match is None:
            raise ValueError("upwork_readback_incomplete")
        result[field] = int(match.group(1))
    projects = []
    for match in re.finditer(
        r"Visible\s+([^\n]+)\s+(\d+)\s+(\d+)\s+More Project Options",
        text or "", re.IGNORECASE,
    ):
        projects.append({
            "title": match.group(1).strip(),
            "visible": True,
            "views_30d": int(match.group(2)),
            "orders": int(match.group(3)),
        })
    if result["catalog_approved"] and not projects:
        raise ValueError("upwork_readback_incomplete")
    result["catalog_projects"] = projects
    return result


def _stable_link(link: dict[str, Any]) -> dict[str, str] | None:
    href = str(link.get("href") or "")
    match = re.search(r"/jobs/(?:[^/?#]*-)?(~[A-Za-z0-9]+)(?:[/?#]|$)", href)
    if match is None:
        match = re.search(
            r"/(?:proposals|workroom|rooms)/([^/?#]+)(?:[/?#]|$)", href,
        )
    if match is None or match.group(1).lower() in {"archived", "referrals"}:
        return None
    return {
        "id": match.group(1),
        "href": href.split("?", 1)[0],
        "title": str(link.get("text") or "").strip(),
    }


def _dedupe_links(links: list[dict[str, Any]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for link in links:
        entity = _stable_link(link)
        if entity is None:
            continue
        key = (entity["id"], entity["href"])
        if key not in seen:
            seen.add(key)
            result.append(entity)
    return result


def parse_stable_entities(
    *, invite_links: list[dict[str, Any]], proposal_links: list[dict[str, Any]],
) -> dict[str, Any]:
    invitations = _dedupe_links(invite_links)
    offers: list[dict[str, str]] = []
    proposals: list[dict[str, str]] = []
    for link in proposal_links:
        entity = _stable_link(link)
        if entity is None:
            continue
        context = " ".join(str(link.get(key) or "") for key in (
            "context", "text", "aria", "data_qa", "class_name",
        )).lower()
        target = offers if "offer" in context else proposals
        if entity not in target:
            target.append(entity)
    return {
        "invitation_entities": invitations,
        "proposal_offer_entities": offers,
        "proposal_entities": proposals,
    }


def parse_contracts(text: str, links: list[dict[str, Any]]) -> dict[str, Any]:
    match = re.search(r"Earnings available now:\s*\$([\d,]+\.\d{2})", text or "")
    if match is None:
        raise ValueError("upwork_readback_incomplete")
    contracts = [
        item for item in _dedupe_links(links)
        if "/workroom/" in item["href"] or "contract" in item["href"].lower()
    ]
    if "There are no active contracts." not in text and not contracts:
        raise ValueError("upwork_readback_incomplete")
    return {
        "earnings_available_usd_minor": int(
            Decimal(match.group(1).replace(",", "")) * 100
        ),
        "active_contracts": contracts,
    }


def parse_messages(text: str, links: list[dict[str, Any]]) -> dict[str, Any]:
    rooms = [
        item for item in _dedupe_links(links)
        if "/ab/messages/rooms/" in item["href"]
    ]
    if "Conversations will appear here" not in text and not rooms:
        raise ValueError("upwork_readback_incomplete")
    unread = []
    for link in links:
        entity = _stable_link(link)
        marker = " ".join(str(link.get(key) or "") for key in (
            "context", "aria", "data_qa", "class_name",
        )).lower()
        if entity and "/ab/messages/rooms/" in entity["href"] and "unread" in marker:
            unread.append(entity["id"])
    return {"message_rooms": rooms, "unread_message_room_ids": sorted(set(unread))}


def _read_evidence(path: Path, expected_url: str) -> tuple[str, str, list[dict[str, Any]]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("navigated_ok") is not True or value.get("url") != expected_url:
        raise ValueError("upwork_readback_incomplete")
    text = value.get("rendered_text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("upwork_readback_incomplete")
    links = value.get("rendered_links", [])
    if not isinstance(links, list):
        raise ValueError("upwork_readback_incomplete")
    return text, hashlib.sha256(path.read_bytes()).hexdigest(), links


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


async def observe(output: Path) -> dict[str, Any]:
    pass_id = f"upwork-free-{int(time.time())}"
    artifacts: dict[str, str] = {}
    pages: dict[str, str] = {}
    links: dict[str, list[dict[str, Any]]] = {}
    for sequence, (label, url) in enumerate((
        ("connects", CONNECTS_URL), ("invites", INVITES_URL),
        ("proposals", PROPOSALS_URL), ("catalog", CATALOG_URL),
        ("contracts", CONTRACTS_URL), ("messages", MESSAGES_URL),
    ), start=1):
        for attempt in range(1, 4):
            artifact = Path(await navigate_and_snapshot(
                pass_id, f"{sequence:02d}-{attempt}", label, url, "read_only", 2,
                1440,
            ))
            try:
                pages[label], artifacts[label], links[label] = _read_evidence(artifact, url)
                break
            except ValueError:
                if attempt == 3:
                    raise
                await asyncio.sleep(attempt)
    state = {
        "version": 1,
        "provider": "upwork",
        "mode": "zero_spend",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        **parse_connects(pages["connects"]),
        **parse_inventory(pages["proposals"] + "\n" + pages["invites"]),
        **parse_stable_entities(
            invite_links=links["invites"], proposal_links=links["proposals"],
        ),
        **parse_catalog(pages["catalog"]),
        **parse_contracts(pages["contracts"], links["contracts"]),
        **parse_messages(pages["messages"], links["messages"]),
        "evidence_sha256": artifacts,
    }
    state["can_submit_public_job"] = state["balance"] > 0
    _atomic_write(output, state)
    return state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cdp-base", default="http://127.0.0.1:9233")
    parser.add_argument(
        "--output", type=Path,
        default=Path(os.path.expanduser("~/gig/state/upwork-free-loop.json")),
    )
    args = parser.parse_args()
    os.environ["CLOAK_CDP_BASE_URL"] = args.cdp_base.rstrip("/")
    state = asyncio.run(observe(args.output.expanduser()))
    print(json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
