#!/usr/bin/env python3
"""Deterministic Japanese Capafy owner report and delivery ledger."""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
import re
import stat
import sys
import tempfile
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capafy_outcome import validate_outcome

JST = dt.timezone(dt.timedelta(hours=9))
KINDS = {"hourly", "morning", "daily_close", "event"}
REASONS = {"sale", "published", "repair_closed", "unresolved"}
KEY = re.compile(r"^[A-Za-z0-9_.:-]+$")
PERIOD = {"hourly": re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}$"), "morning": re.compile(r"^\d{4}-\d{2}-\d{2}$"), "daily_close": re.compile(r"^\d{4}-\d{2}-\d{2}$")}
HANDLE = re.compile(r"(?:no-active-account|capafy\.[a-z0-9](?:[a-z0-9._-]{0,61}[a-z0-9])?)$")
REEL_PATH = re.compile(r"^/reel/[A-Za-z0-9_-]+/$")
CREDENTIAL_WORDS = ("token", "secret", "password", "authorization", "credential", "sk_live", "bearer")


def bad(message: str):
    raise ValueError(message)


def amount(value: object) -> str:
    try:
        number = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if not number.is_finite():
            raise InvalidOperation
    except (InvalidOperation, TypeError, ValueError):
        bad("company_state money field is malformed")
    return f"{'-' if number < 0 else ''}${abs(number):.2f}"


def public_url(value: object) -> str | None:
    if not isinstance(value, str) or "{" in value or "}" in value:
        return None
    try:
        parsed = urlparse(value)
        port = parsed.port
        hostname = parsed.hostname
    except ValueError:
        return None
    if parsed.scheme != "https" or not hostname or "@" in parsed.netloc or parsed.username or parsed.password or port not in (None, 443) or "#" in value:
        return None
    try:
        pairs = parse_qsl(parsed.query, keep_blank_values=True)
    except ValueError:
        return None
    query_text = "&".join(f"{key}={val}" for key, val in pairs).lower()
    return value if not any(word in query_text for word in CREDENTIAL_WORDS) else None


def role_url(value: object, hosts: set[str], path_pattern: re.Pattern[str] | None = None) -> str | None:
    value = public_url(value)
    if not value:
        return None
    parsed = urlparse(value)
    if (parsed.hostname or "").lower() not in hosts:
        return None
    if path_pattern and not path_pattern.fullmatch(parsed.path):
        return None
    return value


def validate_links(state: dict) -> None:
    listing = state.get("listing_url")
    if listing is not None and not role_url(listing, {"capafy.ai"}):
        bad("listing_url is not a safe Capafy URL")
    marketing = state.get("marketing")
    if not isinstance(marketing, dict):
        bad("marketing is required")
    reel = marketing.get("public_post_url")
    if reel is not None and not role_url(reel, {"www.instagram.com", "instagram.com"}, REEL_PATH):
        bad("marketing.public_post_url is not a safe Reel URL")
    campaign = marketing.get("campaign_url")
    if campaign is not None and not role_url(campaign, {"capafy-skills-daily.netlify.app"}):
        bad("marketing.campaign_url is not a safe campaign URL")
    if not role_url(state.get("dashboard_url"), {"capafy-skills-daily.netlify.app"}):
        bad("dashboard_url is not a safe dashboard URL")


def validate_company_state(state: dict) -> None:
    errors = validate_outcome(state)
    if errors:
        bad("company_state is not deliverable: " + "; ".join(errors))
    account = state.get("account")
    if not isinstance(account, dict) or not HANDLE.fullmatch(str(account.get("handle") or "")):
        bad("account.handle is invalid")
    validate_links(state)


def infer_reason(state: dict, previous: dict | None) -> str | None:
    old_marketing, new_marketing = (previous or {}).get("marketing") or {}, state.get("marketing") or {}
    paid_up = isinstance(state.get("paid_orders"), int) and isinstance(previous.get("paid_orders"), int) and state["paid_orders"] > previous["paid_orders"] if previous else False
    if previous and (state.get("orders", 0) > previous.get("orders", 0) or paid_up):
        return "sale"
    if public_url(new_marketing.get("public_post_url")) and not public_url(old_marketing.get("public_post_url")):
        return "published"
    if previous and previous.get("incident") and not state.get("incident"):
        return "repair_closed"
    if state.get("incident"):
        return "unresolved"
    event_id = str(state.get("last_event_id") or "")
    if re.search(r"(?:^|:)order\.received(?:[:]|$)", event_id):
        return "sale"
    if re.search(r"(?:^|:)content\.published(?:[:]|$)", event_id):
        return "published"
    if re.search(r"(?:^|:)incident\.verified(?:[:]|$)", event_id):
        return "repair_closed"
    return "unresolved" if state.get("incident") and state["incident"].get("phase") != "verified" else None


def reason_is_valid(reason: str, state: dict, previous: dict | None) -> bool:
    old_marketing, new_marketing = (previous or {}).get("marketing") or {}, state.get("marketing") or {}
    event_id = str(state.get("last_event_id") or "")
    if reason == "sale":
        paid_up = previous and isinstance(state.get("paid_orders"), int) and isinstance(previous.get("paid_orders"), int) and state["paid_orders"] > previous["paid_orders"]
        return bool(previous and (state.get("orders", 0) > previous.get("orders", 0) or paid_up)) or bool(re.search(r"(?:^|:)order\.received(?:[:]|$)", event_id))
    if reason == "published":
        return bool(public_url(new_marketing.get("public_post_url")) and not public_url(old_marketing.get("public_post_url"))) or bool(re.search(r"(?:^|:)content\.published(?:[:]|$)", event_id))
    if reason == "repair_closed":
        prior_active = isinstance((previous or {}).get("incident"), dict) and (previous["incident"].get("phase") != "verified")
        return bool((prior_active and not state.get("incident")) or (not state.get("incident") and re.search(r"(?:^|:)incident\.verified(?:[:]|$)", event_id)))
    return bool(isinstance(state.get("incident"), dict) and state["incident"].get("phase") != "verified")


def load_envelope(stream: object) -> dict:
    try:
        envelope = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        bad(f"invalid JSON envelope: {exc}")
    if not isinstance(envelope, dict) or envelope.get("schema_version") != 1:
        bad("envelope schema_version must be 1")
    state = envelope.get("company_state")
    if not isinstance(state, dict):
        bad("company_state is required")
    validate_company_state(state)
    previous = envelope.get("previous_company_state")
    if previous is not None:
        if not isinstance(previous, dict):
            bad("previous_company_state must be an object or null")
        validate_company_state(previous)
    kind = envelope["report_kind"] if "report_kind" in envelope else "morning"
    if not isinstance(kind, str) or kind not in KINDS:
        bad("report_kind is invalid")
    reason = envelope.get("event_reason")
    if kind != "event" and reason is not None:
        bad("event_reason is only valid for event reports")
    if kind == "event" and reason is None:
        reason = infer_reason(state, previous)
    if kind == "event" and (not isinstance(reason, str) or reason not in REASONS or not reason_is_valid(reason, state, previous)):
        bad("event_reason is invalid")
    period = envelope.get("period_key")
    if not period:
        now = dt.datetime.now(JST)
        period = now.strftime("%Y-%m-%dT%H" if kind == "hourly" else "%Y-%m-%d")
    if kind != "event" and (not isinstance(period, str) or not PERIOD[kind].fullmatch(period)):
        bad("period_key is invalid")
    if kind != "event":
        try:
            dt.datetime.strptime(period, "%Y-%m-%dT%H" if kind == "hourly" else "%Y-%m-%d")
        except (TypeError, ValueError):
            bad("period_key is invalid")
    if kind == "event" and (not isinstance(period, str) or not KEY.fullmatch(period)):
        bad("period_key is invalid")
    envelope = dict(envelope)
    envelope.update(report_kind=kind, period_key=period)
    if kind == "event":
        envelope["event_reason"] = reason
    return envelope


def delivery_key(envelope: dict) -> str:
    if envelope["report_kind"] == "event":
        event_id = envelope["company_state"].get("last_event_id")
        if not isinstance(event_id, str) or not KEY.fullmatch(event_id):
            bad("last_event_id is invalid")
        return f"event:{envelope['event_reason']}:{event_id}"
    return f"{envelope['report_kind']}:{envelope['period_key']}"


def jst(value: object) -> str:
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError
        return parsed.astimezone(JST).strftime("%Y-%m-%d %H:%M JST")
    except (TypeError, ValueError):
        return "不明"


def freshness(state: dict) -> str:
    names = {"money": "売上", "inventory": "商品在庫", "account": "Instagramアカウント", "marketing": "マーケティング", "cost": "コスト"}
    groups = {"fresh": [], "stale": [], "unknown": []}
    sources = state.get("sources") if isinstance(state.get("sources"), dict) else {}
    for key, name in names.items():
        source = sources.get(key) if isinstance(sources.get(key), dict) else {}
        groups["fresh" if source.get("freshness") == "fresh" else "stale" if source.get("freshness") == "stale" else "unknown"].append(name)
    pieces = []
    if groups["fresh"]:
        pieces.append("、".join(groups["fresh"]) + "は最新")
    if groups["stale"]:
        pieces.append("、".join(groups["stale"]) + "は古いため要更新")
    if groups["unknown"]:
        pieces.append("、".join(groups["unknown"]) + "の鮮度は不明")
    return "データ鮮度: " + "。".join(pieces) + "。"


def marketer(state: dict) -> str:
    account, marketing, metrics = state["account"], state["marketing"], state["metrics"]
    reel = "公開Reelを確認済み" if public_url(marketing.get("public_post_url")) else "公開Reelは未確認"
    values = [str(metrics[x]) if isinstance(metrics.get(x), int) else "不明" for x in ("views", "likes", "comments", "clicks")]
    handle = "アカウント不明" if account["handle"] == "no-active-account" else f"@{account['handle']}"
    return f"Marketer: {handle}。{reel}。閲覧{values[0]}、いいね{values[1]}、コメント{values[2]}、計測クリック{values[3]}。"


def repair(state: dict, previous: dict | None, reason: str | None) -> str:
    incident = state.get("incident")
    owners = {"marketer": "Marketer", "builder": "Builder", "company": "会社"}
    phases = {"detected": "問題を検知", "repair_started": "修復中", "repaired": "修復済み", "unresolved": "未解決", "verified": "確認済み"}
    if isinstance(incident, dict):
        owner, phase = owners.get(incident.get("owner"), "担当不明"), phases.get(incident.get("phase"), "不明")
        return f"修復: {owner}の問題は{phase}。次回確認は{jst(incident.get('next_retry_at'))}。"
    if reason == "repair_closed" or isinstance(previous, dict) and isinstance(previous.get("incident"), dict):
        return "修復: 直前の問題は解決済み。現在対応が必要な問題はありません。"
    return "修復: 現在対応が必要な問題はありません。"


def action(state: dict, previous: dict | None, reason: str | None) -> str:
    old_marketing = (previous or {}).get("marketing") or {}
    new_marketing = state.get("marketing") or {}
    if reason == "sale" or previous and state["orders"] > previous["orders"]:
        text = "新しい注文の受取状況を確認する。"
    elif reason == "published" or previous and public_url(new_marketing.get("public_post_url")) and not public_url(old_marketing.get("public_post_url")):
        text = "公開Reelの閲覧・反応・クリック計測を確認する。"
    elif reason == "repair_closed" or previous and previous.get("incident") and not state.get("incident"):
        text = "修復後のMarketer実ブラウザ状態を再確認する。"
    elif state.get("incident"):
        text = "MarketerがInstagramの実ブラウザ状態を再取得する。"
    elif previous and state == previous:
        text = "前回から変更なし。次回の定期確認を待つ。"
    else:
        text = "次回の定期確認で売上、公開状況、修復状態を再確認する。"
    return "次の対応: " + text


def render(envelope: dict) -> str:
    state, previous, kind, period = envelope["company_state"], envelope.get("previous_company_state"), envelope["report_kind"], envelope["period_key"]
    title = {"hourly": "時間", "morning": "朝", "daily_close": "日次締め", "event": "イベント"}[kind]
    label = f"{period[:10]} {period[11:]}時" if kind == "hourly" else period
    if kind == "event":
        label = jst(state.get("as_of")).replace(" JST", "") if jst(state.get("as_of")) != "不明" else period
    paid = f"有料{state['paid_orders']}件" if isinstance(state.get("paid_orders"), int) else "有料件数不明"
    lines = [
        f"Capafy {title}レポート（{label}）",
        f"売上: 累計{state['orders']}件（{paid}）、総売上{amount(state['gross_usd'])}、受取待ち{amount(state['pending_usd'])}、入金済み{amount(state['realized_usd'])}、MRR {amount(state['mrr_usd'])}。",
        f"収支: 計測コスト{amount(state['cost_usd'])}、記録済みコスト差引後{amount(state['contribution_usd'])}。",
        freshness(state),
        f"Builder: 公開{state['inventory']['online']}件、審査中{state['inventory']['under_review']}件、下書き{state['inventory']['draft']}件、却下{state['inventory']['rejected']}件。",
        marketer(state),
        repair(state, previous, envelope.get("event_reason")),
        action(state, previous, envelope.get("event_reason")),
        f"検証ID: {state['projection_id'].removeprefix('sha256:')[:12]}",
    ]
    listing = public_url(state.get("listing_url")) or "不明"
    reel = public_url((state.get("marketing") or {}).get("public_post_url")) or "不明"
    dashboard = public_url(state.get("dashboard_url")) or "不明"
    lines += [f"Capafy: {listing}", f"Reel: {reel}"]
    content = public_url((state.get("marketing") or {}).get("campaign_url"))
    if content:
        lines.append(f"コンテンツ: {content}")
    lines.append(f"ダッシュボード: {dashboard}")
    return "\n".join(lines) + "\n"


def read_state(path: str) -> list[dict]:
    target = Path(path)
    try:
        metadata = os.lstat(target)
    except FileNotFoundError:
        return []
    except OSError as exc:
        bad(f"delivery state is unsafe: {exc}")
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o600:
        bad("delivery state is unsafe")
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        bad(f"delivery state is corrupt: {exc}")
    if not isinstance(payload, dict) or payload.get("schema_version") not in (1, 2):
        bad("delivery state is corrupt")
    if payload["schema_version"] == 1:
        return []
    rows = payload.get("deliveries")
    required = {"delivery_key", "projection_id", "telegram_message_id", "delivered_at"}
    if not isinstance(rows, list) or any(not isinstance(row, dict) or set(row) != required or not KEY.fullmatch(str(row.get("delivery_key") or "")) or not re.fullmatch(r"sha256:[0-9a-f]{64}", str(row.get("projection_id") or "")) or not re.fullmatch(r"[0-9]+", str(row.get("telegram_message_id") or "")) or not isinstance(row.get("delivered_at"), str) for row in rows):
        bad("delivery state is corrupt")
    return rows


def write_state(path: str, rows: list[dict]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        read_state(path)
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"schema_version": 2, "deliveries": rows[-256:]}, stream, ensure_ascii=False, separators=(",", ":"))
            stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
        os.chmod(temporary, stat.S_IRUSR | stat.S_IWUSR); os.replace(temporary, target); os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def delivery_ledger_lock(path: str):
    target = Path(f"{path}.lock")
    target.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(target, flags, 0o600)
    except OSError as exc:
        bad(f"delivery ledger lock is unsafe: {exc}")
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o600:
            bad("delivery ledger lock is unsafe")
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def record(args: argparse.Namespace) -> int:
    if not KEY.fullmatch(args.key or "") or not re.fullmatch(r"[0-9]+", args.message_id or "") or not re.fullmatch(r"sha256:[0-9a-f]{64}", args.projection_id or ""):
        bad("delivery record arguments are invalid")
    with delivery_ledger_lock(args.state):
        rows = read_state(args.state)
        if any(row.get("delivery_key") == args.key for row in rows):
            return 0
        rows.append({"delivery_key": args.key, "projection_id": args.projection_id, "telegram_message_id": args.message_id, "delivered_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")})
        write_state(args.state, rows)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("command", choices=("render", "delivery-key", "delivered", "record-delivery")); parser.add_argument("--state"); parser.add_argument("--key"); parser.add_argument("--projection-id"); parser.add_argument("--message-id"); args = parser.parse_args()
    try:
        if args.command in {"render", "delivery-key"}:
            envelope = load_envelope(sys.stdin)
            sys.stdout.write(render(envelope) if args.command == "render" else delivery_key(envelope) + "\n"); return 0
        if not args.state or not KEY.fullmatch(args.key or ""):
            bad("state and delivery key are required")
        if args.command == "delivered":
            with delivery_ledger_lock(args.state):
                return 0 if any(row.get("delivery_key") == args.key for row in read_state(args.state)) else 1
        if not args.projection_id or not args.message_id:
            bad("projection id and message id are required")
        return record(args)
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"capafy_owner_report: {exc}\n"); return 2


if __name__ == "__main__":
    raise SystemExit(main())
