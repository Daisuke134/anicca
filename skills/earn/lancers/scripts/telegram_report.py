#!/usr/bin/env python3
"""Read-only, truth-preserving Lancers owner snapshot and Telegram tick."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Callable, Mapping, Optional, Sequence
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUTBOX_PATH = ROOT / "skills/_shared/marketplace-core/scripts/telegram_outbox.py"
LEDGER_PATH = OUTBOX_PATH.with_name("ledger.py")
TICK_PATH = HERE / "application_tick.py"
STATE = Path.home() / ".local/state/anicca/lancers/application.json"
DATABASE = STATE.with_name("telegram.sqlite3")
LEDGER_DATABASE = STATE.with_name("marketplace-ledger.sqlite3")
STOREFRONT_LOG = STATE.parent / "logs/storefront.stdout.log"
TARGET = "0000000000"
TOKYO = ZoneInfo("Asia/Tokyo")
_LABELS = (("published", "受付中", "/myplan"), ("paused", "受付休止中", "/myplan/paused"), ("hidden", "非表示", "/myplan/archived"), ("draft", "下書き", "/myplan/draft"))
def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("dependency_unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
outbox = _load("lancers_report_outbox", OUTBOX_PATH)


@dataclass(frozen=True)
class SendResult:
    attempted: bool
    provider_message_id: Optional[str] = None
    error_code: Optional[str] = None


@dataclass(frozen=True)
class DeliveryResult:
    attempted: int = 0
    delivered: int = 0
    delivery_uncertain: int = 0
    pre_send_failed: int = 0
def read_last_json(path: Path) -> Optional[Mapping[str, object]]:
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return None
    for line in reversed(lines):
        try:
            value = json.loads(line)
        except (TypeError, ValueError):
            continue
        if isinstance(value, Mapping):
            return value
    return None


def _int(value: object) -> Optional[int]:
    return value if type(value) is int and value >= 0 else None


def _timestamp(value: object) -> Optional[str]:
    if isinstance(value, datetime):
        value = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return value.strip() if isinstance(value, str) and value.strip() else None


def _storefront_counts(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {key: None for key, _label, _href in _LABELS} | {"error": "source_unknown"}
    counts: dict[str, object] = {}
    for key, label, _href in _LABELS:
        value_for_key = value.get(key, value.get(label))
        counts[key] = _int(value_for_key)
    counts["error"] = value.get("error") if isinstance(value.get("error"), str) else None
    return counts


def _parse_storefront(page: object) -> dict[str, int]:
    if getattr(page, "url", None) != "https://www.lancers.jp/myplan":
        raise RuntimeError("storefront_route_invalid")
    anchors, found = page.locator("a"), {}
    for index in range(int(anchors.count())):
        anchor = anchors.nth(index)
        try:
            if not anchor.is_visible(): continue
            text, href = " ".join(anchor.inner_text().split()), anchor.get_attribute("href")
        except Exception:
            continue
        for key, label, expected_href in _LABELS:
            match = re.fullmatch(rf"{re.escape(label)}\s*\(\s*([0-9][0-9,]*)\s*件\s*\)", text)
            if match is not None:
                if href != expected_href or key in found: raise RuntimeError("storefront_anchor_invalid")
                found[key] = int(match.group(1).replace(",", "")); break
    if set(found) != {key for key, _label, _href in _LABELS}: raise RuntimeError("storefront_anchor_missing")
    return found


def read_storefront(state_path: Path = STATE, *, browser_factory: Optional[Callable[[str], object]] = None,
                    lock: Optional[Callable[[Path], object]] = None) -> dict[str, int]:
    tick = _load("lancers_report_application_tick", TICK_PATH)
    lock_factory = lock or tick.account_lock
    browser = page = None
    with lock_factory(Path(state_path)):
        try:
            browser = (browser_factory or tick._default_browser_factory)(tick.CDP_URL)
            page = tick._new_owned_page(browser)
            page.goto("https://www.lancers.jp/myplan", wait_until="domcontentloaded", timeout=20_000)
            return _parse_storefront(page)
        finally:
            if page is not None: tick._close_owned_page(page)
            runtime = getattr(browser, "_anicca_playwright_runtime", None)
            if runtime is not None: tick._stop_playwright_runtime(runtime)


def build_snapshot(*, application: object, pending_count: object, cumulative_verified: object,
                   storefront: object, source_observed_at: object,
                   official_readback_observed_at: object = None,
                   provider_event_time: object = None, blocker: object = None) -> dict[str, object]:
    app = application if isinstance(application, Mapping) else {}
    stages = {key: _int(app.get(key)) for key in ("observed_count", "eligible_count", "verified_count")}
    stages["submitted"] = (0 if isinstance(app, Mapping) and app.get("submitted") is False else 1) if isinstance(app, Mapping) and isinstance(app.get("submitted"), bool) else None
    reason = app.get("error") or app.get("reason")
    app_ok = isinstance(application, Mapping) and all(value is not None for value in stages.values())
    pending, verified = _int(pending_count), _int(cumulative_verified)
    store = _storefront_counts(storefront)
    store_ok = all(_int(store.get(key)) is not None for key, _label, _href in _LABELS)
    resolved_blocker = blocker if isinstance(blocker, str) and blocker else (reason if isinstance(reason, str) and reason != "no_eligible_project" else None)
    if not resolved_blocker and store.get("error"):
        resolved_blocker = str(store["error"])
    return {
        "application": stages, "pending": pending, "cumulative_verified": verified,
        "storefront": store, "blocker": resolved_blocker or None,
        "source_observed_at": _timestamp(source_observed_at),
        "official_readback_observed_at": _timestamp(official_readback_observed_at),
        "provider_event_time": _timestamp(provider_event_time),
        "actual_ai_cost": "unknown (meter未接続)",
        "complete": bool(app_ok and pending is not None and verified is not None and store_ok and source_observed_at and official_readback_observed_at and not resolved_blocker and not store.get("error")),
    }


def _shown(value: object) -> str:
    return str(value) if type(value) is int or isinstance(value, str) else "unknown"


def render_snapshot(snapshot: Mapping[str, object]) -> str:
    app = snapshot.get("application") if isinstance(snapshot.get("application"), Mapping) else {}
    store = snapshot.get("storefront") if isinstance(snapshot.get("storefront"), Mapping) else {}
    icon = "✅" if snapshot.get("complete") is True else "⚠️"
    blocker = snapshot.get("blocker") or "none"
    states = " / ".join(f"{label}{_shown(store.get(key))}件" for key, label, _href in _LABELS)
    return (f"{icon} Lancers G2 owner snapshot\n"
            f"acquisition: observed {_shown(app.get('observed_count'))} / qualified {_shown(app.get('eligible_count'))} / submitted {_shown(app.get('submitted'))} / newly verified {_shown(app.get('verified_count'))}\n"
            f"application receipts: cumulative verified {_shown(snapshot.get('cumulative_verified'))} / pending {_shown(snapshot.get('pending'))} / blocker {blocker}\n"
            f"storefront official counts: {states}\n"
            f"source_observed_at: {_shown(snapshot.get('source_observed_at'))}\n"
            f"official_readback_observed_at: {_shown(snapshot.get('official_readback_observed_at'))}\n"
            f"provider event time: {_shown(snapshot.get('provider_event_time'))}\n"
            f"売上: unknown\nAI処理費: unknown (meter未接続)")


def semantic_hash(snapshot: Mapping[str, object]) -> str:
    value = {key: snapshot.get(key) for key in ("application", "pending", "cumulative_verified", "storefront", "blocker", "actual_ai_cost", "complete")}
    value["storefront"] = {key: value["storefront"].get(key) for key, _label, _href in _LABELS} | {"error": value["storefront"].get("error")} if isinstance(value["storefront"], Mapping) else None
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _jst_day(value: object) -> str:
    if isinstance(value, datetime):
        parsed = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
        parsed = parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = datetime.now(timezone.utc)
    return parsed.astimezone(TOKYO).date().isoformat()


def enqueue_snapshot(database: Path, snapshot: Mapping[str, object], now: object) -> bool:
    key = f"lancers:g2:{_jst_day(now)}:{semantic_hash(snapshot)}"
    try:
        return bool(outbox.enqueue(Path(database), key, render_snapshot(snapshot), _timestamp(now) or "unknown"))
    except outbox.IdempotencyConflict:
        return False


def _provider_id(value: object) -> Optional[str]:
    if isinstance(value, SendResult):
        value = value.provider_message_id
    elif isinstance(value, Mapping):
        payload = value
        value = payload.get("messageId", payload.get("message_id", payload.get("id")))
        if value is None and isinstance(payload.get("result"), Mapping):
            result = payload["result"]
            value = result.get("messageId", result.get("message_id", result.get("id")))
    if isinstance(value, int) and value > 0:
        return str(value)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def deliver_pending(database: Path, notifier: Callable[[str], object], now: object) -> DeliveryResult:
    result = DeliveryResult()
    for _ in range(20):
        item = outbox.claim_next(Path(database))
        if item is None:
            break
        try:
            sent = notifier(item.message)
            attempted = sent.attempted if isinstance(sent, SendResult) else True
            error = sent.error_code if isinstance(sent, SendResult) else "receipt_missing"
        except Exception:
            attempted, error, sent = True, "provider_error", None
        if not attempted:
            outbox.mark_pre_send_failed(Path(database), item.event_key, error or "process_not_started")
            result = DeliveryResult(result.attempted, result.delivered, result.delivery_uncertain, result.pre_send_failed + 1)
            break
        else:
            result = DeliveryResult(result.attempted + 1, result.delivered, result.delivery_uncertain, result.pre_send_failed)
            provider_id = _provider_id(sent)
            if provider_id:
                outbox.mark_delivered(Path(database), item.event_key, provider_id, _timestamp(now) or "unknown")
                result = DeliveryResult(result.attempted, result.delivered + 1, result.delivery_uncertain, result.pre_send_failed)
            else:
                outbox.mark_delivery_uncertain(Path(database), item.event_key, error or "receipt_missing")
                result = DeliveryResult(result.attempted, result.delivered, result.delivery_uncertain + 1, result.pre_send_failed)
    return result


def _pending_count(path: Path) -> Optional[int]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, Mapping) or not isinstance(value.get("fingerprints"), list):
            return None
        if set(value) not in ({"fingerprints"}, {"fingerprints", "pending"}): return None
        fingerprints = value["fingerprints"]
        if not isinstance(fingerprints, list) or any(not isinstance(item, str) or re.fullmatch(r"[0-9a-f]{64}", item) is None for item in fingerprints): return None
        pending = value.get("pending", {})
        if not isinstance(pending, Mapping) or any(not isinstance(marker, str) or marker not in fingerprints or not isinstance(item, Mapping) for marker, item in pending.items()): return None
        return len(pending)
    except (OSError, ValueError, TypeError):
        return None


def _verified(events: object) -> tuple[int, Optional[str]]:
    rows = events if isinstance(events, Sequence) and not isinstance(events, (str, bytes)) else ()
    values = [item for item in rows if (item.get("event_type") if isinstance(item, Mapping) else getattr(item, "event_type", None)) == "application_verified"]
    stamps = [item.get("observed_at") if isinstance(item, Mapping) else getattr(item, "observed_at", None) for item in values]
    stamps = [item for item in stamps if isinstance(item, str) and item]
    return len(values), max(stamps) if stamps else None


def _source_error(error: BaseException) -> str:
    return "account_lock_busy" if "LockBusy" in type(error).__name__ else "storefront_readback_failed"


def collect_snapshot(*, application_log: Path, state_path: Path, ledger_database: Path, storefront: object = None, storefront_log: Path = STOREFRONT_LOG, now: object = None, ledger_events: object = None) -> dict[str, object]:
    observed = read_last_json(application_log)
    source_time = _timestamp(now or datetime.now(timezone.utc))
    events = ledger_events
    if events is None:
        try:
            events = _load("lancers_report_ledger", LEDGER_PATH).list_events(Path(ledger_database))
        except Exception:
            events = ()
    verified, official = _verified(events)
    latest_storefront = read_last_json(storefront_log)
    if storefront is None:
        try:
            storefront = read_storefront(Path(state_path))
        except Exception as error:
            storefront = {"error": _source_error(error)}
    if isinstance(latest_storefront, Mapping) and isinstance(latest_storefront.get("error"), str):
        storefront = dict(storefront) if isinstance(storefront, Mapping) else {}
        storefront["error"] = latest_storefront["error"]
    return build_snapshot(application=observed, pending_count=_pending_count(Path(state_path)), cumulative_verified=verified, storefront=storefront, source_observed_at=source_time, official_readback_observed_at=official)


def _default_notifier(message: str) -> SendResult:
    try:
        completed = subprocess.run(["openclaw", "message", "send", "--channel", "telegram", "--target", TARGET, "--message", message, "--json"], capture_output=True, text=True, timeout=60, check=False)
        payload = json.loads(completed.stdout) if completed.returncode == 0 else {}
        return SendResult(True, _provider_id(payload), "receipt_missing")
    except OSError:
        return SendResult(False, None, "process_not_started")
    except Exception:
        return SendResult(True, None, "provider_response_invalid")


def main(argv: Optional[Sequence[str]] = None, *, notifier: Optional[Callable[[str], object]] = None, stdout: Any = None) -> int:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--json", action="store_true", required=True); parser.add_argument("--database", default=str(DATABASE)); parser.add_argument("--ledger-database", default=str(LEDGER_DATABASE)); parser.add_argument("--state-path", default=str(STATE)); parser.add_argument("--application-log", default=str(STATE.parent / "logs/application.out.log")); parser.add_argument("--storefront-log", default=str(STOREFRONT_LOG)); parser.add_argument("--now")
    out = sys.stdout if stdout is None else stdout
    try:
        args = parser.parse_args(list(argv) if argv is not None else None); now = args.now or datetime.now(timezone.utc).isoformat(); snapshot = collect_snapshot(application_log=Path(args.application_log), state_path=Path(args.state_path), ledger_database=Path(args.ledger_database), storefront_log=Path(args.storefront_log), now=now); enqueued = int(enqueue_snapshot(Path(args.database), snapshot, now)); delivery = deliver_pending(Path(args.database), notifier or _default_notifier, now)
        payload = {"ok": delivery.delivery_uncertain == 0, "enqueued": enqueued, "attempted": delivery.attempted, "delivered": delivery.delivered, "delivery_uncertain": delivery.delivery_uncertain, "pre_send_failed": delivery.pre_send_failed}
    except Exception as exc:
        payload = {"ok": False, "error": re.sub(r"[^a-z0-9_]", "_", type(exc).__name__.lower())}
    out.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"); out.flush()
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
