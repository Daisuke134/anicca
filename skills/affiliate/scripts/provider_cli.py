#!/usr/bin/env python3
"""Read a provider page through an existing CDP browser and emit a receipt."""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from websocket import create_connection


class ProviderError(Exception):
    pass


def load_playbook(root, provider):
    if not re.fullmatch(r"[a-z0-9-]+", provider):
        raise ProviderError("invalid provider name")
    path = root / "config" / "provider-playbooks" / f"{provider}.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise ProviderError("invalid provider playbook") from error
    if value.get("schema_version") != 1 or value.get("provider") != provider:
        raise ProviderError("unsupported provider playbook")
    return value


def read_json(url):
    with urlopen(url, timeout=5) as response:
        return json.load(response)


def choose_target(targets, playbook):
    wanted = playbook["target"]
    matches = [
        item for item in targets
        if item.get("type") == "page"
        and wanted["url_contains"] in item.get("url", "")
        and wanted["title_contains"] in item.get("title", "")
    ]
    if len(matches) != 1:
        raise ProviderError(f"expected one provider tab, found {len(matches)}")
    return matches[0]


def evaluate(host, port, target_id):
    ws = create_connection(
        f"ws://{host}:{port}/devtools/page/{target_id}",
        timeout=20,
        max_size=None,
        suppress_origin=True,
    )
    try:
        ws.send(json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {
                "expression": "({url:location.href,title:document.title,text:document.body.innerText})",
                "returnByValue": True,
            },
        }))
        while True:
            message = json.loads(ws.recv())
            if message.get("id") == 1:
                if "error" in message:
                    raise ProviderError("CDP evaluation failed")
                return message["result"]["result"]["value"]
    finally:
        ws.close()


def classify(playbook, page):
    if not all(isinstance(page.get(key), str) for key in ("url", "title", "text")):
        raise ProviderError("invalid rendered page")
    allowed = set(playbook["allowed_origins"])
    parsed = urlparse(page["url"])
    if f"{parsed.scheme}://{parsed.netloc}" not in allowed:
        raise ProviderError("provider origin mismatch")
    for candidate in playbook["states"]:
        if all(marker in page["text"] for marker in candidate["all_text"]):
            return candidate["state"], candidate["next_action"], candidate["all_text"]
    return playbook["fallback_state"], playbook["fallback_next_action"], []


def atomic_write(path, payload):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(prog="affiliate provider")
    parser.add_argument("command", choices=("inspect",))
    parser.add_argument("--provider", required=True)
    parser.add_argument("--cdp-port", required=True, type=int)
    parser.add_argument("--cdp-host", default="127.0.0.1")
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    playbook = load_playbook(root, args.provider)
    base = f"http://{args.cdp_host}:{args.cdp_port}"
    target = choose_target(read_json(f"{base}/json/list"), playbook)
    page = evaluate(args.cdp_host, args.cdp_port, target["id"])
    state, next_action, markers = classify(playbook, page)
    receipt = {
        "schema_version": 1,
        "provider": args.provider,
        "state": state,
        "next_action": next_action,
        "url": page["url"],
        "title": page["title"],
        "matched_markers": markers,
        "rendered_text_sha256": hashlib.sha256(page["text"].encode()).hexdigest(),
    }
    atomic_write(args.receipt.expanduser(), receipt)
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ProviderError, OSError, ValueError, KeyError, json.JSONDecodeError):
        print("affiliate provider: failed closed", file=sys.stderr)
        sys.exit(1)
