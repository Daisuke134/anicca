#!/usr/bin/env python3
"""Inspect or apply the versioned English Affiliate X profile through CDP."""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from websocket import create_connection

from job_journal import JobStateError, reconcile_effect, start_effect, verify_effect
from provider_cli import ProviderError, atomic_write, cdp_call, click, query_node, read_json


class XProfileError(Exception):
    pass


def exact_profile_count(text, kind):
    labels = {
        "followers": r"(?:フォロワー|Followers?)",
        "following": r"(?:フォロー中|Following)",
    }
    pattern = labels.get(kind)
    if not isinstance(text, str) or pattern is None:
        return None
    match = re.fullmatch(rf"([0-9][0-9,]*)\s+{pattern}", text.strip(), re.I)
    return int(match.group(1).replace(",", "")) if match else None


def exact_post_metric(text, kind):
    labels = {
        "views": r"Views?",
        "replies": r"Replies?\.\s*Reply",
        "reposts": r"reposts?\.\s*Repost",
        "likes": r"Likes?\.\s*Like",
        "bookmarks": r"Bookmarks?\.\s*Bookmark",
    }
    pattern = labels.get(kind)
    if not isinstance(text, str) or pattern is None:
        return None
    match = re.fullmatch(rf"([0-9][0-9,]*)\s+{pattern}", " ".join(text.split()), re.I)
    return int(match.group(1).replace(",", "")) if match else None


def load_config(root, locale):
    if locale != "en":
        raise XProfileError("unsupported X locale")
    try:
        value = json.loads(
            (root / "config" / "x-profiles" / f"{locale}.json").read_text(encoding="utf-8")
        )
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise XProfileError("invalid X profile config") from error
    if value.get("schema_version") != 1:
        raise XProfileError("unsupported X profile config")
    if not re.fullmatch(r"[A-Za-z0-9_]{1,15}", value.get("handle", "")):
        raise XProfileError("invalid X handle")
    if not 1 <= len(value.get("display_name", "")) <= 50:
        raise XProfileError("invalid X display name")
    if len(value.get("bio", "")) > 160:
        raise XProfileError("invalid X bio")
    parsed = urlparse(value.get("url", ""))
    if parsed.scheme != "https" or parsed.hostname != "aniccaai.com":
        raise XProfileError("invalid X profile URL")
    return value


def choose_x_target(host, port):
    targets = read_json(f"http://{host}:{port}/json/list")
    matches = [
        item for item in targets
        if item.get("type") == "page"
        and urlparse(item.get("url", "")).hostname in {"x.com", "www.x.com"}
    ]
    if len(matches) != 1:
        raise XProfileError(f"expected one X tab, found {len(matches)}")
    return matches[0]


def connect(args, target):
    return create_connection(
        f"ws://{args.cdp_host}:{args.cdp_port}/devtools/page/{target['id']}",
        timeout=20, max_size=None, suppress_origin=True,
    )


def navigate(ws, request_id, url):
    cdp_call(ws, request_id, "Page.enable")
    cdp_call(ws, request_id + 1, "Page.navigate", {"url": url})
    return request_id + 2


def evaluate_profile(ws, request_id):
    expression = """(() => {
      const rawName = document.querySelector('[data-testid="UserName"]')?.innerText || '';
      const handle = (rawName.split('\\n').find(v => v.startsWith('@')) || '').slice(1);
      const links = [...document.querySelectorAll('a[href]')];
      const following = links.find(a => a.getAttribute('href') === `/${handle}/following`);
      const followers = links.find(a => [`/${handle}/followers`, `/${handle}/verified_followers`]
        .includes(a.getAttribute('href')));
      return {
        name: rawName.split('\\n')[0] || '',
        handle,
        bio: document.querySelector('[data-testid="UserDescription"]')?.innerText || '',
        url: document.querySelector('[data-testid="UserUrl"]')?.innerText || '',
        followers_text: followers?.innerText || '',
        following_text: following?.innerText || '',
        owner: Boolean(document.querySelector('[data-testid="editProfileButton"]')),
        rendered_url: location.href
      };
    })()"""
    for _ in range(20):
        result = cdp_call(ws, request_id, "Runtime.evaluate", {
            "expression": expression, "returnByValue": True,
        })
        request_id += 1
        value = result.get("result", {}).get("value")
        if isinstance(value, dict) and value.get("handle"):
            return value, request_id
        time.sleep(0.5)
    raise XProfileError("X profile DOM did not become ready")


def set_control(ws, request_id, selector, value):
    node_id, request_id = query_node(ws, request_id, selector)
    resolved = cdp_call(ws, request_id, "DOM.resolveNode", {"nodeId": node_id})
    cdp_call(ws, request_id + 1, "Runtime.callFunctionOn", {
        "objectId": resolved["object"]["objectId"],
        "functionDeclaration": """function (value) {
          const prototype = this instanceof HTMLTextAreaElement
            ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
          Object.getOwnPropertyDescriptor(prototype, 'value').set.call(this, value);
          this.dispatchEvent(new Event('input', {bubbles: true}));
          this.dispatchEvent(new Event('change', {bubbles: true}));
        }""",
        "arguments": [{"value": value}],
    })
    return request_id + 2


def wait_for_edit_controls(ws, request_id):
    expression = """Boolean(
      document.querySelector("input[name='displayName']") &&
      document.querySelector("textarea[name='description']") &&
      document.querySelector("input[name='url']") &&
      document.querySelector("button[data-testid='Profile_Save_Button']")
    )"""
    for _ in range(20):
        result = cdp_call(ws, request_id, "Runtime.evaluate", {
            "expression": expression, "returnByValue": True,
        })
        request_id += 1
        if result.get("result", {}).get("value") is True:
            return request_id
        time.sleep(0.5)
    raise XProfileError("X profile edit controls did not become ready")


def inspect(args, config):
    target = choose_x_target(args.cdp_host, args.cdp_port)
    ws = connect(args, target)
    try:
        request_id = navigate(ws, 1, f"https://x.com/{config['handle']}")
        profile, _ = evaluate_profile(ws, request_id)
    finally:
        ws.close()
    if profile["handle"].lower() != config["handle"].lower() or not profile["owner"]:
        raise XProfileError("authenticated X identity mismatch")
    return profile


def inspect_post_metrics(args, config, post_url):
    parsed = urlparse(post_url)
    expected_path = f"/{config['handle']}/status/"
    if not (
        parsed.scheme == "https" and parsed.hostname == "x.com"
        and parsed.path.startswith(expected_path)
        and re.fullmatch(r"[0-9]+", parsed.path.removeprefix(expected_path))
        and not parsed.query and not parsed.fragment
    ):
        raise XProfileError("invalid X post permalink")
    target = choose_x_target(args.cdp_host, args.cdp_port)
    ws = connect(args, target)
    try:
        request_id = navigate(ws, 1, post_url)
        path_json = json.dumps(parsed.path)
        expression = f"""(() => {{
          const path = {path_json};
          const article = [...document.querySelectorAll('article')]
            .find(a => a.querySelector(`a[href="${{path}}"]`));
          if (!article) return null;
          const analytics = article.querySelector(`a[href="${{path}}/analytics"]`);
          const aria = testid => article.querySelector(`[data-testid="${{testid}}"]`)
            ?.getAttribute('aria-label') || '';
          return {{
            views_text: analytics?.innerText || '',
            replies_text: aria('reply'),
            reposts_text: aria('retweet'),
            likes_text: aria('like'),
            bookmarks_text: aria('bookmark')
          }};
        }})()"""
        raw = None
        for _ in range(20):
            result = cdp_call(ws, request_id, "Runtime.evaluate", {
                "expression": expression, "returnByValue": True,
            })
            request_id += 1
            raw = result.get("result", {}).get("value")
            if isinstance(raw, dict):
                break
            time.sleep(0.5)
    finally:
        ws.close()
    if not isinstance(raw, dict):
        raise XProfileError("X post metrics DOM did not become ready")
    return {
        key: exact_post_metric(raw.get(f"{key}_text"), key)
        for key in ("views", "replies", "reposts", "likes", "bookmarks")
    }


def matches(profile, config):
    return (
        profile["name"] == config["display_name"]
        and profile["bio"] == config["bio"]
        and profile["url"].rstrip("/") == config["url"].removeprefix("https://").rstrip("/")
    )


def apply(args, config):
    before = inspect(args, config)
    if matches(before, config):
        reconcile_effect(args.state, "X_PROFILE_SAVE", config["handle"], {
            key: before.get(key) for key in ("name", "handle", "bio", "url", "rendered_url")
        })
        return before, False
    target = choose_x_target(args.cdp_host, args.cdp_port)
    ws = connect(args, target)
    try:
        request_id = navigate(ws, 1, "https://x.com/settings/profile")
        request_id = wait_for_edit_controls(ws, request_id)
        request_id = set_control(ws, request_id, "input[name='displayName']", config["display_name"])
        request_id = set_control(ws, request_id, "textarea[name='description']", config["bio"])
        request_id = set_control(ws, request_id, "input[name='url']", config["url"])
        job = start_effect(
            args.state, "X_PROFILE_SAVE", config["handle"], config,
            {key: before.get(key) for key in ("name", "handle", "bio", "url", "rendered_url")}, 300,
        )
        click(ws, request_id, "button[data-testid='Profile_Save_Button']:not([disabled])")
        time.sleep(2)
    finally:
        ws.close()
    after = inspect(args, config)
    if not matches(after, config):
        raise XProfileError("X profile save readback mismatch")
    verify_effect(args.state, job["job_id"], {
        key: after.get(key) for key in ("name", "handle", "bio", "url", "rendered_url")
    })
    return after, True


def main():
    parser = argparse.ArgumentParser(prog="affiliate x")
    parser.add_argument("command", choices=("inspect", "apply"))
    parser.add_argument("--locale", default="en")
    parser.add_argument("--cdp-host", default="127.0.0.1")
    parser.add_argument("--cdp-port", type=int, default=9326)
    parser.add_argument("--state", type=Path, default=Path("~/.local/state/mr-bot/affiliate"))
    parser.add_argument(
        "--receipt", type=Path,
        default=Path("~/.local/state/mr-bot/affiliate/x-profile-en.json"),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config = load_config(root, args.locale)
    profile, changed = (apply(args, config) if args.command == "apply" else (inspect(args, config), False))
    receipt = {
        "schema_version": 1,
        "receipt_type": "X_PROFILE",
        "handle": config["handle"],
        "name": profile["name"],
        "bio": profile["bio"],
        "url": profile["url"],
        "changed": changed,
        "matches_config": matches(profile, config),
        "followers": {
            "count": exact_profile_count(profile.get("followers_text"), "followers"),
            "state": (
                "EXACT" if exact_profile_count(profile.get("followers_text"), "followers") is not None
                else "UNAVAILABLE_EXACT"
            ),
        },
        "following": {
            "count": exact_profile_count(profile.get("following_text"), "following"),
            "state": (
                "EXACT" if exact_profile_count(profile.get("following_text"), "following") is not None
                else "UNAVAILABLE_EXACT"
            ),
        },
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_write(args.receipt.expanduser(), receipt)
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (XProfileError, ProviderError, JobStateError, OSError, ValueError, KeyError, json.JSONDecodeError):
        print("affiliate x: failed closed", file=sys.stderr)
        sys.exit(1)
