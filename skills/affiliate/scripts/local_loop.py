#!/usr/bin/env python3
"""Mac-local Affiliate wake and append-only receipts."""

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
from types import SimpleNamespace

from job_journal import JobStateError, start_effect, verify_effect
from provider_cli import ProviderError, observe, poll


def atomic_json(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def append(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def append_unique(path, value, identity):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.seek(0)
        for line in stream:
            try:
                existing = json.loads(line)
            except ValueError:
                continue
            if all(existing.get(key) == value[key] for key in identity):
                return False
        stream.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
        return True


def json_rows(path):
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def latest_live_url(state):
    receipts = list((state / "x-posts").glob("*.json")) + list(
        (state / "owned-publications").glob("*.json")
    )
    live = []
    for path in receipts:
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if row.get("state") == "LIVE" and str(row.get("public_url", "")).startswith("https://"):
            live.append(row)
    return max(live, key=lambda row: row.get("observed_at", ""))["public_url"] if live else None


def owner_event(state, wake_event):
    ledger = json_rows(state / "commission-ledger.jsonl")
    transition = ledger[-1] if ledger else None
    cycle_path = state / "revenue-cycle.json"
    try:
        cycle = json.loads(cycle_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cycle = {}
    if transition:
        kind = {
            "pending": "COMMISSION_PENDING", "approved": "COMMISSION_APPROVED",
            "reversed": "COMMISSION_REVERSED", "paid": "COMMISSION_PAID",
        }.get(transition.get("status"), "COMMISSION_CHANGED")
        identity = {"kind": kind, "transition_id": transition["transition_id"]}
        money = (
            f"{transition.get('status')} / gross={transition.get('gross_commission_minor')} minor "
            f"net={transition.get('net_commission_minor')} minor / {transition.get('currency') or 'currency unknown'}"
        )
    elif cycle.get("state") == "NO_TRANSACTIONS":
        kind = "REVENUE_RECONCILED"
        identity = {"kind": kind, "provider": "elevenlabs", "state": "NO_TRANSACTIONS"}
        money = "NO_TRANSACTIONS / gross=unknown / net=unknown / cost=unknown"
    elif wake_event["status"] not in ("READY_FOR_PUBLICATION",):
        kind = "BLOCKED"
        identity = {"kind": kind, "provider": "elevenlabs", "status": wake_event["status"]}
        money = "unknown"
    else:
        return None
    event_uuid = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    public_url = (transition or {}).get("placement", {}).get("public_url") or latest_live_url(state)
    recovery = "なし" if kind != "BLOCKED" else f"未回復: {wake_event['status']}"
    next_job = "buyer-intentを収集し、次の公開・収益照合を継続"
    body = "\n".join((
        "Life Manager Affiliate::: Affiliate loop report",
        f"実行: {kind}",
        f"公開先: {public_url or '未紐付け'}",
        "プログラム: ElevenLabs / PartnerStack",
        f"お金: {money}",
        f"回復: {recovery}",
        f"次: {next_job}",
    ))
    return {"event_uuid": event_uuid, "kind": kind, "body": body, "created_at": int(time.time())}


def find_message_id(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key.replace("_", "").lower() == "messageid" and item is not None:
                return str(item)
            found = find_message_id(item)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = find_message_id(item)
            if found:
                return found
    return None


def flush_telegram(state, event, runner=subprocess.run):
    if event:
        append_unique(state / "telegram-outbox.jsonl", event, ("event_uuid",))
    sent_ids = {row.get("event_uuid") for row in json_rows(state / "telegram-sent.jsonl")}
    pending = [row for row in json_rows(state / "telegram-outbox.jsonl") if row.get("event_uuid") not in sent_ids]
    if not pending:
        return {"state": "NO_PENDING", "sent": 0, "message_id": None}
    openclaw = shutil.which("openclaw")
    if not openclaw:
        return {"state": "TRANSPORT_UNAVAILABLE", "sent": 0, "message_id": None}
    row = pending[0]
    try:
        job = start_effect(
            state, "TELEGRAM_SEND", row["event_uuid"],
            {"channel": "telegram", "event_uuid": row["event_uuid"],
             "body_sha256": hashlib.sha256(row["body"].encode()).hexdigest()},
            {"state": "NOT_SENT", "event_uuid": row["event_uuid"]}, 60,
        )
    except JobStateError:
        return {"state": "RECONCILE_REQUIRED", "sent": 0, "message_id": None}
    completed = runner(
        [openclaw, "message", "send", "--channel", "telegram", "--target", "8547730585",
         "--message", row["body"], "--json"],
        check=False, capture_output=True, text=True, timeout=30,
    )
    try:
        response = json.loads(completed.stdout)
    except ValueError:
        response = None
    message_id = find_message_id(response)
    if completed.returncode or not message_id:
        return {"state": "SEND_FAILED", "sent": 0, "message_id": None}
    append_unique(state / "telegram-sent.jsonl", {
        "event_uuid": row["event_uuid"], "message_id": message_id,
        "sent_at": int(time.time()),
    }, ("event_uuid",))
    verify_effect(state, job["job_id"], {
        "state": "SENT", "event_uuid": row["event_uuid"], "message_id": message_id,
    })
    return {"state": "SENT", "sent": 1, "message_id": message_id}


def elevenlabs_link(path):
    if not path.is_file() or path.stat().st_mode & 0o077:
        return None
    text = path.read_text(encoding="utf-8")
    section = re.search(r"(?ms)^## ElevenLabs\n.*?(?=^## |\Z)", text)
    if not section:
        return None
    match = re.search(r"(?m)^- Default affiliate link: `([^`]+)`$", section.group())
    if not match:
        return None
    link = match.group(1)
    parsed = urlparse(link)
    return link if parsed.scheme == "https" and parsed.hostname == "try.elevenlabs.io" else None


def browser_ready(port, attempts=15):
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=3) as response:
                return response.status == 200
        except OSError:
            if attempt + 1 < attempts:
                time.sleep(2)
    return False


def provider_poll(state, cdp_port, attempts=15):
    args = SimpleNamespace(
        provider="elevenlabs",
        cdp_host="127.0.0.1",
        cdp_port=cdp_port,
        receipt=state / "providers" / "elevenlabs.json",
    )
    for attempt in range(attempts):
        try:
            return poll(args, observe(args))
        except (ProviderError, OSError, ValueError, KeyError, json.JSONDecodeError):
            if attempt + 1 < attempts:
                time.sleep(2)
    return {
        "state": "PROVIDER_OBSERVATION_FAILED",
        "changed": False,
        "transition_id": None,
    }


def revenue_cycle_due(state, now=None, cooldown_seconds=3600):
    receipt = state / "revenue-cycle.json"
    if not receipt.is_file():
        return True
    try:
        completed_at = int(json.loads(receipt.read_text(encoding="utf-8"))["completed_at"])
    except (OSError, ValueError, KeyError, TypeError):
        return True
    return (int(time.time()) if now is None else now) - completed_at >= cooldown_seconds


def run_revenue_cycle(state, cdp_port):
    if not revenue_cycle_due(state):
        return {"state": "COOLDOWN", "source_rows": None, "appended_transitions": None}
    script = Path(__file__).with_name("revenue_cli.py")
    common = ["--state", str(state), "--cdp-port", str(cdp_port)]
    result = None
    for command in ("observe", "capture", "reconcile"):
        completed = subprocess.run(
            [sys.executable, str(script), command, *common],
            check=False, capture_output=True, text=True, timeout=90,
        )
        if completed.returncode:
            return {"state": "REVENUE_CYCLE_FAILED", "source_rows": None, "appended_transitions": None}
        try:
            result = json.loads(completed.stdout)
        except ValueError:
            return {"state": "REVENUE_CYCLE_FAILED", "source_rows": None, "appended_transitions": None}
    cycle = {
        "state": result["money_state"],
        "source_rows": result["source_rows"],
        "appended_transitions": result["appended_transitions"],
        "completed_at": int(time.time()),
    }
    atomic_json(state / "revenue-cycle.json", cycle)
    return cycle


def wake(args):
    state = args.state.expanduser()
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = (state / ".wake.lock").open("a+")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        print('{"state":"ALREADY_RUNNING"}')
        return 0
    link = elevenlabs_link(args.private_markdown.expanduser())
    browser = browser_ready(args.cdp_port)
    provider = provider_poll(state, args.cdp_port) if browser else {
        "state": "BROWSER_UNAVAILABLE", "changed": False, "transition_id": None,
    }
    revenue = run_revenue_cycle(state, args.cdp_port) if provider["state"] == "AUTHENTICATED" else {
        "state": "PROVIDER_NOT_AUTHENTICATED", "source_rows": None, "appended_transitions": None,
    }
    if not link:
        status = "TRACKING_LINK_UNAVAILABLE"
    elif not browser:
        status = "BROWSER_UNAVAILABLE"
    elif provider["state"] == "AUTHENTICATED":
        status = "READY_FOR_PUBLICATION"
    else:
        status = provider["state"]
    event = {
        "event": "affiliate_wake",
        "provider": "elevenlabs",
        "provider_changed": provider["changed"],
        "provider_state": provider["state"],
        "provider_transition_id": provider["transition_id"],
        "revenue_state": revenue["state"],
        "revenue_source_rows": revenue["source_rows"],
        "revenue_appended_transitions": revenue["appended_transitions"],
        "status": status,
        "ts": int(time.time()),
    }
    append(state / "events.jsonl", event)
    atomic_json(state / "last-run.json", event)
    telegram = flush_telegram(state, owner_event(state, event))
    event["telegram_state"] = telegram["state"]
    event["telegram_message_id"] = telegram["message_id"]
    atomic_json(state / "last-run.json", event)
    lock.close()
    print(json.dumps(event, sort_keys=True, separators=(",", ":")))
    return 0


def placement(args):
    link = elevenlabs_link(args.private_markdown.expanduser())
    if not link:
        raise ValueError("verified ElevenLabs tracking link is unavailable")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,79}", args.placement):
        raise ValueError("invalid placement")
    state = args.state.expanduser()
    receipt = {
        "event": "placement_ready",
        "locale": args.locale,
        "placement": args.placement,
        "provider": "elevenlabs",
        "status": "TRACKING_LINK_VERIFIED",
        "ts": int(time.time()),
    }
    created = append_unique(
        state / "placements.jsonl", receipt, ("provider", "locale", "placement")
    )
    receipt["deduplicated"] = not created
    print(link if args.print_url else json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


def main():
    parser = argparse.ArgumentParser(prog="affiliate loop")
    parser.add_argument("command", choices=("wake", "placement"))
    parser.add_argument("--state", type=Path, default=Path("~/.local/state/life-manager/affiliate"))
    parser.add_argument("--private-markdown", type=Path, default=Path("~/.config/anicca/affiliate-credentials.md"))
    parser.add_argument("--cdp-port", type=int, default=9324)
    parser.add_argument("--placement", default="article-1")
    parser.add_argument("--locale", choices=("en", "ja"), default="en")
    parser.add_argument("--print-url", action="store_true")
    args = parser.parse_args()
    return wake(args) if args.command == "wake" else placement(args)


if __name__ == "__main__":
    raise SystemExit(main())
