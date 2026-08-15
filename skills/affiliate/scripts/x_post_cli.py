#!/usr/bin/env python3
"""Publish one disclosed English X post with an effect fence and live readback."""

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from provider_cli import ProviderError, atomic_write, cdp_call, click, query_node, read_json
from x_profile_cli import XProfileError, choose_x_target, connect, inspect, load_config


class XPostError(Exception):
    pass


def content_fingerprint(text):
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def validate_content(text):
    value = text.strip()
    if not value or len(value) > 280:
        raise XPostError("post must contain 1..280 characters")
    if not re.search(r"(?i)(#ad\b|affiliate link)", value):
        raise XPostError("post requires a clear affiliate disclosure")
    urls = re.findall(r"https://[^\s]+", value)
    if len(urls) != 1:
        raise XPostError("post requires exactly one owned article URL")
    parsed = urlparse(urls[0].rstrip(".,)"))
    if parsed.hostname != "aniccaai.com" or not parsed.path.startswith("/blog/"):
        raise XPostError("post CTA must be an aniccaai.com blog article")
    return value


def placement_path(state_root, placement):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,80}", placement):
        raise XPostError("invalid placement id")
    return state_root / "x-posts" / f"{placement}.json"


def require_live_owned_article(state_root, text):
    url = re.findall(r"https://[^\s]+", text)[0].rstrip(".,)")
    slug = urlparse(url).path.removeprefix("/blog/")
    try:
        receipt = json.loads((state_root / "owned-publications" / f"{slug}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise XPostError("owned publication receipt is unavailable") from error
    if receipt.get("state") != "LIVE" or receipt.get("public_url") != url:
        raise XPostError("owned article is not live")


def evaluate(ws, request_id, expression):
    result = cdp_call(ws, request_id, "Runtime.evaluate", {
        "expression": expression, "returnByValue": True,
    })
    return result.get("result", {}).get("value"), request_id + 1


def navigate(ws, request_id, url):
    cdp_call(ws, request_id, "Page.enable")
    cdp_call(ws, request_id + 1, "Page.navigate", {"url": url})
    time.sleep(4)
    return request_id + 2


def timeline_posts(ws, request_id):
    expression = """(() => [...document.querySelectorAll('[data-testid="tweet"]')].map(tweet => ({
      text: tweet.querySelector('[data-testid="tweetText"]')?.innerText || '',
      url: tweet.querySelector('a[href*="/status/"]')?.href || '',
      outbound: [...tweet.querySelectorAll('[data-testid="tweetText"] a')]
        .map(anchor => anchor.href || '')
    })))()"""
    rows, request_id = evaluate(ws, request_id, expression)
    if not isinstance(rows, list):
        raise XPostError("X timeline readback is malformed")
    return rows, request_id


def resolve_outbound(url):
    parsed = urlparse(url)
    if parsed.hostname == "aniccaai.com":
        return url
    if parsed.hostname != "t.co":
        return ""
    try:
        request = Request(url, method="HEAD", headers={"User-Agent": "Life-Manager-Affiliate/1.0"})
        with urlopen(request, timeout=12) as response:
            return response.geturl()
    except OSError:
        return ""


def find_exact(rows, text, resolver=resolve_outbound):
    owned_url = re.findall(r"https://[^\s]+", text)[0].rstrip(".,)")
    prefix = text.replace(owned_url, "").strip()
    for row in rows:
        url = str(row.get("url", ""))
        outbound = [resolver(str(link)) for link in row.get("outbound", [])]
        if (
            str(row.get("text", "")).strip().startswith(prefix)
            and owned_url in outbound
            and re.search(r"/status/[0-9]+", url)
        ):
            return url.split("?")[0]
    return ""


def live_readback(ws, request_id, url, text):
    request_id = navigate(ws, request_id, url)
    rows, request_id = timeline_posts(ws, request_id)
    if find_exact(rows, text) != url:
        raise XPostError("published X post failed exact public readback")
    return request_id


def publish(args):
    root = Path(__file__).resolve().parents[1]
    config = load_config(root, "en")
    text = validate_content(args.content.read_text(encoding="utf-8"))
    fingerprint = content_fingerprint(text)
    state_root = args.state.expanduser()
    require_live_owned_article(state_root, text)
    profile = inspect(args, config)
    if profile["handle"].lower() != config["handle"].lower():
        raise XPostError("authenticated X identity mismatch")
    receipt_path = placement_path(state_root, args.placement)
    if receipt_path.is_file():
        existing = json.loads(receipt_path.read_text(encoding="utf-8"))
        if existing.get("content_sha256") != fingerprint:
            raise XPostError("placement id is already bound to different content")
    target = choose_x_target(args.cdp_host, args.cdp_port)
    ws = connect(args, target)
    try:
        request_id = navigate(ws, 1, f"https://x.com/{config['handle']}")
        rows, request_id = timeline_posts(ws, request_id)
        public_url = find_exact(rows, text)
        if not public_url and receipt_path.is_file():
            candidate = existing.get("public_url", "")
            if candidate:
                request_id = live_readback(ws, request_id, candidate, text)
                public_url = candidate
        if not public_url:
            fence = {
                "schema_version": 1,
                "receipt_type": "X_POST_EFFECT_FENCE",
                "placement_id": args.placement,
                "content_sha256": fingerprint,
                "phase": "effect-possible",
                "effect_started_at": datetime.now(timezone.utc).isoformat(),
            }
            atomic_write(receipt_path, fence)
            request_id = navigate(ws, request_id, "https://x.com/compose/post")
            for _ in range(20):
                try:
                    node_id, request_id = query_node(
                        ws, request_id,
                        '[role="dialog"] [data-testid="tweetTextarea_0"]',
                    )
                    break
                except ProviderError:
                    time.sleep(0.5)
            else:
                raise XPostError("X composer is unavailable")
            cdp_call(ws, request_id, "DOM.focus", {"nodeId": node_id})
            cdp_call(ws, request_id + 1, "Input.insertText", {"text": text})
            request_id += 2
            click(ws, request_id, '[role="dialog"] [data-testid="tweetButton"]:not([disabled])')
            time.sleep(6)
            request_id = navigate(ws, request_id + 10, f"https://x.com/{config['handle']}")
            rows, request_id = timeline_posts(ws, request_id)
            public_url = find_exact(rows, text)
            if not public_url:
                raise XPostError("X effect is ambiguous; retry will reconcile timeline")
        live_readback(ws, request_id, public_url, text)
    finally:
        ws.close()
    receipt = {
        "schema_version": 1,
        "receipt_type": "X_POST_PUBLIC_READBACK",
        "placement_id": args.placement,
        "handle": config["handle"],
        "content_sha256": fingerprint,
        "public_url": public_url,
        "state": "LIVE",
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_write(receipt_path, receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(prog="affiliate x post")
    parser.add_argument("command", choices=("publish",))
    parser.add_argument("--content", type=Path, required=True)
    parser.add_argument("--placement", required=True)
    parser.add_argument("--cdp-host", default="127.0.0.1")
    parser.add_argument("--cdp-port", type=int, default=9326)
    parser.add_argument(
        "--state", type=Path,
        default=Path("~/.local/state/life-manager/affiliate"),
    )
    args = parser.parse_args()
    print(json.dumps(publish(args), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (XPostError, XProfileError, ProviderError, OSError, ValueError, KeyError, json.JSONDecodeError):
        print("affiliate x post: failed closed", file=sys.stderr)
        raise SystemExit(1)
