#!/usr/bin/env python3
"""Bind one unconsumed claim to one immutable Writer Agent topic card."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from claim_store import ClaimStore, _text, _timestamp  # noqa: E402
from topic_router import TopicRouteError, route_topic  # noqa: E402


def _render_card(
    claim: dict[str, Any] | None,
    proposal: dict[str, Any],
    *,
    created_at: str,
    demand_mode: str = "legacy-migration",
) -> bytes:
    title = _text(proposal.get("title"), "title")
    angle = _text(proposal.get("angle"), "angle")
    priority = proposal.get("priority", 10)
    if not isinstance(priority, int) or isinstance(priority, bool):
        raise ValueError("priority must be an integer")
    required_demand = demand_mode == "required"
    claim_id = str(claim["claim_id"]) if claim is not None else None
    if not required_demand:
        if claim is None:
            raise ValueError("legacy topic requires a durable claim")
        if proposal.get("claim_id") != claim_id:
            raise ValueError("proposal claim_id does not match the durable claim")
    reader = proposal.get("reader")
    if not isinstance(reader, dict):
        raise ValueError("proposal reader must be an object")
    if not required_demand and claim is not None and reader.get("job") != claim["reader_job"]:
        raise ValueError("proposal reader.job must equal the durable claim reader_job")
    evidence_plan = proposal.get("evidence_plan")
    if not isinstance(evidence_plan, list):
        raise ValueError("evidence_plan must be a list")
    refs = [
        row.get("ref") for row in evidence_plan
        if isinstance(row, dict) and isinstance(row.get("ref"), str)
    ]
    if not required_demand and claim is not None and claim["canonical_url"] not in refs:
        raise ValueError("evidence_plan must cite the canonical claim source")
    if required_demand:
        topic_id = _text(proposal.get("topic_id"), "topic_id")
        if not topic_id.startswith("paid-demand:"):
            raise ValueError("required demand topic_id must be stable paid-demand identity")
    else:
        topic_id = f"claim:{claim_id}"
    route_input = {
        "topic_id": topic_id,
        "topic_source": proposal.get("topic_source"),
        "reader": reader,
        "evidence_plan": evidence_plan,
        "editorial_form": proposal.get("editorial_form"),
        "product_link": proposal.get("product_link"),
    }
    if "demand_card" in proposal:
        route_input["demand_card"] = proposal["demand_card"]
    try:
        routed = route_topic(route_input, demand_mode=demand_mode)
    except TopicRouteError as error:
        raise ValueError(f"invalid claim topic route: {error}") from error
    source_urls: list[str] = []
    for ref in refs:
        if ref.startswith("https://") and ref not in source_urls:
            source_urls.append(ref)
    frontmatter = {
        "created": created_at,
        "priority": priority,
        "form": "article",
        "topic_id": route_input["topic_id"],
        "topic_source": route_input["topic_source"],
        "reader": reader,
        "evidence_plan": evidence_plan,
        "editorial_form": route_input["editorial_form"],
        "product_link": route_input["product_link"],
        "sources": source_urls,
        "angle": angle,
    }
    if claim_id is not None:
        frontmatter["claim_id"] = claim_id
    if "demand_card" in routed:
        frontmatter["demand_card"] = routed["demand_card"]
    yaml_text = yaml.safe_dump(
        frontmatter, allow_unicode=True, sort_keys=False, default_flow_style=False
    ).rstrip()
    sections: list[str] = [
        "---",
        yaml_text,
        "---",
        "",
        f"# {title}",
        "",
    ]
    if required_demand:
        sections.extend((
            "## Demand evidence",
            "",
            "This topic is bound to the paid-demand observations below; legacy claim text is not topic authority.",
            "",
        ))
    else:
        if claim is None:  # pragma: no cover - guarded above
            raise ValueError("legacy topic requires a durable claim")
        sections.extend((
            "## New claim",
            "",
            str(claim["claim"]),
            "",
            "## Source evidence excerpt",
            "",
            str(claim["evidence_excerpt"]),
            "",
        ))
    sections.extend((
        "## Reader job",
        "",
        str(reader["job"]),
        "",
    ))
    demand_card = routed.get("demand_card")
    if isinstance(demand_card, dict):
        sections.extend(
            (
                "## Paid-demand card",
                "",
                f"Buyer: {demand_card['buyer']}",
                f"Problem: {demand_card['problem']}",
                f"Transformation: {demand_card['transformation']}",
                f"Deliverable: {demand_card['deliverable']}",
                f"Price hypothesis: {demand_card['price_hypothesis']}",
                f"Distribution path: {demand_card['distribution_path']}",
                "",
            )
        )
        for body in demand_card["source_bodies"]:
            sections.extend(
                (
                    f"## Full source body: {body['url']}",
                    "",
                    f"Source family: {body['source_family']}",
                    f"SHA-256: {body['sha256']}",
                    f"Capture method: {body['capture_method']}",
                    "",
                    body["body"],
                    "",
                )
            )
    body = "\n".join(sections)
    return body.encode("utf-8")


def _install_exact(path: Path, content: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = path.parent.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise ValueError("topic queue must be a real directory")
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != content:
            raise ValueError("claim already has a different topic card")
        return False
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.is_symlink() or not path.is_file() or path.read_bytes() != content:
                raise ValueError("claim already has a different topic card")
            return False
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return True
    finally:
        temporary.unlink(missing_ok=True)


def materialize_topic(
    database: Path | str,
    queue: Path | str,
    proposal: dict[str, Any],
    *,
    created_at: str,
    demand_mode: str = "legacy-migration",
) -> dict[str, Any]:
    normalized_created = _timestamp(created_at, "created_at")
    if not isinstance(proposal, dict):
        raise ValueError("topic proposal must be an object")
    required_demand = demand_mode == "required"
    raw_claim_id = proposal.get("claim_id")
    if required_demand and raw_claim_id in (None, ""):
        claim_id = None
        store = None
        claim = None
    else:
        claim_id = _text(raw_claim_id, "claim_id")
        store = ClaimStore(database)
        claim = store.get(claim_id)
    content = _render_card(
        claim,
        proposal,
        created_at=str(normalized_created),
        demand_mode=demand_mode,
    )
    digest = hashlib.sha256(content).hexdigest()
    if required_demand:
        topic_id = _text(proposal.get("topic_id"), "topic_id")
        destination = Path(queue) / f"paid-demand-{topic_id.removeprefix('paid-demand:')}.md"
    else:
        if claim_id is None:  # pragma: no cover - guarded above
            raise ValueError("legacy topic requires claim_id")
        destination = Path(queue) / f"claim-{claim_id.removeprefix('clm_')}.md"
    installed = _install_exact(destination, content)
    try:
        if store is not None and claim_id is not None:
            store.consume(
                claim_id,
                topic_card=destination.name,
                topic_card_sha256=digest,
                consumed_at=str(normalized_created),
            )
    except Exception:
        if installed and destination.is_file() and not destination.is_symlink():
            if hashlib.sha256(destination.read_bytes()).hexdigest() == digest:
                destination.unlink()
        raise
    result = {
        "topic_card": str(destination),
        "topic_card_sha256": digest,
    }
    if claim_id is not None:
        result["claim_id"] = claim_id
    if required_demand:
        result["topic_id"] = proposal["topic_id"]
        # Required paid-demand refill needs to distinguish a fresh card from an
        # idempotent retry so it can terminate a no-progress wake.  Keep the
        # legacy receipt shape stable for callers that compare retry receipts.
        result["installed"] = installed
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--created-at", required=True)
    args = parser.parse_args(argv)
    proposal = json.loads(args.proposal.read_text(encoding="utf-8"))
    print(
        json.dumps(
            materialize_topic(
                args.db, args.queue, proposal, created_at=args.created_at
            ),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
