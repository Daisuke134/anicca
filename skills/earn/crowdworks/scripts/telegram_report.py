#!/usr/bin/env python3
"""CrowdWorks apply-lane Telegram tick, delivered through the shared marketplace outbox.

Reporting is not a per-platform concern: Lancers already loads
skills/_shared/marketplace-core/scripts/telegram_outbox.py for the same job, so this reads its own
state and renders its own sentence but reuses that outbox for idempotency and delivery accounting.
Without it the lane could submit applications all day and nothing would reach Dais.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[4]
OUTBOX_PATH = ROOT / "skills" / "_shared" / "marketplace-core" / "scripts" / "telegram_outbox.py"
# The [Platform][応募判断] wording is already written once, platform-neutral, and proven in
# production by Coconala. Reuse it rather than writing a fourth copy of the same sentences; moving
# the file into _shared is the extraction step once its other consumer is not mid-flight.
ENVELOPE_PATH = ROOT / "skills" / "earn" / "gig" / "scripts" / "report_envelope.py"
# Lancers delivers through this client, not through a CLI: launchd gives a job no PATH, so shelling
# out to a Homebrew binary fails as process_not_started and the queue silently stops delivering.
DELIVERY_PATH = ROOT / "skills" / "_shared" / "marketplace-core" / "scripts" / "telegram_delivery.py"
CHAT_CONFIG = Path.home() / ".config" / "anicca" / "crowdworks" / "telegram.env"
STATE = Path("~/.local/state/anicca/crowdworks").expanduser()
LEDGER = STATE / "application-receipts.jsonl"
STATUS = STATE / "application-owner.json"
DATABASE = STATE / "telegram-outbox.sqlite3"
def _report_chat() -> str:
    """Where the owner report goes; never a repository literal."""
    for key in ("CROWDWORKS_REPORT_CHAT", "GIG_REPORT_CHAT"):
        value = os.environ.get(key, "").strip()
        if value: return value
    try: lines = CHAT_CONFIG.read_text(encoding="utf-8").splitlines()
    except OSError: return ""
    for raw in lines:
        name, _, value = raw.partition("=")
        if name.strip() in ("CROWDWORKS_REPORT_CHAT", "GIG_REPORT_CHAT"): return value.strip()
    return ""


TARGET = _report_chat()


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None: raise RuntimeError("telegram_outbox_unavailable")
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    spec.loader.exec_module(module); return module


outbox = _load("crowdworks_report_outbox", OUTBOX_PATH)
envelope = _load("crowdworks_report_envelope", ENVELOPE_PATH)
delivery = _load("crowdworks_report_delivery", DELIVERY_PATH)
SendResult = delivery.SendResult


def _receipts(ledger_path: Path) -> list[Mapping[str, object]]:
    try: lines = ledger_path.read_text(encoding="utf-8").splitlines()
    except OSError: return []
    out = []
    for line in lines:
        try: record = json.loads(line)
        except ValueError: continue
        if isinstance(record, Mapping) and record.get("status") == "verified": out.append(record)
    return out


def decision_message(receipt: Mapping[str, object], now: str) -> str:
    """One completed application, rendered by the shared envelope.

    The application is already submitted and confirmed on CrowdWorks by the time a receipt exists,
    so this is the 応募完了 event. Reporting it as 応募判断 said "応募を準備します" about work that
    was already done.
    """
    project = str(receipt.get("opportunity_external_id") or "")
    proposal = str(receipt.get("application_external_id") or "")
    observed = str(receipt.get("observed_at") or now)
    title = receipt.get("opportunity_title")
    work_event = {
        "kind": "application",
        "state": "verified",
        "event_key": f"crowdworks:application:{proposal}",
        "entity_id": project,
        "occurred_at": observed,
        "next_action": "クライアントからの返信を待ち、返信があれば同じレーンが対応します。",
        "attributes": {
            "platform": "crowdworks",
            "platform_display_name": "CrowdWorks",
            "title": title if isinstance(title, str) and title.strip() else f"案件 {project}",
            "proposal_id": proposal,
            "quote": {"currency": "JPY", "amount": str(receipt.get("proposed_amount_minor") or ""), "unit": "固定報酬"},
        },
    }
    built = envelope.build_work_event_envelope(work_event=work_event, observed_at=datetime.fromisoformat(now))
    return envelope.render_human_ja(built)


def enqueue_decisions(database: Path, *, ledger_path: Path = LEDGER, now: str) -> int:
    """Enqueue one message per verified application; the proposal id keeps it exactly-once."""
    enqueued = 0
    for receipt in _receipts(ledger_path):
        proposal = str(receipt.get("application_external_id") or "")
        if not proposal: continue
        try:
            if outbox.enqueue(Path(database), f"crowdworks:application:{proposal}", decision_message(receipt, now), now): enqueued += 1
        except outbox.IdempotencyConflict:
            continue
        except Exception:
            continue
    return enqueued


def run(*, database: Path = DATABASE, notifier: Optional[Callable[[str], SendResult]] = None, now: Optional[str] = None) -> dict[str, object]:
    stamp = now or datetime.now(timezone.utc).isoformat()
    enqueued = enqueue_decisions(database, now=stamp)
    send = notifier or (lambda message: delivery.send_via_shared_client(message, chat_id=TARGET))
    sent = delivery.deliver_pending(outbox, database, send, stamp)
    return {"ok": sent.delivery_uncertain == 0 and sent.pre_send_failed == 0, "platform": "crowdworks",
            "enqueued": enqueued, "attempted": sent.attempted, "delivered": sent.delivered,
            "delivery_uncertain": sent.delivery_uncertain, "pre_send_failed": sent.pre_send_failed}


def main(argv: Optional[Sequence[str]] = None, *, notifier: Optional[Callable[[str], SendResult]] = None, stdout: Any = None) -> int:
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--database", default=str(DATABASE))
    parser.add_argument("--now", default=None)
    args = parser.parse_args(argv)
    result = run(database=Path(args.database), notifier=notifier, now=args.now)
    out = stdout or sys.stdout
    out.write(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"); out.flush()
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
