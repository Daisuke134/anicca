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
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable, Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[4]
OUTBOX_PATH = ROOT / "skills" / "_shared" / "marketplace-core" / "scripts" / "telegram_outbox.py"
STATE = Path("~/.local/state/anicca/crowdworks").expanduser()
LEDGER = STATE / "application-receipts.jsonl"
STATUS = STATE / "application-owner.json"
DATABASE = STATE / "telegram-outbox.sqlite3"
TARGET = "8547730585"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None: raise RuntimeError("telegram_outbox_unavailable")
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    spec.loader.exec_module(module); return module


outbox = _load("crowdworks_report_outbox", OUTBOX_PATH)


@dataclass(frozen=True)
class SendResult:
    started: bool
    provider_id: Optional[str]
    error: Optional[str]


def collect_snapshot(*, ledger_path: Path = LEDGER, status_path: Path = STATUS, now: str) -> dict[str, object]:
    """What this lane can honestly say: verified receipts, today's receipts, and the last tick."""
    receipts: list[Mapping[str, object]] = []
    try: lines = ledger_path.read_text(encoding="utf-8").splitlines()
    except OSError: lines = []
    for line in lines:
        try: record = json.loads(line)
        except ValueError: continue
        if isinstance(record, Mapping): receipts.append(record)
    today = now[:10]
    verified = [r for r in receipts if r.get("status") == "verified"]
    todays = [r for r in verified if str(r.get("observed_at", ""))[:10] == today]
    try: status = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, ValueError): status = {}
    return {
        "verified_total": len(verified),
        "today_count": len(todays),
        "today_proposals": [str(r.get("application_external_id")) for r in todays if r.get("application_external_id")],
        "last_status": status.get("status") if isinstance(status.get("status"), str) else None,
        "last_observed_at": status.get("observed_at") if isinstance(status.get("observed_at"), str) else None,
        "date": today,
    }


def render_snapshot(snapshot: Mapping[str, object]) -> str:
    today = snapshot.get("today_count") if type(snapshot.get("today_count")) is int else 0
    total = snapshot.get("verified_total") if type(snapshot.get("verified_total")) is int else 0
    status = snapshot.get("last_status") or "不明"
    icon = "📨" if today else ("⚠️" if status not in ("profile_complete_no_eligible_open_job", "duplicate_project", "verified") else "✅")
    headline = f"本日{today}件の応募を公式確認しました" if today else "本日の新規応募はありません"
    proposals = snapshot.get("today_proposals") if isinstance(snapshot.get("today_proposals"), list) else []
    detail = f"提案ID: {'、'.join(proposals)}。" if proposals else ""
    return (f"{icon} CrowdWorks 応募レーン: {headline}。{detail}"
            f"公式確認済みの累計は{total}件です。直近の結果は{status}でした。")


def enqueue_snapshot(database: Path, snapshot: Mapping[str, object], now: str) -> bool:
    key = f"crowdworks:apply:{snapshot.get('date')}:{snapshot.get('verified_total')}:{snapshot.get('last_status')}"
    try: return bool(outbox.enqueue(Path(database), key, render_snapshot(snapshot), now))
    except outbox.IdempotencyConflict: return False


def _provider_id(payload: object) -> Optional[str]:
    if isinstance(payload, Mapping):
        for key in ("messageId", "message_id", "id"):
            value = payload.get(key)
            if isinstance(value, (str, int)) and not isinstance(value, bool): return str(value)
        for key in ("result", "payload", "data"):
            found = _provider_id(payload.get(key))
            if found is not None: return found
    return None


def _default_notifier(message: str) -> SendResult:
    try:
        completed = subprocess.run(["openclaw", "message", "send", "--channel", "telegram", "--target", TARGET, "--message", message, "--json"], capture_output=True, text=True, timeout=70, check=False)
        payload = json.loads(completed.stdout[completed.stdout.find("{"):]) if completed.returncode == 0 and "{" in completed.stdout else {}
        return SendResult(True, _provider_id(payload), "receipt_missing")
    except OSError:
        return SendResult(False, None, "process_not_started")
    except Exception:
        return SendResult(True, None, "provider_response_invalid")


@dataclass(frozen=True)
class Delivery:
    attempted: int
    delivered: int
    delivery_uncertain: int
    pre_send_failed: int


def deliver_pending(database: Path, notifier: Callable[[str], SendResult], now: str) -> Delivery:
    attempted = delivered = uncertain = pre_send = 0
    while (item := outbox.claim_next(Path(database))) is not None:
        attempted += 1
        result = notifier(item.message)
        if not result.started:
            outbox.mark_pre_send_failed(Path(database), item.event_key, result.error or "process_not_started"); pre_send += 1
        elif result.provider_id:
            outbox.mark_delivered(Path(database), item.event_key, result.provider_id, now); delivered += 1
        else:
            outbox.mark_delivery_uncertain(Path(database), item.event_key, result.error or "receipt_missing"); uncertain += 1
    return Delivery(attempted, delivered, uncertain, pre_send)


def run(*, database: Path = DATABASE, notifier: Optional[Callable[[str], SendResult]] = None, now: Optional[str] = None) -> dict[str, object]:
    stamp = now or datetime.now(timezone.utc).isoformat()
    snapshot = collect_snapshot(now=stamp)
    enqueued = int(enqueue_snapshot(database, snapshot, stamp))
    delivery = deliver_pending(database, notifier or _default_notifier, stamp)
    return {"ok": delivery.delivery_uncertain == 0 and delivery.pre_send_failed == 0, "platform": "crowdworks",
            "enqueued": enqueued, "attempted": delivery.attempted, "delivered": delivery.delivered,
            "delivery_uncertain": delivery.delivery_uncertain, "pre_send_failed": delivery.pre_send_failed}


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
