#!/usr/bin/env python3
"""Build one source-bound English affiliate article without exposing its link."""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from local_loop import elevenlabs_link
from provider_cli import atomic_write


class ContentError(Exception):
    pass


REQUIRED = {
    "elevenlabs-affiliate": "Earn up to 22% in commissions over 12 months",
    "elevenlabs-pricing": "Free $0 (10,000 credits); Starter $6 (30,000 credits)",
    "elevenlabs-tts": "commercial usage rights are only available with paid plans",
    "elevenlabs-alec": "five-figure income stream",
    "elevenlabs-greg": "referring thousands of users each month",
}

FOUNDATION_REQUIRED = {
    "elevenlabs-pricing": "Credits are shared across every product",
    "elevenlabs-tts": "Output is nondeterministic",
}

AGENTS_REQUIRED = {
    "elevenagents-overview": "tools to monitor and evaluate agent performance at scale",
    "elevenagents-quickstart": "managed either through the",
    "elevenagents-integrations": "whether through web widgets, mobile apps, phone systems, or custom integrations",
    "elevenagents-cost": "There is no cost to create your agent.",
}

DISCLOSURE = "Disclosure: This article contains an affiliate link."
FORBIDDEN_CLAIMS = ("guaranteed income", "guaranteed earnings", "risk-free income", "100% guaranteed")


def require_sources(state, required, now):
    source_hashes = {}
    for source_id, marker in required.items():
        directory = state / "sources" / source_id
        try:
            receipt = json.loads((directory / "latest.json").read_text(encoding="utf-8"))
            expires = datetime.fromisoformat(receipt["expires_at"])
            artifact = next(directory.glob(f"{receipt['raw_sha256']}.*"))
            raw = artifact.read_text(encoding="utf-8")
        except (OSError, ValueError, KeyError, StopIteration) as error:
            raise ContentError("required source capture is unavailable") from error
        if expires <= now or marker not in raw:
            raise ContentError("required source is stale or does not support its claim")
        source_hashes[source_id] = receipt["raw_sha256"]
    return source_hashes


def build(root, state, private_markdown):
    now = datetime.now(timezone.utc)
    source_hashes = require_sources(state, REQUIRED, now)
    link = elevenlabs_link(private_markdown)
    if not link:
        raise ContentError("executable ElevenLabs link is unavailable")
    template = (root / "config" / "content" / "elevenlabs-en-v1.md").read_text(encoding="utf-8")
    if template.count("{{AFFILIATE_LINK}}") != 1:
        raise ContentError("content template has an invalid link boundary")
    markdown = template.replace("{{AFFILIATE_LINK}}", link)
    slug = "elevenlabs-plans-for-solo-creators"
    artifact = {
        "schema_version": 1,
        "artifact_id": "elevenlabs-en-v1",
        "slug": slug,
        "locale": "en",
        "title": "ElevenLabs for Solo Creators: Which Plan Actually Makes Sense?",
        "disclosure": "affiliate_link",
        "source_hashes": source_hashes,
        "content_sha256": hashlib.sha256(markdown.encode()).hexdigest(),
        "markdown": markdown,
        "state": "READY_FOR_POLICY",
        "built_at": now.isoformat(),
    }
    target = state / "content" / f"{slug}.json"
    atomic_write(target, artifact)
    return {key: artifact[key] for key in ("artifact_id", "slug", "content_sha256", "state")}


def build_agents(root, state, private_markdown):
    now = datetime.now(timezone.utc)
    source_hashes = require_sources(state, AGENTS_REQUIRED, now)
    link = elevenlabs_link(private_markdown, "ElevenAgents affiliate link")
    if not link:
        raise ContentError("executable ElevenAgents link is unavailable")
    template = (root / "config" / "content" / "elevenagents-en-v1.md").read_text(encoding="utf-8")
    if template.count("{{AFFILIATE_LINK}}") != 1:
        raise ContentError("content template has an invalid link boundary")
    markdown = template.replace("{{AFFILIATE_LINK}}", link)
    slug = "elevenagents-for-customer-support"
    artifact = {
        "schema_version": 1,
        "artifact_id": "elevenagents-en-v1",
        "slug": slug,
        "locale": "en",
        "title": "ElevenAgents for Customer Support: What to Test Before You Pay",
        "disclosure": "affiliate_link",
        "source_hashes": source_hashes,
        "content_sha256": hashlib.sha256(markdown.encode()).hexdigest(),
        "markdown": markdown,
        "state": "READY_FOR_POLICY",
        "built_at": now.isoformat(),
    }
    atomic_write(state / "content" / f"{slug}.json", artifact)
    return {key: artifact[key] for key in ("artifact_id", "slug", "content_sha256", "state")}


def build_foundation(root, state):
    now = datetime.now(timezone.utc)
    source_hashes = require_sources(state, FOUNDATION_REQUIRED, now)
    markdown = (root / "config" / "content" / "ai-voice-evaluation-en-v1.md").read_text(encoding="utf-8")
    if "affiliate link" not in markdown or "contains no affiliate links" not in markdown:
        raise ContentError("foundation disclosure is missing")
    slug = "how-to-test-ai-voice-tools-before-you-pay"
    artifact = {
        "schema_version": 1,
        "artifact_id": "ai-voice-evaluation-en-v1",
        "slug": slug,
        "locale": "en",
        "title": "How to Test an AI Voice Tool Before You Pay",
        "source_hashes": source_hashes,
        "content_sha256": hashlib.sha256(markdown.encode()).hexdigest(),
        "markdown": markdown,
        "readback_markers": [
            "This article is independent editorial content.",
            "Score five things, not one",
            "Choose the lowest plan that clears the job",
        ],
        "state": "READY_FOR_PUBLICATION",
        "built_at": now.isoformat(),
    }
    atomic_write(state / "content" / f"{slug}.json", artifact)
    return {key: artifact[key] for key in ("artifact_id", "slug", "content_sha256", "state")}


def policy_checks(artifact, source_hashes, link):
    markdown = artifact.get("markdown", "")
    tracking = link if isinstance(link, str) else ""
    parsed = urlsplit(tracking)
    lowered = markdown.lower()
    return {
        "artifact_hash": hashlib.sha256(markdown.encode()).hexdigest() == artifact.get("content_sha256"),
        "disclosure_before_first_cta": bool(tracking) and DISCLOSURE in markdown and markdown.find(DISCLOSURE) < markdown.find(tracking),
        "fresh_sources_match_artifact": source_hashes == artifact.get("source_hashes"),
        "one_owned_tracking_link": bool(tracking) and markdown.count(tracking) == 1 and parsed.scheme == "https" and parsed.hostname == "try.elevenlabs.io",
        "forbidden_claims_absent": not any(claim in lowered for claim in FORBIDDEN_CLAIMS),
    }


def policy_campaign(state, private_markdown, slug, required, link_field, project, markers):
    path = state / "content" / f"{slug}.json"
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ContentError("affiliate article artifact is unavailable") from error
    if artifact.get("state") not in ("READY_FOR_POLICY", "READY_FOR_PUBLICATION"):
        raise ContentError("affiliate article is not ready for policy")
    source_hashes = require_sources(state, required, datetime.now(timezone.utc))
    link = elevenlabs_link(private_markdown, link_field)
    checks = policy_checks(artifact, source_hashes, link)
    receipt = {
        "schema_version": 1,
        "receipt_type": "CONTENT_POLICY",
        "artifact_id": artifact.get("artifact_id"),
        "slug": slug,
        "content_sha256": artifact.get("content_sha256"),
        "source_hashes": source_hashes,
        "checks": checks,
        "decision": "PASS" if all(checks.values()) else "FAIL",
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_write(state / "policy" / f"{slug}.json", receipt)
    if receipt["decision"] != "PASS":
        raise ContentError("affiliate article policy failed")
    artifact.update({
        "project": project,
        "readback_markers": [DISCLOSURE, *markers, "Last evidence refresh"],
        "readback_links": [link],
        "state": "READY_FOR_PUBLICATION",
    })
    atomic_write(path, artifact)
    return {key: receipt[key] for key in ("artifact_id", "slug", "content_sha256", "decision")}


def policy(state, private_markdown):
    return policy_campaign(
        state, private_markdown, "elevenlabs-plans-for-solo-creators", REQUIRED,
        "Default affiliate link", "AI VOICE TOOLS", ["A simple buying checklist"],
    )


def policy_agents(state, private_markdown):
    return policy_campaign(
        state, private_markdown, "elevenagents-for-customer-support", AGENTS_REQUIRED,
        "ElevenAgents affiliate link", "AI CUSTOMER SUPPORT", ["The five-test evaluation"],
    )


def build_x(state):
    slug = "elevenlabs-plans-for-solo-creators"
    publication_path = state / "owned-publications" / f"{slug}.json"
    try:
        publication = json.loads(publication_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ContentError("live owned publication receipt is unavailable") from error
    url = f"https://aniccaai.com/blog/{slug}"
    if publication.get("state") != "LIVE" or publication.get("public_url") != url:
        raise ContentError("owned article is not live")
    text = (
        "Choosing an AI voice plan? Compare commercial rights, real monthly usage, "
        "cloning needs, and correction time before upgrading.\n\n"
        "Affiliate link: my evidence-based ElevenLabs plan guide:\n"
        f"{url}"
    )
    if len(text) > 280:
        raise ContentError("X artifact exceeds the platform limit")
    target = state / "x-content" / "elevenlabs-en-1.txt"
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text + "\n")
        os.replace(temporary_path, target)
    finally:
        temporary_path.unlink(missing_ok=True)
    return {
        "artifact_id": "elevenlabs-x-en-1",
        "placement": "elevenlabs-en-1",
        "content_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "state": "READY_FOR_X_PUBLICATION",
    }


def build_x_agents(state):
    slug = "elevenagents-for-customer-support"
    publication_path = state / "owned-publications" / f"{slug}.json"
    try:
        publication = json.loads(publication_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ContentError("live owned publication receipt is unavailable") from error
    url = f"https://aniccaai.com/blog/{slug}"
    if publication.get("state") != "LIVE" or publication.get("public_url") != url:
        raise ContentError("owned article is not live")
    text = (
        "A customer-support voice agent needs more than a polished demo. Test knowledge freshness, "
        "failure handling, latency, channel fit, and real call costs before rollout.\n\n"
        "Affiliate link disclosed in my ElevenAgents evaluation:\n"
        f"{url}"
    )
    if len(text) > 280:
        raise ContentError("X artifact exceeds the platform limit")
    target = state / "x-content" / "elevenagents-en-1.txt"
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text + "\n")
        os.replace(temporary_path, target)
    finally:
        temporary_path.unlink(missing_ok=True)
    return {
        "artifact_id": "elevenagents-x-en-1",
        "placement": "elevenagents-en-1",
        "content_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "state": "READY_FOR_X_PUBLICATION",
    }


def main():
    parser = argparse.ArgumentParser(prog="affiliate content")
    parser.add_argument("command", choices=("build", "build-agents", "build-foundation", "build-x", "build-x-agents", "policy", "policy-agents"))
    parser.add_argument("--state", type=Path, default=Path("~/.local/state/life-manager/affiliate"))
    parser.add_argument("--private-markdown", type=Path, default=Path("~/.config/anicca/affiliate-credentials.md"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.command == "build-x":
        result = build_x(args.state.expanduser())
    elif args.command == "build-x-agents":
        result = build_x_agents(args.state.expanduser())
    elif args.command == "policy":
        result = policy(args.state.expanduser(), args.private_markdown.expanduser())
    elif args.command == "policy-agents":
        result = policy_agents(args.state.expanduser(), args.private_markdown.expanduser())
    elif args.command == "build-foundation":
        result = build_foundation(root, args.state.expanduser())
    elif args.command == "build-agents":
        result = build_agents(root, args.state.expanduser(), args.private_markdown.expanduser())
    else:
        result = build(root, args.state.expanduser(), args.private_markdown.expanduser())
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContentError, OSError, ValueError, KeyError):
        print("affiliate content: failed closed", file=sys.stderr)
        raise SystemExit(1)
