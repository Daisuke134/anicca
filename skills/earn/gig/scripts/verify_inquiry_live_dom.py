#!/usr/bin/env python3
"""Independent before/after CDP verifier for inquiry replies.

The model runner never supplies the truth for a reply.  This helper captures
the talkroom DOM before and after the worker runs and only marks ``sent`` when
the message fingerprint changed and the new last message is seller-side.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import time
from pathlib import Path
import importlib.util


HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("coconala_queue_snapshot", HERE / "coconala_queue_snapshot.py")
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load Coconala collector")
_collector = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_collector)


def fingerprint(messages: object) -> str:
    rows = []
    for message in messages if isinstance(messages, list) else []:
        if not isinstance(message, dict):
            continue
        attachments = message.get("attachments") if isinstance(message.get("attachments"), list) else []
        rows.append({
            "side": message.get("side"),
            "text": message.get("text"),
            "attachments": [a.get("filename") for a in attachments if isinstance(a, dict)],
        })
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def last_side(messages: object) -> str:
    rows = messages if isinstance(messages, list) else []
    for message in reversed(rows):
        if isinstance(message, dict) and message.get("side") in {"buyer", "seller"}:
            return str(message["side"])
    return ""


def seller_count(messages: object) -> int:
    return sum(
        1 for message in (messages if isinstance(messages, list) else [])
        if isinstance(message, dict) and message.get("side") == "seller"
    )


def read_ids(path: Path) -> list[str]:
    values = json.loads(path.read_text(encoding="utf-8"))
    return [str(value) for value in values]


def run(phase: str, evidence_dir: Path, expected_ids: list[str], helper: Path) -> int:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    observed = []
    for room_id in expected_ids:
        url = f"https://coconala.com/talkrooms/{room_id}"
        screenshot = evidence_dir / f"inquiry-{phase}-{room_id}.png"
        try:
            with _collector.DefaultTab(helper, url) as tab:
                raw = asyncio.run(_collector.inspect_page(
                    tab.ws, _collector.TALKROOM_EXPRESSION, screenshot, url,
                ))
        except Exception as error:
            print(json.dumps({"ok": False, "error": f"room:{room_id}:{error}"}, ensure_ascii=False))
            return 1
        messages = raw.get("messages") if isinstance(raw, dict) else []
        observed.append({
            "talkroom_id": room_id,
            "url": url,
            "fingerprint": fingerprint(messages),
            "last_side": last_side(messages),
            "seller_count": seller_count(messages),
            "screenshot_path": str(screenshot),
            "observed_at": time.time(),
        })
    state_path = evidence_dir / f"inquiry-live-dom-{phase}.json"
    state_path.write_text(json.dumps(observed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if phase == "after":
        before_path = evidence_dir / "inquiry-live-dom-before.json"
        try:
            before = {row["talkroom_id"]: row for row in json.loads(before_path.read_text(encoding="utf-8"))}
        except (OSError, json.JSONDecodeError, TypeError):
            print(json.dumps({"ok": False, "error": "missing_before_dom"}))
            return 1
        actions = []
        for row in observed:
            prior = before.get(row["talkroom_id"], {})
            changed = bool(prior.get("fingerprint")) and prior.get("fingerprint") != row["fingerprint"]
            sent = changed and row["seller_count"] > int(prior.get("seller_count") or 0)
            live_dom_path = evidence_dir / f"inquiry-live-dom-after-{row['talkroom_id']}.json"
            live_dom_path.write_text(json.dumps({
                "url": row["url"], "reply_sent": sent, "last_side": row["last_side"],
                "seller_count": row["seller_count"], "fingerprint_changed": changed,
                "observed_at": row["observed_at"],
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            actions.append({
                "talkroom_id": row["talkroom_id"], "url": row["url"], "sent": sent,
                "screenshot_path": row["screenshot_path"], "live_dom_path": str(live_dom_path),
            })
        (evidence_dir / "inquiry-actions.json").write_text(
            json.dumps(actions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps({"ok": True, "phase": phase, "rooms": len(observed)}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--expected-ids", required=True, type=Path)
    parser.add_argument("--cdp-helper", type=Path,
                        default=Path.home() / "anicca/skills/browser/scripts/cdp_default_tab.py")
    args = parser.parse_args()
    return run(args.phase, args.evidence_dir, read_ids(args.expected_ids), args.cdp_helper)


if __name__ == "__main__":
    raise SystemExit(main())
