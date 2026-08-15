#!/usr/bin/env python3
"""Read a provider page through an existing CDP browser and emit a receipt."""

import argparse
import fcntl
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from websocket import create_connection
from job_journal import JobStateError, reconcile_effect, start_effect, verify_effect


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


def cdp_call(ws, request_id, method, params=None):
    ws.send(json.dumps({"id": request_id, "method": method, "params": params or {}}))
    while True:
        message = json.loads(ws.recv())
        if message.get("id") == request_id:
            if "error" in message:
                raise ProviderError(f"CDP {method} failed")
            return message.get("result", {})


def query_node(ws, request_id, selector):
    document = cdp_call(ws, request_id, "DOM.getDocument", {"depth": 1})
    result = cdp_call(
        ws, request_id + 1, "DOM.querySelector",
        {"nodeId": document["root"]["nodeId"], "selector": selector},
    )
    if not result.get("nodeId"):
        raise ProviderError("required login control is unavailable")
    return result["nodeId"], request_id + 2


def focus_and_type(ws, request_id, selector, value):
    node_id, request_id = query_node(ws, request_id, selector)
    resolved = cdp_call(ws, request_id, "DOM.resolveNode", {"nodeId": node_id})
    cdp_call(ws, request_id + 1, "Runtime.callFunctionOn", {
        "objectId": resolved["object"]["objectId"],
        "functionDeclaration": """function () {
            const setter = Object.getOwnPropertyDescriptor(
                HTMLInputElement.prototype, 'value'
            ).set;
            setter.call(this, '');
            this.dispatchEvent(new Event('input', {bubbles: true}));
            this.dispatchEvent(new Event('change', {bubbles: true}));
        }""",
    })
    cdp_call(ws, request_id + 2, "DOM.focus", {"nodeId": node_id})
    cdp_call(ws, request_id + 3, "Input.insertText", {"text": value})
    return request_id + 4


def click(ws, request_id, selector):
    node_id, request_id = query_node(ws, request_id, selector)
    box = cdp_call(ws, request_id, "DOM.getBoxModel", {"nodeId": node_id})
    content = box["model"]["content"]
    x = (content[0] + content[2]) / 2
    y = (content[1] + content[5]) / 2
    for event_type in ("mousePressed", "mouseReleased"):
        cdp_call(ws, request_id + 1, "Input.dispatchMouseEvent", {
            "type": event_type, "x": x, "y": y, "button": "left", "clickCount": 1,
        })
        request_id += 1


def read_login_credentials(path, section_name):
    path = path.expanduser()
    if not path.is_file() or path.stat().st_mode & 0o077:
        raise ProviderError("private credential file is unavailable")
    text = path.read_text(encoding="utf-8")
    section = re.search(
        rf"(?ms)^## {re.escape(section_name)}\n.*?(?=^## |\Z)", text,
    )
    if not section:
        raise ProviderError("provider credential section is unavailable")

    def field(label):
        match = re.search(
            rf"(?m)^- {re.escape(label)}:[ \t]*(.*?)[ \t]*$", section.group(),
        )
        value = match.group(1).strip().strip("`") if match else ""
        if not value:
            raise ProviderError("provider credential field is unavailable")
        return value

    return field("Login"), field("Password")


def submit_login(args, playbook, target):
    login = playbook.get("login")
    if not login:
        raise ProviderError("provider login automation is unsupported")
    username, password = read_login_credentials(
        args.private_markdown, login["credential_section"],
    )
    ws = create_connection(
        f"ws://{args.cdp_host}:{args.cdp_port}/devtools/page/{target['id']}",
        timeout=20, max_size=None, suppress_origin=True,
    )
    try:
        cdp_call(ws, 1, "DOM.enable")
        request_id = focus_and_type(ws, 2, login["username_selector"], username)
        request_id = focus_and_type(ws, request_id, login["password_selector"], password)
        click(ws, request_id, login["submit_selector"])
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
        if (
            candidate.get("url_contains", "") in page["url"]
            and all(marker in page["text"] for marker in candidate.get("all_text", []))
        ):
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


def observe(args):
    root = Path(__file__).resolve().parents[1]
    playbook = load_playbook(root, args.provider)
    base = f"http://{args.cdp_host}:{args.cdp_port}"
    target = choose_target(read_json(f"{base}/json/list"), playbook)
    page = evaluate(args.cdp_host, args.cdp_port, target["id"])
    state, next_action, markers = classify(playbook, page)
    return {
        "schema_version": 1,
        "receipt_type": "PROVIDER_OBSERVATION",
        "provider": args.provider,
        "state": state,
        "next_action": next_action,
        "url": page["url"],
        "title": page["title"],
        "matched_markers": markers,
        "rendered_text_sha256": hashlib.sha256(page["text"].encode()).hexdigest(),
    }


def resume(args):
    root = Path(__file__).resolve().parents[1]
    playbook = load_playbook(root, args.provider)
    before = observe(args)
    submitted = False
    if before["state"] == "SIGN_IN_REQUIRED":
        base = f"http://{args.cdp_host}:{args.cdp_port}"
        target = choose_target(read_json(f"{base}/json/list"), playbook)
        state = getattr(args, "state", args.receipt.expanduser().parent / "affiliate-state").expanduser()
        job = start_effect(
            state, "PROVIDER_LOGIN", args.provider,
            {"operation": "submit_login", "provider": args.provider},
            {key: before.get(key) for key in ("state", "url", "rendered_text_sha256")}, 300,
        )
        submit_login(args, playbook, target)
        submitted = True
        for _ in range(20):
            time.sleep(1)
            after = observe(args)
            if after["state"] != "SIGN_IN_REQUIRED":
                break
        if after["state"] == "AUTHENTICATED":
            verify_effect(state, job["job_id"], {
                key: after.get(key) for key in ("state", "url", "rendered_text_sha256")
            })
    else:
        after = before
        state = getattr(args, "state", args.receipt.expanduser().parent / "affiliate-state").expanduser()
        if after["state"] == "AUTHENTICATED":
            reconcile_effect(state, "PROVIDER_LOGIN", args.provider, {
                key: after.get(key) for key in ("state", "url", "rendered_text_sha256")
            })
    receipt = {
        **after,
        "receipt_type": "PROVIDER_RESUME",
        "previous_state": before["state"],
        "submitted": submitted,
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_write(args.receipt.expanduser(), receipt)
    return receipt


def poll(args, receipt):
    path = args.receipt.expanduser()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    with lock_path.open("a+", encoding="utf-8") as lock:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        previous = None
        if path.exists():
            previous = json.loads(path.read_text(encoding="utf-8"))
            if previous.get("provider") != args.provider:
                raise ProviderError("provider receipt mismatch")
            if previous.get("receipt_type") != "PROVIDER_POLL_STATE":
                previous = None
        previous_state = previous.get("state") if previous else None
        changed = previous_state != receipt["state"]
        sequence = (previous.get("sequence", 0) if previous else 0) + int(changed)
        material = "\0".join((
            args.provider,
            previous_state or "NONE",
            receipt["state"],
            receipt["rendered_text_sha256"],
        ))
        receipt.update({
            "receipt_type": "PROVIDER_POLL_STATE",
            "changed": changed,
            "previous_state": previous_state,
            "provider_next_action": receipt["next_action"],
            "next_action": receipt["next_action"] if changed else "NO_STATE_CHANGE",
            "sequence": sequence,
            "transition_id": (
                hashlib.sha256(material.encode()).hexdigest()
                if changed else previous.get("transition_id")
            ),
            "observed_at": datetime.now(timezone.utc).isoformat(),
        })
        atomic_write(path, receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(prog="affiliate provider")
    parser.add_argument("command", choices=("inspect", "poll", "resume"))
    parser.add_argument("--provider", required=True)
    parser.add_argument("--cdp-port", required=True, type=int)
    parser.add_argument("--cdp-host", default="127.0.0.1")
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--state", type=Path, default=Path("~/.local/state/life-manager/affiliate"))
    parser.add_argument(
        "--private-markdown", type=Path,
        default=Path("~/.config/anicca/affiliate-credentials.md"),
    )
    args = parser.parse_args()

    if args.command == "resume":
        receipt = resume(args)
    else:
        receipt = observe(args)
    if args.command == "poll":
        receipt = poll(args, receipt)
    elif args.command == "inspect":
        atomic_write(args.receipt.expanduser(), receipt)
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ProviderError, JobStateError, OSError, ValueError, KeyError, json.JSONDecodeError):
        print("affiliate provider: failed closed", file=sys.stderr)
        sys.exit(1)
