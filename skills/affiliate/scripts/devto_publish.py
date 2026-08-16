#!/usr/bin/env python3
"""Publish one canonical Affiliate guide to DEV through the existing Forem pattern.

Copy+tweak source: skills/writer-engine/publishers/publisher_core.py.  The
Affiliate variant adds Forem's official canonical_url field and reuses the
Affiliate external-effect journal instead of Writer state.
"""

import argparse
import hashlib
import json
import os
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from job_journal import resume_effect, start_effect, unresolved_effect, verify_effect


class DevtoError(RuntimeError):
    pass


def _atomic(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _key():
    if os.environ.get("DEVTO_API_KEY", "").strip():
        return os.environ["DEVTO_API_KEY"].strip()
    for path in (Path("~/.config/anicca/affiliate.env"), Path("~/.openclaw/.env")):
        path = path.expanduser()
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("DEVTO_API_KEY=") and line.split("=", 1)[1].strip():
                return line.split("=", 1)[1].strip().strip("\"'")
    raise DevtoError("DEVTO_API_KEY is unavailable")


def _request(url, key, method="GET", payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers={
        "api-key": key, "Content-Type": "application/json",
        "User-Agent": "life-manager-affiliate/1",
    })
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except (urllib.error.URLError, json.JSONDecodeError) as error:
        raise DevtoError(f"DEV request failed: {type(error).__name__}") from error


def _existing(key, marker):
    rows = _request("https://dev.to/api/articles/me/all?per_page=1000&state=all", key)
    if not isinstance(rows, list):
        raise DevtoError("DEV article list is not an array")
    for row in rows:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        detail = row if "body_markdown" in row else _request(
            f"https://dev.to/api/articles/{row['id']}", key,
        )
        if marker in str(detail.get("body_markdown", "")):
            return detail
    return None


def _public_readback(url, title):
    request = urllib.request.Request(url, headers={"User-Agent": "life-manager-affiliate/1"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            html = response.read().decode("utf-8", errors="replace")
            return response.status == 200 and title in html
    except urllib.error.URLError:
        return False


def publish(state, plan_id):
    state = Path(state).expanduser()
    campaign_path = state / "campaign-publications" / f"{plan_id}.json"
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    if campaign.get("state") != "X_LIVE":
        raise DevtoError("campaign is not X_LIVE")
    slug = campaign["slug"]
    artifact = json.loads((state / "content" / f"{slug}.json").read_text(encoding="utf-8"))
    policy = json.loads((state / "policy" / f"{slug}.json").read_text(encoding="utf-8"))
    markdown = artifact.get("markdown", "")
    digest = hashlib.sha256(markdown.encode()).hexdigest()
    if not all((
        digest == campaign.get("content_sha256"),
        artifact.get("state") == "READY_FOR_PUBLICATION",
        artifact.get("disclosure") == "affiliate_link",
        policy.get("decision") == "PASS",
        policy.get("content_sha256") == digest,
        "affiliate link" in markdown[:800].casefold(),
    )):
        raise DevtoError("campaign artifact does not match publication receipt")
    placement = campaign["placement_id"]
    marker = f"affiliate-intent:{placement}"
    full_marker = f"<!-- {marker} content-sha256:{digest} -->"
    canonical = campaign["owned_url"]
    receipt_path = state / "devto-publications" / f"{plan_id}.json"
    if receipt_path.is_file():
        prior = json.loads(receipt_path.read_text(encoding="utf-8"))
        if prior.get("state") == "LIVE":
            return {**prior, "deduplicated": True}
    key = _key()
    existing = _existing(key, marker)
    created = existing is None
    job = unresolved_effect(state, "DEVTO_PUBLICATION", placement)
    if existing is None:
        body = markdown.rstrip() + "\n\n" + full_marker + "\n"
        action = {
            "operation": "publish_devto", "placement": placement,
            "canonical_url": canonical, "content_sha256": digest,
        }
        job = resume_effect(state, "DEVTO_PUBLICATION", placement) if job else start_effect(
            state, "DEVTO_PUBLICATION", placement, action,
            {"state": "READY", "canonical_url": canonical}, 86400,
        )
        existing = _request("https://dev.to/api/articles", key, "POST", {"article": {
            "title": artifact["title"], "body_markdown": body,
            "published": True, "canonical_url": canonical,
            "tags": ["ai", "productivity", "webdev", "tutorial"],
        }})
    if not isinstance(existing, dict) or not existing.get("id"):
        raise DevtoError("DEV publication has no stable id")
    readback = _request(f"https://dev.to/api/articles/{existing['id']}", key)
    live_url = str(readback.get("url", ""))
    valid = all((
        marker in str(readback.get("body_markdown", "")),
        full_marker in str(readback.get("body_markdown", "")),
        readback.get("canonical_url") == canonical,
        bool(readback.get("published_at")),
        live_url.startswith("https://dev.to/"),
        _public_readback(live_url, artifact["title"]),
    ))
    if not valid:
        raise DevtoError("DEV publication failed exact public readback")
    external = {"state": "LIVE", "public_id": str(readback["id"]), "public_url": live_url}
    if job:
        verify_effect(state, job["job_id"], external)
    receipt = {
        "schema_version": 1, "receipt_type": "DEVTO_PUBLICATION", "state": "LIVE",
        "plan_id": plan_id, "placement_id": placement, "canonical_url": canonical,
        "public_id": str(readback["id"]), "public_url": live_url,
        "content_sha256": digest, "published_at": readback["published_at"],
        "observed_at": datetime.now(timezone.utc).isoformat(), "deduplicated": not created,
    }
    _atomic(receipt_path, receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(prog="affiliate distribution")
    parser.add_argument("command", choices=("publish-devto",))
    parser.add_argument("--state", type=Path, default=Path("~/.local/state/life-manager/affiliate"))
    parser.add_argument("--plan", required=True)
    args = parser.parse_args()
    print(json.dumps(publish(args.state, args.plan), sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
