"""Slack post helper."""
import os
import json
import urllib.request
from pathlib import Path


def load_env():
    env_path = Path.home() / ".openclaw" / ".env"
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            if k.startswith("export "):
                k = k[7:]
            os.environ.setdefault(k.strip(), v.strip())


def post_blocks(channel: str, text_fallback: str, blocks: list) -> dict:
    load_env()
    payload = {"channel": channel, "text": text_fallback, "blocks": blocks}
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read().decode("utf-8"))
    if not resp.get("ok"):
        raise RuntimeError(f"Slack failed: {resp}")
    return resp


def trim(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n - 3] + "..."
