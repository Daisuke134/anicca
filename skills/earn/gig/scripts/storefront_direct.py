#!/usr/bin/env python3
"""Observe one Coconala Storefront wake without the legacy Hermes/B0 path."""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from telegram_outbox import TelegramOutbox, dispatch_one  # noqa: E402
from gig_paths import BROWSER_DIR, GIG_DIR, HOST_STATE_DIR, RUNNER_DIR, STATE_DIR  # noqa: E402

DEFAULT_STATE = STATE_DIR / "storefront-direct"
DEFAULT_BRAKE = HOST_STATE_DIR / "gig-work" / "storefront.operator.brake"
DEFAULT_LEASE = BROWSER_DIR / "scripts" / "cdp_context_lease.py"
DEFAULT_TAB = BROWSER_DIR / "scripts" / "cdp_default_tab.py"
DEFAULT_ENSURE_BROWSER = BROWSER_DIR / "ensure_browser.sh"
DEFAULT_RUNNER = RUNNER_DIR / "agent_runner.py"
DEFAULT_SCHEMA = GIG_DIR / "schemas" / "storefront_judgement.schema.json"
DEFAULT_PROPOSAL_SCHEMA = GIG_DIR / "schemas" / "storefront_proposal.schema.json"
DEFAULT_CREATE_PROPOSAL_SCHEMA = GIG_DIR / "schemas" / "storefront_create_proposal.schema.json"
DEFAULT_SCORECARD = GIG_DIR / "config" / "storefront-catalog-scorecard.json"
DEFAULT_REPLY_TRANSCRIPTS = Path.home() / "gig" / "reply-transcripts.jsonl"
DEFAULT_APPLIED = Path.home() / "gig" / "applied.jsonl"
DEFAULT_EARNINGS = Path.home() / "gig" / "earnings.jsonl"
DEFAULT_PROJECTS = Path.home() / "gig" / "projects"
DEFAULT_NEGOTIATE_CONTEXT_ACKS = Path.home() / "gig" / "negotiate-context-acks.jsonl"
DEFAULT_NEGOTIATE_RUN_LOG = Path.home() / ".openclaw" / "logs" / "gig-reply-detector-launchd.out.log"
DEFAULT_CAPABILITIES = (
    Path.home() / "gig" / "projects" / "5138597" / "state.json",
    Path.home() / "gig" / "projects" / "5138597" / "acceptance" / "v4-acceptance-evidence.json",
)
DEFAULT_TELEGRAM_DATABASE = Path.home() / "gig" / "telegram-outbox.sqlite3"
DEFAULT_TELEGRAM_RECEIPTS = Path.home() / "gig" / "telegram-delivery-receipts"
STATE_FILES = (
    "effects.jsonl", "experiments.jsonl", "offer-contracts.jsonl", "attribution-map.jsonl",
    "analytics.jsonl", "outcomes.jsonl", "prepared-hypotheses.jsonl", "listing-contracts.jsonl",
    "new-listing-drafts.jsonl", "funnel-events.jsonl", "portfolio-allocations.jsonl",
    "inquiry-context-envelopes.jsonl",
)
TARGET_SERVICE_ID = "4330368"
DEFAULT_IMAGE_CONTRACT = GIG_DIR / "assets" / "storefront" / TARGET_SERVICE_ID / "image-contract.json"
GALLERY_SERVICE_ID = "4313386"
DEFAULT_GALLERY_CONTRACT = GIG_DIR / "assets" / "storefront" / GALLERY_SERVICE_ID / "gallery-contract.json"
DEFAULT_TITLE_MUTATION = GIG_DIR / "contracts" / "storefront" / "mutations" / "4308502-title-v1.json"
DEFAULT_BODY_MUTATION = GIG_DIR / "contracts" / "storefront" / "mutations" / "4308502-body-v1.json"
DEFAULT_SCOPE_MUTATION = GIG_DIR / "contracts" / "storefront" / "mutations" / "4244910-body-v1.json"
DEFAULT_PACKAGE_MUTATION = GIG_DIR / "contracts" / "storefront" / "mutations" / "4308502-package-v1.json"
DEFAULT_FAQ_MUTATION = GIG_DIR / "contracts" / "storefront" / "mutations" / "4308502-faq-v1.json"
DEFAULT_PRICE_MUTATION = GIG_DIR / "contracts" / "storefront" / "mutations" / "4308502-price-v1.json"
DEFAULT_LISTING_CONTRACT_DIR = GIG_DIR / "contracts" / "storefront"
DEFAULT_LISTING_CONTRACT_FAMILIES = GIG_DIR / "config" / "storefront-contract-families.json"
DEFAULT_NEW_LISTING_CONTRACT = (
    GIG_DIR / "contracts" / "storefront" / "new" / "seo-article-v1.json"
)
JUDGEMENT_FIELDS = {
    "decision", "service_id", "changed_field", "before_value", "proposed_value",
    "hypothesis", "competitor_evidence_paths", "capability_evidence_paths",
    "success_metric", "observation_window_days", "no_op_reason", "experiment_key", "uncertainty",
}
FAQ_PATTERN = re.compile(
    r"(?:よくある質問\s*)?Q[.．]\s*(?P<question>.+?)\s*\n+A[.．]\s*(?P<answer>.+)\Z",
    re.DOTALL,
)
SELLER_FORM_EXPRESSION = r'''JSON.stringify((()=>{const form=document.forms[0];return{url:location.href,action:form?.action||null,method:form?.method||null,fields:form?[...form.elements].filter(e=>e.name).map(e=>({name:e.name,type:e.type||null,value:e.value||'',checked:!!e.checked,maxLength:Number.isInteger(e.maxLength)&&e.maxLength>=0?e.maxLength:null})):[],select_options:form?Object.fromEntries([...form.elements].filter(e=>e.name&&e.tagName==='SELECT').map(e=>[e.name,[...e.options].map(o=>({value:o.value,label:(o.textContent||'').trim()}))])):{}}})())'''
COMPETITOR_SOURCES = (
    ("category", "https://coconala.com/categories/230/66"),
    ("search", "https://coconala.com/search?keyword=%E6%A5%AD%E5%8B%99%E8%87%AA%E5%8B%95%E5%8C%96"),
    ("service", "https://coconala.com/services/2475514"),
    ("service", "https://coconala.com/services/1991922"),
    ("service", "https://coconala.com/services/3933104"),
    ("service", "https://coconala.com/services/2200084"),
    ("service", "https://coconala.com/services/3122692"),
    ("service", "https://coconala.com/services/3741646"),
)
MUTATION_FIELDS = {"image", "title", "body", "package", "FAQ", "price"}
GENERATED_MUTATION_FIELDS = {"image", "title", "body", "package", "FAQ", "price"}
MUTATION_CONTRACT_FIELDS = {
    "version", "platform", "service_id", "precondition_listing_version_sha256",
    "changed_field", "before_value", "proposed_value", "allowed_delta", "rollback_value",
    "official_readback", "success_metric", "observation_window_days", "capability_family",
    "evidence", "contract_sha256",
}


def _atomic_write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        path.chmod(0o600)
    finally:
        try:
            Path(temporary).unlink()
        except FileNotFoundError:
            pass


def _append(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    path.chmod(0o600)


def _display_count(value: object) -> str:
    return str(value) if type(value) is int and value >= 0 else "不明"


def _display_delta(value: object) -> str:
    return f"{value:+d}" if type(value) is int else "不明"


def _display_money(value: object) -> str:
    return f"¥{value:,.0f}" if type(value) in {int, float} else "不明"


def _report_message(row: dict) -> str:
    failed = int(row.get("status") == "failed")
    hypothesis = row.get("next_hypothesis") if isinstance(row.get("next_hypothesis"), dict) else {}
    contract_delta = row.get("listing_contracts_appended")
    catalog = row.get("catalog_analytics") if isinstance(row.get("catalog_analytics"), dict) else {}
    totals = catalog.get("totals") if isinstance(catalog.get("totals"), dict) else {}
    changes = catalog.get("changes") if isinstance(catalog.get("changes"), dict) else {}
    metric_unknown = (
        catalog.get("metric_unknown_services")
        if isinstance(catalog.get("metric_unknown_services"), dict) else {}
    )
    draft = row.get("new_listing_draft") if isinstance(row.get("new_listing_draft"), dict) else {}
    funnel = row.get("funnel") if isinstance(row.get("funnel"), dict) else {}
    by_origin = funnel.get("by_origin") if isinstance(funnel.get("by_origin"), dict) else {}
    storefront_funnel = by_origin.get("storefront", {})
    apply_funnel = by_origin.get("apply", {})
    unknown_funnel = by_origin.get("unknown", {})
    funnel_coverage = funnel.get("coverage") if isinstance(funnel.get("coverage"), dict) else {}
    portfolio = row.get("portfolio") if isinstance(row.get("portfolio"), dict) else {}
    portfolio_counts = portfolio.get("counts") if isinstance(portfolio.get("counts"), dict) else {}
    portfolio_selected = portfolio.get("selected") if isinstance(portfolio.get("selected"), dict) else {}
    inquiry_context = row.get("inquiry_context") if isinstance(row.get("inquiry_context"), dict) else {}
    effect = max(int(row.get("effect") or 0), int(draft.get("effect") or 0),
                 int(draft.get("public_effect") or 0))
    readback = max(int(row.get("readback") or 0), int(draft.get("readback") or 0))
    competitor = row.get("competitor_evidence") if isinstance(row.get("competitor_evidence"), dict) else {}
    competitor_text = (
        f"今回未計測（直近full {_display_count(competitor.get('latest_full_count'))}件）"
        if competitor.get("status") == "not_checked_incremental"
        else _display_count(row.get("competitor_evidence_count")) + "件"
    )
    catalog_status = {
        "current_full": "今回公式確認",
        "last_known_good": "前回公式値",
        "not_checked_incremental": "今回未計測",
        "not_applicable": "対象外",
        "unknown": "不明",
    }.get(catalog.get("status"), "不明")
    catalog_observed_at = catalog.get("observed_at_epoch")
    if type(catalog_observed_at) is int and catalog_observed_at > 0:
        catalog_status += "・確認" + time.strftime(
            "%m/%d %H:%M", time.localtime(catalog_observed_at),
        )
    window = catalog.get("window") if isinstance(catalog.get("window"), dict) else {}
    window_text = (
        f"{window.get('start')}–{window.get('end')}"
        if window.get("complete") is True and window.get("start") and window.get("end") else "期間不明"
    )
    coverage = catalog.get("coverage") if isinstance(catalog.get("coverage"), dict) else {}
    coverage_text = f"{_display_count(coverage.get('observed'))}/{_display_count(coverage.get('expected'))}"
    draft_status = draft.get("status")
    draft_id = (
        "今回未計測" if draft_status == "not_checked_incremental"
        else str(draft.get("draft_service_id")) if draft.get("draft_service_id")
        else "不明"
    )
    draft_image = (
        "今回未計測"
        if draft_status == "not_checked_incremental" and draft.get("image_count") is None
        else _display_count(draft.get("image_count"))
    )
    draft_status_text = {
        "not_checked_incremental": "今回未計測",
        "not_applicable": "対象外",
    }.get(draft_status, str(draft_status) if draft_status else "不明")
    source_errors = funnel.get("unknown_sources")
    source_error_text = (
        ", ".join(source_errors) or "なし" if isinstance(source_errors, list) else "不明"
    )
    coverage_source_text = {
        "latest_completed_log_noncanonical": "Negotiate最新完了log（canonical inventory未提供）",
        "unknown": "不明",
    }.get(funnel_coverage.get("source_status"), "不明")
    selected_text = (
        f"{portfolio_selected.get('service_id')} / "
        f"{portfolio_selected.get('improvement_field')} / "
        f"{portfolio_selected.get('action')}"
        if portfolio_selected.get("service_id")
        and portfolio_selected.get("improvement_field")
        and portfolio_selected.get("action") else "不明"
    )
    hypothesis_executable = hypothesis.get("executable")
    executable_text = (
        f"{hypothesis.get('service_id')} / {hypothesis.get('field')}"
        if hypothesis and hypothesis_executable is True
        else f"なし（{hypothesis.get('guard_reason') or hypothesis.get('reason')}）"
        if hypothesis and hypothesis_executable is False
        else "不明" if failed
        else "なし"
    )
    next_action = (
        "失敗stageを自動修復して同じ境界から再開" if failed
        else (f"{portfolio_selected.get('service_id')}/{portfolio_selected.get('improvement_field')}を"
              f"{portfolio_selected.get('action')}" if portfolio_selected else
              "全出品adapterをversioned mutation contractへ共通化") if draft.get("status") == "already_public"
        else "公式readbackとoutcome ledgerを照合" if effect
        else f"{hypothesis.get('service_id')}/{hypothesis.get('field')}の実行harnessを継続"
        if hypothesis else
        (f"{portfolio_selected.get('service_id')}/{portfolio_selected.get('improvement_field')}のfenceを維持し、"
         "他出品の実行可能gapを選定")
        if portfolio_selected else "scorecard先頭の改善gapを選択"
    )
    lines = [
        "Codex::: 🏪 ココナラ Storefront hourly",
        f"✅ 公式出品 {_display_count(row.get('official_services_read'))}件 / 競合証拠 {competitor_text}",
        (f"📊 actionable {_display_count(row.get('actionable'))} / effect {effect} / "
         f"readback {readback} / duplicate {_display_count(row.get('duplicate'))}"),
        (f"📚 公開contract {_display_count(row.get('listing_contracts_active'))}件 / "
         f"version履歴 {_display_count(row.get('listing_contracts_total'))}件 / "
         f"今回追加 {_display_count(contract_delta)}件"),
        (f"📝 新規出品draft {draft_id} / "
         f"更新 {_display_count(draft.get('effect'))} / 照合 {_display_count(draft.get('readback'))} / "
         f"画像 {draft_image} / 公開 {_display_count(draft.get('public_effect'))} / "
         f"状態 {draft_status_text}"),
        (f"📈 公式分析 {catalog_status} / {window_text} / coverage {coverage_text}: "
         f"閲覧 {_display_count(totals.get('views'))} / 販売 {_display_count(totals.get('purchases'))} / "
         f"お気に入り {_display_count(totals.get('favorites'))} | 前回比 閲覧 {_display_delta(changes.get('views'))} / "
         f"販売 {_display_delta(changes.get('purchases'))} / "
         f"現在値不明 {_display_count(metric_unknown.get('views'))}件 / "
         f"前回比不明 {_display_count(catalog.get('change_unknown_services'))}件"),
        (f"✅ Storefront funnel: 問合せ {_display_count(storefront_funnel.get('inquiries'))} / "
         f"入金 {_display_count(storefront_funnel.get('payments'))} / "
         f"純入金 {_display_money(storefront_funnel.get('net_jpy'))}"),
        (f"✅ Apply funnel: 問合せ {_display_count(apply_funnel.get('inquiries'))} / "
         f"入金 {_display_count(apply_funnel.get('payments'))} / "
         f"純入金 {_display_money(apply_funnel.get('net_jpy'))}"),
        (f"❓ 帰属未確定: 問合せ {_display_count(unknown_funnel.get('inquiries'))} / "
         f"入金 {_display_count(unknown_funnel.get('payments'))} / "
         f"純入金 {_display_money(unknown_funnel.get('net_jpy'))}"),
        (f"🔎 Funnel coverage: transcript/公式 "
         f"{_display_count(funnel_coverage.get('transcript_conversations_ingested'))}/"
         f"{_display_count(funnel_coverage.get('official_negotiate_conversations_observed'))} / "
         f"未収載 {_display_count(funnel_coverage.get('uncovered_official_conversations'))} / "
         f"Storefront問合せ {_display_count(funnel_coverage.get('storefront_inquiries'))} / "
         f"Apply 問合せ {_display_count(funnel_coverage.get('apply_inquiries'))}・入金 "
         f"{_display_count(funnel_coverage.get('apply_payments'))} / "
         f"未帰属 問合せ {_display_count(funnel_coverage.get('unresolved_inquiries'))}・入金 "
         f"{_display_count(funnel_coverage.get('unresolved_payments'))} / "
         f"source {coverage_source_text}"),
        (f"🧭 Portfolio: KEEP {_display_count(portfolio_counts.get('KEEP'))} / "
         f"IMPROVE {_display_count(portfolio_counts.get('IMPROVE'))} / "
         f"RETIRE {_display_count(portfolio_counts.get('RETIRE'))} / "
         f"REPLACE {_display_count(portfolio_counts.get('REPLACE'))} / "
         f"枠 {_display_count((portfolio.get('capacity') or {}).get('used'))}/"
         f"{_display_count((portfolio.get('capacity') or {}).get('limit'))}"),
        (f"🧠 Negotiate context: {inquiry_context.get('negotiate_context') or '不明'} / "
         f"envelope {_display_count(inquiry_context.get('contexts'))} / "
         f"ACK {_display_count(inquiry_context.get('acknowledged'))}"),
        ("⚠️ bad: 確定入金0" if storefront_funnel.get("payments") == 0
         else "⚠️ bad: Storefront入金不明" if type(storefront_funnel.get("payments")) is not int
         else "⚠️ bad: なし"),
        f"❌ source file errors: {source_error_text}",
        f"🧪 改善選定 {selected_text} | 実行contract {executable_text}",
        f"🛡️ fence {hypothesis.get('guard_reason') or row.get('reason') or 'なし'}",
        f"🔧 次の一手: {next_action}",
    ]
    accounting = row.get("accounting") if isinstance(row.get("accounting"), dict) else None
    if accounting is not None:
        lines.append(
            f"⚡ hourly / hour {accounting.get('hour')} / day {accounting.get('day')} / "
            f"全KPI更新 {accounting.get('analytics_observed_at_epoch') or 'unknown'}"
        )
    if draft.get("public_url"):
        lines.extend(("✅ 新規SEOサービスは公式公開中", f"🔗 {draft['public_url']}"))
    if failed:
        lines.extend((f"reason: {str(row.get('reason') or 'unknown')[:300]}",
                      f"pass_id: {str(row.get('pass_id') or '')[:200]}"))
    outcome = row.get("outcome")
    if isinstance(outcome, dict):
        lines.extend((
            f"実験判定: {outcome.get('decision') or 'NO_OP'}",
            f"判定理由: {outcome.get('reason') or 'unknown'}",
        ))
    return "\n".join(lines)


def _report_identity(row: dict, message: str) -> tuple[str, str, bool]:
    draft = row.get("new_listing_draft") if isinstance(row.get("new_listing_draft"), dict) else {}
    if int(draft.get("public_effect") or 0) == 1:
        identity = ":".join((str(draft.get("candidate_key") or ""),
                             str(draft.get("contract_sha256") or ""),
                             str(draft.get("draft_service_id") or "")))
        digest = hashlib.sha256(identity.encode()).hexdigest()
        return f"gig:telegram:storefront-public-effect:v1:{digest}", "storefront_public_effect", False
    if int(row.get("readback") or 0) > 0 and row.get("experiment_key"):
        identity = ":".join((str(row.get("service_id") or ""),
                             str(row.get("changed_field") or ""),
                             str(row["experiment_key"])))
        digest = hashlib.sha256(identity.encode()).hexdigest()
        return f"gig:telegram:storefront-effect:v1:{digest}", "storefront_direct_effect", False
    if row.get("status") == "failed":
        return (f"gig:telegram:storefront-failure:v1:{str(row.get('pass_id') or '')}",
                "storefront_direct_failure", False)
    # Runtime remains in the durable receipt, not the idempotent notification.
    # v2 separates stable incremental payloads from the historical runtime-bound key.
    digest = hashlib.sha256(message.encode()).hexdigest()
    key_version = "v3" if isinstance(row.get("accounting"), dict) else "v1"
    return f"gig:telegram:storefront-noop:{key_version}:{digest}", "storefront_direct_noop", True


def _send_telegram(args: argparse.Namespace, message: str, event_key: str) -> str:
    completed = subprocess.run(
        [str(args.openclaw), "message", "send", "--channel", "telegram",
         "--target", str(args.telegram_target), "--message", message, "--json"],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=180, check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Telegram transport failed rc={completed.returncode}")
    result = json.loads(completed.stdout)
    payload = result.get("payload") if isinstance(result, dict) else None
    if isinstance(payload, dict) and payload.get("ok") is False:
        raise RuntimeError("Telegram provider rejected message")
    message_id = result.get("messageId") if isinstance(result, dict) else None
    if not message_id and isinstance(payload, dict):
        message_id = payload.get("messageId")
    if not message_id:
        raise RuntimeError("Telegram ACK has no message ID")
    receipt_path = Path(args.telegram_receipt_dir) / (
        hashlib.sha256(event_key.encode()).hexdigest() + ".json"
    )
    _atomic_write(receipt_path, {
        "version": 1, "event_key": event_key, "target": str(args.telegram_target),
        "message_sha256": hashlib.sha256(message.encode()).hexdigest(),
        "message_id": str(message_id), "provider_acked_at_epoch_ms": int(time.time() * 1000),
    })
    return str(message_id)


def _dispatch_report(args: argparse.Namespace, row: dict) -> dict:
    message = _report_message(row)
    event_key, kind, suppress = _report_identity(row, message)
    outbox = TelegramOutbox(Path(args.telegram_database))
    report = outbox.enqueue(event_key=event_key, kind=kind, message=message,
                            created_at=int(time.time()), suppress_identical_body=suppress)
    if report.get("suppressed"):
        return {"status": "suppressed", "message_id": report.get("message_id"),
                "event_key": event_key}
    if report["state"] in {"sent", "delivery_unknown"}:
        return {"status": "deduped" if report["state"] == "sent" else "delivery_unknown",
                "message_id": report.get("message_id"), "event_key": event_key}
    delivered = dispatch_one(
        outbox, owner=f"gig-storefront-direct:{row.get('pass_id')}",
        now=lambda: int(time.time()),
        transport=lambda body: _send_telegram(args, body, event_key),
        report_id=int(report["report_id"]),
    )
    return {"status": delivered["status"], "message_id": delivered.get("message_id"),
            "event_key": event_key}


def _persist_receipt(args: argparse.Namespace, output: Path, row: dict) -> dict:
    durable = dict(row)
    durable.setdefault("mode", "incremental" if getattr(args, "incremental", False) else "full")
    if getattr(args, "auto_cadence", False):
        durable["cadence"] = {
            "auto": True,
            "full_interval_seconds": int(getattr(args, "full_interval_seconds", 1800)),
        }
    if hasattr(args, "telegram_database"):
        try:
            durable["telegram"] = _dispatch_report(args, durable)
        except Exception as error:
            durable["telegram"] = {"status": "failed", "error": type(error).__name__}
    _append(args.state_dir / "wakes.jsonl", durable)
    _atomic_write(output, durable)
    return durable


def _append_effect_once(path: Path, value: dict) -> bool:
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise RuntimeError("effect_ledger_invalid") from error
            if row.get("status") == "accepted" and row.get("experiment_key") == value.get("experiment_key"):
                return False
    _append(path, value)
    return True


def _append_key_once(path: Path, field: str, value: dict) -> bool:
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                prior = json.loads(line)
            except json.JSONDecodeError as error:
                raise RuntimeError(f"{path.stem}_ledger_invalid") from error
            if prior.get(field) == value.get(field):
                return False
    _append(path, value)
    return True


def _jsonl_rows(path: Path) -> tuple[list[dict], str | None]:
    if not path.is_file():
        return [], f"{path.name}_missing"
    rows = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if isinstance(row, dict):
                    rows.append(row)
    except (OSError, json.JSONDecodeError):
        return [], f"{path.name}_invalid"
    return rows, None


def _latest_negotiate_observation(path: Path) -> tuple[dict | None, str | None]:
    if not path.is_file():
        return None, f"{path.name}_missing"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None, f"{path.name}_invalid"
    for line in reversed(lines):
        if not line.strip().startswith("{"):
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("status") == "completed" and type(row.get("observed")) is int:
            return {
                "observed": row["observed"],
                "run_id": row.get("run_id"),
                "evidence_path": str(path.resolve()),
                "evidence_sha256": hashlib.sha256(line.encode()).hexdigest(),
            }, None
    return None, f"{path.name}_completed_observation_missing"


def _last_known_good_catalog_analytics(
    state_dir: Path, service_ids: list[str], now: int,
) -> dict | None:
    expected_ids = set(service_ids)
    if (
        not expected_ids
        or len(expected_ids) != len(service_ids)
        or any(not value.isdigit() for value in service_ids)
    ):
        raise RuntimeError("catalog_analytics_expected_services_invalid")
    expected_services = len(expected_ids)
    wakes, error = _jsonl_rows(state_dir / "wakes.jsonl")
    if error not in {None, "wakes.jsonl_missing"}:
        raise RuntimeError(error)
    source_row = next((
        row for row in reversed(wakes)
        if row.get("status") == "completed"
        and isinstance(row.get("catalog_analytics"), dict)
        and row["catalog_analytics"].get("services_observed") == expected_services
        and isinstance(row["catalog_analytics"].get("totals"), dict)
        and isinstance(row["catalog_analytics"].get("metric_unknown_services"), dict)
    ), None)
    if source_row is None:
        return None

    catalog = dict(source_row["catalog_analytics"])
    source_epoch = int(
        catalog.get("observed_at_epoch") or source_row.get("observed_at_epoch") or 0
    )
    analytics, analytics_error = _jsonl_rows(state_dir / "analytics.jsonl")
    if analytics_error not in {None, "analytics.jsonl_missing"}:
        raise RuntimeError(analytics_error)
    latest_official: dict[str, dict] = {}
    for row in analytics:
        service_id = str(row.get("service_id") or "")
        if service_id in expected_ids and row.get("official") is True:
            latest_official[service_id] = row
    windows = {
        json.dumps(row.get("window"), sort_keys=True, separators=(",", ":"))
        for row in latest_official.values()
        if isinstance(row.get("window"), dict) and row["window"].get("complete") is True
    }
    window = json.loads(next(iter(windows))) if len(latest_official) == expected_services and len(windows) == 1 else None
    catalog.update({
        "status": "last_known_good",
        "observed_at_epoch": source_epoch,
        "freshness_seconds": max(0, now - source_epoch) if source_epoch else None,
        "coverage": {"observed": int(catalog["services_observed"]), "expected": expected_services},
        "window": window,
    })
    return catalog


def _last_full_competitor_evidence(state_dir: Path, now: int) -> dict:
    wakes, error = _jsonl_rows(state_dir / "wakes.jsonl")
    if error not in {None, "wakes.jsonl_missing"}:
        raise RuntimeError(error)
    source = next((
        row for row in reversed(wakes)
        if row.get("status") == "completed"
        and row.get("mode") == "full"
        and type(row.get("competitor_evidence_count")) is int
    ), None)
    if source is None:
        return {"status": "not_checked_incremental", "latest_full_count": None,
                "observed_at_epoch": None, "freshness_seconds": None}
    observed_at = int(source.get("observed_at_epoch") or 0)
    return {
        "status": "not_checked_incremental",
        "latest_full_count": int(source["competitor_evidence_count"]),
        "observed_at_epoch": observed_at,
        "freshness_seconds": max(0, now - observed_at) if observed_at else None,
    }


def _auto_cadence_is_incremental(state_dir: Path, now: int, full_interval_seconds: int) -> bool:
    if full_interval_seconds <= 0:
        raise RuntimeError("full_interval_seconds_invalid")
    rows, error = _jsonl_rows(state_dir / "wakes.jsonl")
    if error not in {None, "wakes.jsonl_missing"}:
        raise RuntimeError(error)
    full_epochs = [
        int(row.get("observed_at_epoch") or 0)
        for row in rows
        if row.get("status") == "completed"
        and (
            row.get("mode") == "full"
            or (row.get("mode") is None and row.get("reason") != "incremental_catalog_funnel_readback")
        )
    ]
    last_full_epoch = max(full_epochs, default=0)
    return last_full_epoch > 0 and now - last_full_epoch < full_interval_seconds


def _join_funnel(
    state_dir: Path, contracts: list[dict], reply_transcripts: Path, applied_path: Path,
    earnings_path: Path, projects_dir: Path, now: int,
    negotiate_run_log: Path = DEFAULT_NEGOTIATE_RUN_LOG,
) -> dict:
    transcripts, transcript_error = _jsonl_rows(reply_transcripts)
    applied, applied_error = _jsonl_rows(applied_path)
    earnings, earnings_error = _jsonl_rows(earnings_path)
    versions = {row["service_id"]: row["service_version_sha256"] for row in contracts}
    applied_rows = {
        str(row.get("requestId") or ""): row
        for row in applied if row.get("status") == "applied" and row.get("requestId")
    }
    apply_talkrooms: dict[str, dict] = {}
    if projects_dir.is_dir():
        for path in projects_dir.glob("*/state.json"):
            try:
                project = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            request_id, talkroom_id = str(project.get("request_id") or ""), str(project.get("talkroom_id") or "")
            application = applied_rows.get(request_id)
            if application is not None and talkroom_id:
                apply_talkrooms[talkroom_id] = {
                    "request_id": request_id,
                    "project_state_path": str(path.resolve()),
                    "project_state_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "application_evidence_sha256": hashlib.sha256(json.dumps(
                        application, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                    ).encode()).hexdigest(),
                }
    conversations: dict[str, dict] = {}
    for row in transcripts:
        talkroom_id = str(row.get("talkroom_id") or "")
        if not talkroom_id:
            continue
        evidence = json.dumps({"buyer_last_said": row.get("buyer_last_said"),
                               "conversation": row.get("conversation")}, ensure_ascii=False)
        service_ids = {value for value in re.findall(r"coconala\.com/services/(\d+)", evidence)
                       if value in versions}
        current = conversations.setdefault(talkroom_id, {"service_ids": set(), "observed_at": row.get("sent_at")})
        current["service_ids"].update(service_ids)
        if type(row.get("sent_at")) is int:
            prior = current.get("observed_at")
            current["observed_at"] = min(row["sent_at"], prior) if type(prior) is int else row["sent_at"]
    origins = {}
    appended = 0
    for talkroom_id, value in conversations.items():
        ids = value["service_ids"]
        service_id = next(iter(ids)) if len(ids) == 1 else None
        origin = "storefront" if service_id else "apply" if talkroom_id in apply_talkrooms else "unknown"
        origins[talkroom_id] = (origin, service_id)
        event = {
            "version": 1, "source_event_id": f"coconala:conversation:{talkroom_id}",
            "event_kind": "inquiry", "platform": "coconala", "origin": origin,
            "service_id": service_id, "listing_version": versions.get(service_id),
            "conversation_id": talkroom_id, "order_id": None,
            "observed_at_epoch": value.get("observed_at"), "ingested_at_epoch": now,
        }
        appended += int(_append_key_once(state_dir / "funnel-events.jsonl", "source_event_id", event))
        _append_key_once(state_dir / "attribution-map.jsonl", "attribution_key", {
            **event, "attribution_key": f"coconala:conversation:{talkroom_id}",
        })
    attribution_corrections_appended = 0
    for row in earnings:
        talkroom_id = str(row.get("talkroom_id") or "")
        origin, service_id = origins.get(talkroom_id, ("unknown", None))
        if origin == "unknown" and talkroom_id in apply_talkrooms:
            origin = "apply"
        idem = str(row.get("idem_key") or "")
        if not idem or type(row.get("jpy")) not in {int, float} or row.get("net_of_fee") is not True:
            continue
        source_event_id = f"coconala:payment:{idem}"
        event = {
            "version": 1, "source_event_id": source_event_id,
            "event_kind": "payment", "platform": "coconala", "origin": origin,
            "service_id": service_id, "listing_version": versions.get(service_id),
            "conversation_id": talkroom_id or None, "order_id": str(row.get("requestId") or "") or None,
            "gross_jpy": None, "fee_jpy": None, "refund_jpy": None,
            "net_receipt_jpy": row["jpy"], "observed_at_epoch": row.get("ts"),
            "ingested_at_epoch": now, "immutable_receipt_id": idem,
            "revision_count": None, "rating": None, "review_id": None, "repeat_purchase": None,
        }
        appended += int(_append_key_once(state_dir / "funnel-events.jsonl", "source_event_id", event))
        if origin == "apply":
            evidence = apply_talkrooms[talkroom_id]
            evidence_sha = hashlib.sha256(json.dumps(
                evidence, sort_keys=True, separators=(",", ":"),
            ).encode()).hexdigest()
            correction = {
                "version": 1,
                "attribution_key": f"{source_event_id}:origin:apply:evidence:{evidence_sha}",
                "event_kind": "attribution_correction",
                "source_event_id": source_event_id,
                "platform": "coconala",
                "origin": "apply",
                "conversation_id": talkroom_id,
                "order_id": str(row.get("requestId") or "") or None,
                "immutable_receipt_id": idem,
                "evidence": evidence,
                "observed_at_epoch": now,
            }
            attribution_corrections_appended += int(_append_key_once(
                state_dir / "attribution-map.jsonl", "attribution_key", correction,
            ))
    events, ledger_error = _jsonl_rows(state_dir / "funnel-events.jsonl")
    attributions, attribution_error = _jsonl_rows(state_dir / "attribution-map.jsonl")
    negotiate_observation, negotiate_observation_error = _latest_negotiate_observation(
        negotiate_run_log,
    )
    corrections = {
        str(row.get("source_event_id")): row
        for row in attributions
        if row.get("event_kind") == "attribution_correction"
        and row.get("origin") in {"storefront", "apply", "unknown"}
        and row.get("source_event_id")
    }
    summary = {origin: {"inquiries": 0, "payments": 0, "net_jpy": 0.0}
               for origin in ("storefront", "apply", "unknown")}
    for event in events:
        correction = corrections.get(str(event.get("source_event_id") or ""), {})
        corrected_origin = correction.get("origin", event.get("origin"))
        origin = corrected_origin if corrected_origin in summary else "unknown"
        if event.get("event_kind") == "inquiry":
            summary[origin]["inquiries"] += 1
        elif event.get("event_kind") == "payment" and type(event.get("net_receipt_jpy")) in {int, float}:
            summary[origin]["payments"] += 1
            summary[origin]["net_jpy"] += float(event["net_receipt_jpy"])
    errors = [value for value in (
        transcript_error, applied_error, earnings_error, ledger_error, attribution_error,
        negotiate_observation_error,
    ) if value]
    cursor_inputs = [str(row.get("source_event_id") or "") for row in events]
    cursor_inputs.extend(str(row.get("attribution_key") or "") for row in attributions)
    cursor = hashlib.sha256("\n".join(sorted(cursor_inputs)).encode()).hexdigest()
    official_observed = negotiate_observation.get("observed") if negotiate_observation else None
    transcript_ingested = len(conversations)
    uncovered = (
        max(official_observed - transcript_ingested, 0)
        if type(official_observed) is int else None
    )
    coverage = {
        "official_negotiate_conversations_observed": official_observed,
        "transcript_conversations_ingested": transcript_ingested,
        "uncovered_official_conversations": uncovered,
        "storefront_inquiries": summary["storefront"]["inquiries"],
        "apply_inquiries": summary["apply"]["inquiries"],
        "apply_payments": summary["apply"]["payments"],
        "unresolved_inquiries": summary["unknown"]["inquiries"],
        "unresolved_payments": summary["unknown"]["payments"],
        "source_status": "latest_completed_log_noncanonical" if negotiate_observation else "unknown",
        "source": negotiate_observation,
    }
    return {"version": 1, "appended": appended, "events": len(events), "by_origin": summary,
            "attribution_corrections_appended": attribution_corrections_appended,
            "coverage": coverage, "unknown_sources": errors, "cutoff_cursor": cursor}


def _allocate_portfolio(
    state_dir: Path, contracts: list[dict], funnel: dict, scorecard_path: Path, now: int,
) -> dict:
    try:
        scorecard = json.loads(scorecard_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("storefront_portfolio_policy_invalid") from error
    policy = scorecard.get("portfolio_policy")
    services = scorecard.get("services")
    backlog = scorecard.get("priority_backlog")
    if (not isinstance(policy, dict) or policy.get("version") != 1
            or type(policy.get("slot_limit")) is not int or policy["slot_limit"] <= 0
            or type(policy.get("minimum_views_for_retirement")) is not int
            or policy.get("short_term_zero_sales_can_retire") is not False
            or policy.get("retirement_mode") != "recoverable_unpublish_before_delete"
            or not isinstance(services, list) or not isinstance(backlog, list)
            or not isinstance(policy.get("replacement_candidates"), list)):
        raise RuntimeError("storefront_portfolio_policy_invalid")
    latest_analytics = {}
    analytics_path = state_dir / "analytics.jsonl"
    rows, analytics_error = _jsonl_rows(analytics_path)
    for row in rows:
        if str(row.get("service_id") or "").isdigit():
            latest_analytics[str(row["service_id"])] = row
    contract_by_id = {str(row["service_id"]): row for row in contracts}
    demand = {str(row.get("service_id") or ""): ((row.get("scores") or {}).get("demand"))
              for row in services if isinstance(row, dict)}
    gaps = {str(row.get("service_id") or ""): row for row in sorted(
        (row for row in backlog if isinstance(row, dict)), key=lambda row: int(row.get("priority") or 9999),
    )}
    events, funnel_error = _jsonl_rows(state_dir / "funnel-events.jsonl")
    inquiries = {}
    payments = {}
    net = {}
    for event in events:
        service_id = str(event.get("service_id") or "")
        if not service_id:
            continue
        if event.get("event_kind") == "inquiry":
            inquiries[service_id] = inquiries.get(service_id, 0) + 1
        elif event.get("event_kind") == "payment":
            payments[service_id] = payments.get(service_id, 0) + 1
            if type(event.get("net_receipt_jpy")) in {int, float}:
                net[service_id] = net.get(service_id, 0.0) + float(event["net_receipt_jpy"])
    evidence_identity = {
        "contracts": {key: value["service_version_sha256"] for key, value in sorted(contract_by_id.items())},
        "analytics": {key: {"window": value.get("window"), "metrics": value.get("metrics")}
                      for key, value in sorted(latest_analytics.items())},
        "funnel": funnel.get("cutoff_cursor"), "policy": policy,
    }
    evidence_cursor = hashlib.sha256(json.dumps(
        evidence_identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    capacity_pressure = len(contract_by_id) >= policy["slot_limit"]
    replacements = policy["replacement_candidates"]
    allocations = []
    appended = 0
    for service_id, contract in sorted(contract_by_id.items()):
        analytics = latest_analytics.get(service_id, {})
        metrics = analytics.get("metrics") if isinstance(analytics.get("metrics"), dict) else {}
        views = ((metrics.get("views") or {}).get("value"))
        purchases = ((metrics.get("purchases") or {}).get("value"))
        favorites = ((metrics.get("favorites") or {}).get("value"))
        known = type(views) is int and type(purchases) is int and type(favorites) is int
        minimum_sample = known and views >= policy["minimum_views_for_retirement"]
        weak_demand = demand.get(service_id) in {0, 1}
        replacement = next((row for row in replacements if isinstance(row, dict)
                            and row.get("replaces_service_id") == service_id), None)
        replace_ready = bool(
            minimum_sample and inquiries.get(service_id, 0) == 0 and purchases == 0
            and payments.get(service_id, 0) == 0 and weak_demand and replacement and capacity_pressure
        )
        gap = gaps.get(service_id)
        if replace_ready:
            action, reason = "REPLACE", "all_replacement_gates_met"
        elif payments.get(service_id, 0) > 0 or (known and purchases > 0):
            action, reason = "KEEP", "verified_purchase_or_payment"
        elif gap is not None:
            action = "IMPROVE"
            reason = "known_offer_gap" if minimum_sample else "minimum_sample_open_improve_known_gap"
        else:
            action, reason = "KEEP", "insufficient_evidence_for_retirement" if not known else "no_stronger_candidate"
        allocation = {
            "version": 1, "service_id": service_id,
            "listing_version": contract["service_version_sha256"], "action": action,
            "reason": reason, "evidence_cursor": evidence_cursor, "observed_at_epoch": now,
            "metrics": {"views": views, "favorites": favorites, "purchases": purchases,
                        "inquiries": inquiries.get(service_id, 0),
                        "verified_payments": payments.get(service_id, 0),
                        "verified_net_jpy": net.get(service_id, 0.0)},
            "gates": {"metrics_known": known, "minimum_sample_met": minimum_sample,
                      "weak_demand_evidence": weak_demand, "stronger_replacement_candidate": bool(replacement),
                      "slot_capacity_pressure": capacity_pressure},
            "improvement_field": gap.get("field") if gap else None,
            "rollback_version": contract["service_version_sha256"],
            "official_readback_required": action in {"IMPROVE", "RETIRE", "REPLACE"},
        }
        identity = f"storefront:portfolio:v1:{service_id}:{contract['service_version_sha256']}:{evidence_cursor}"
        allocation["allocation_key"] = hashlib.sha256(identity.encode()).hexdigest()
        appended += int(_append_key_once(
            state_dir / "portfolio-allocations.jsonl", "allocation_key", allocation,
        ))
        allocations.append(allocation)
    counts = {name: sum(row["action"] == name for row in allocations)
              for name in ("KEEP", "IMPROVE", "RETIRE", "REPLACE")}
    selected = next((row for row in allocations if row["action"] in {"REPLACE", "RETIRE"}), None)
    if selected is None:
        selected = next((row for service_id in gaps for row in allocations
                         if row["service_id"] == service_id and row["action"] == "IMPROVE"), None)
    if selected is None:
        selected = next((row for row in allocations if row["action"] == "IMPROVE"), None)
    return {"version": 1, "evidence_cursor": evidence_cursor, "service_count": len(allocations),
            "capacity": {"used": len(allocations), "limit": policy["slot_limit"],
                         "pressure": capacity_pressure}, "counts": counts, "appended": appended,
            "selected": selected, "unknown_sources": [value for value in (analytics_error, funnel_error) if value]}


def _materialize_inquiry_context(
    state_dir: Path, listing_contracts: list[dict], ack_path: Path, now: int,
) -> dict:
    events, event_error = _jsonl_rows(state_dir / "funnel-events.jsonl")
    contracts = {(str(row.get("service_id") or ""), str(row.get("service_version_sha256") or "")): row
                 for row in listing_contracts}
    appended = 0
    missing = []
    context_keys = []
    for event in events:
        if event.get("event_kind") != "inquiry" or event.get("origin") != "storefront":
            continue
        identity = (str(event.get("service_id") or ""), str(event.get("listing_version") or ""))
        contract = contracts.get(identity)
        conversation_id = str(event.get("conversation_id") or "")
        if contract is None or not conversation_id:
            missing.append({"conversation_id": conversation_id or None,
                            "service_id": identity[0] or None, "listing_version": identity[1] or None})
            continue
        offer = contract.get("offer")
        playbook = contract.get("inquiry_playbook")
        if not isinstance(offer, dict) or not isinstance(playbook, dict):
            raise RuntimeError("storefront_inquiry_context_contract_invalid")
        unsigned = {
            "version": 1, "platform": "coconala", "service_id": identity[0],
            "listing_version": identity[1], "origin": "storefront",
            "conversation_id": conversation_id, "source_event_id": event["source_event_id"],
            "offer": {"outcome": offer.get("outcome"), "inclusions": offer.get("inclusions"),
                      "deliverables": offer.get("deliverables"), "required_inputs": offer.get("required_inputs"),
                      "base_price_jpy": offer.get("base_price_jpy"), "add_ons": offer.get("options"),
                      "exclusions": offer.get("exclusions")},
            "inquiry_playbook": playbook, "listing_contract_key": contract.get("contract_key"),
        }
        canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        envelope = {**unsigned, "context_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
                    "materialized_at_epoch": now}
        envelope["context_key"] = (
            f"storefront:inquiry-context:v1:{conversation_id}:{identity[0]}:{identity[1]}"
        )
        context_keys.append(envelope["context_key"])
        appended += int(_append_key_once(
            state_dir / "inquiry-context-envelopes.jsonl", "context_key", envelope,
        ))
    acks, ack_error = _jsonl_rows(ack_path)
    consumed = {str(row.get("context_key") or "") for row in acks
                if row.get("status") == "consumed" and str(row.get("context_key") or "") in context_keys}
    return {"version": 1, "contexts": len(context_keys), "appended": appended,
            "acknowledged": len(consumed), "missing_contracts": missing,
            "negotiate_context": "ready" if context_keys and len(consumed) == len(context_keys)
            else "missing", "unknown_sources": [value for value in (event_error, ack_error) if value]}


def _load_image_contract(path: Path) -> dict:
    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("storefront_image_contract_invalid") from error
    required = {
        "version", "service_id", "field", "asset", "asset_sha256", "width", "height",
        "mime_type", "claims", "claim_source", "platform_requirement_source",
    }
    if set(contract) != required or contract.get("version") != 1:
        raise RuntimeError("storefront_image_contract_fields_invalid")
    if contract.get("service_id") != TARGET_SERVICE_ID or contract.get("field") != "image":
        raise RuntimeError("storefront_image_contract_identity_invalid")
    asset = (path.parent / str(contract.get("asset") or "")).resolve()
    try:
        asset.relative_to(path.parent.resolve())
        data = asset.read_bytes()
    except (OSError, ValueError) as error:
        raise RuntimeError("storefront_image_asset_invalid") from error
    if (len(data) > 100 * 1024 * 1024 or len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n"
            or contract.get("mime_type") != "image/png"):
        raise RuntimeError("storefront_image_asset_format_invalid")
    width, height = struct.unpack(">II", data[16:24])
    digest = hashlib.sha256(data).hexdigest()
    if (width, height) != (1220, 1016) or (contract.get("width"), contract.get("height")) != (width, height):
        raise RuntimeError("storefront_image_asset_dimensions_invalid")
    if contract.get("asset_sha256") != digest:
        raise RuntimeError("storefront_image_asset_hash_invalid")
    claims = contract.get("claims")
    if not isinstance(claims, list) or not claims or not all(isinstance(claim, str) and claim.strip() for claim in claims):
        raise RuntimeError("storefront_image_claims_invalid")
    return {**contract, "asset_path": str(asset)}


def _load_gallery_contract(path: Path) -> dict:
    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("storefront_gallery_contract_invalid") from error
    required = {
        "version", "service_id", "field", "before_image_ids", "kept_image_ids",
        "replacements", "claims", "claim_source", "platform_requirement_source",
    }
    if (set(contract) != required or contract.get("version") != 1
            or contract.get("service_id") != GALLERY_SERVICE_ID or contract.get("field") != "image"):
        raise RuntimeError("storefront_gallery_contract_fields_invalid")
    before_ids, kept_ids, replacements = (
        contract.get("before_image_ids"), contract.get("kept_image_ids"), contract.get("replacements")
    )
    if (not isinstance(before_ids, list) or len(before_ids) != 6 or len(set(before_ids)) != 6
            or not isinstance(kept_ids, list) or len(kept_ids) != 2 or not set(kept_ids) < set(before_ids)
            or not isinstance(replacements, list) or len(replacements) != 4):
        raise RuntimeError("storefront_gallery_identity_invalid")
    loaded = []
    replaced_ids = []
    for row in replacements:
        if not isinstance(row, dict) or set(row) != {
            "replace_image_id", "asset", "asset_sha256", "width", "height", "mime_type",
        }:
            raise RuntimeError("storefront_gallery_replacement_invalid")
        asset = (path.parent / str(row.get("asset") or "")).resolve()
        try:
            asset.relative_to(path.parent.resolve())
            data = asset.read_bytes()
        except (OSError, ValueError) as error:
            raise RuntimeError("storefront_gallery_asset_invalid") from error
        if (data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) > 100 * 1024 * 1024
                or row.get("mime_type") != "image/png"):
            raise RuntimeError("storefront_gallery_asset_format_invalid")
        width, height = struct.unpack(">II", data[16:24])
        if ((width, height) != (1220, 1016)
                or (row.get("width"), row.get("height")) != (width, height)
                or row.get("asset_sha256") != hashlib.sha256(data).hexdigest()):
            raise RuntimeError("storefront_gallery_asset_identity_invalid")
        replaced_ids.append(str(row.get("replace_image_id") or ""))
        loaded.append({**row, "asset_path": str(asset)})
    if set(replaced_ids) != set(before_ids) - set(kept_ids) or len(set(replaced_ids)) != 4:
        raise RuntimeError("storefront_gallery_partition_invalid")
    return {**contract, "replacements": loaded}


def _load_capability_families(path: Path) -> tuple[dict[str, str], dict[str, dict]]:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("listing_contract_families_invalid") from error
    mappings, families = config.get("service_families"), config.get("families")
    if (config.get("version") != 1 or not isinstance(mappings, dict) or not isinstance(families, dict)
            or not mappings or not families
            or any(not str(service_id).isdigit() or family not in families
                   for service_id, family in mappings.items())):
        raise RuntimeError("listing_contract_families_invalid")
    return mappings, families


def _validate_mutation_contract(contract: dict, capability_families: dict[str, str]) -> None:
    unsigned = {key: value for key, value in contract.items() if key != "contract_sha256"}
    canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    service_id = str(contract.get("service_id") or "")
    allowed_delta = contract.get("allowed_delta")
    evidence = contract.get("evidence")
    if (set(contract) != MUTATION_CONTRACT_FIELDS or contract.get("version") != 1
            or contract.get("platform") != "coconala" or not service_id.isdigit()
            or capability_families.get(service_id) != contract.get("capability_family")
            or not re.fullmatch(r"[0-9a-f]{64}", str(contract.get("precondition_listing_version_sha256") or ""))
            or contract.get("changed_field") not in MUTATION_FIELDS
            or contract.get("before_value") == contract.get("proposed_value")
            or contract.get("rollback_value") != contract.get("before_value")
            or not isinstance(allowed_delta, list) or len(allowed_delta) != 1
            or not isinstance(allowed_delta[0], str) or not allowed_delta[0].startswith("data[")
            or not isinstance(contract.get("official_readback"), dict) or not contract["official_readback"]
            or not isinstance(contract.get("success_metric"), str) or not contract["success_metric"].strip()
            or type(contract.get("observation_window_days")) is not int
            or contract["observation_window_days"] <= 0
            or not isinstance(evidence, list) or not evidence
            or not all(isinstance(value, str) and value.strip() for value in evidence)
            or contract.get("contract_sha256") != hashlib.sha256(canonical.encode()).hexdigest()):
        raise RuntimeError("storefront_mutation_contract_invalid")


def _seal_mutation_contract(unsigned: dict, capability_families: dict[str, str]) -> dict:
    canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    contract = {**unsigned, "contract_sha256": hashlib.sha256(canonical.encode()).hexdigest()}
    _validate_mutation_contract(contract, capability_families)
    return contract


def _render_text_mutation(
    path: Path, sources: list[dict], seller_snapshot: dict, capability_families: dict[str, str],
) -> dict:
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("storefront_text_mutation_spec_invalid") from error
    required = {
        "version", "platform", "service_id", "capability_family", "changed_field", "form_field",
        "before_value", "proposed_value", "rollback_value", "official_readback", "success_metric",
        "observation_window_days", "evidence",
    }
    source = next((row for row in sources if row["service_id"] == str(spec.get("service_id") or "")), None)
    if (set(spec) != required or spec.get("version") != 1 or spec.get("platform") != "coconala"
            or spec.get("changed_field") not in {"title", "body", "package", "FAQ", "price"} or source is None
            or capability_families.get(str(spec.get("service_id") or "")) != spec.get("capability_family")
            or not str(spec.get("form_field") or "").startswith("data[")
            or not all(isinstance(spec.get(key), str) and spec[key].strip()
                       for key in ("before_value", "proposed_value", "rollback_value"))
            or spec["before_value"] != spec["rollback_value"]
            or spec["before_value"] == spec["proposed_value"]
            or not isinstance(spec.get("evidence"), list) or not spec["evidence"]):
        raise RuntimeError("storefront_text_mutation_spec_fields_invalid")
    fields = {
        str(row.get("name") or ""): str(row.get("value") or "")
        for row in seller_snapshot.get("fields", []) if isinstance(row, dict)
    }
    faq_fields = {name: value for name, value in fields.items() if name.startswith("data[Faq]")}
    current_matches = (
        not faq_fields and spec["before_value"] == "FAQ_ABSENT"
        if spec["changed_field"] == "FAQ" else fields.get(spec["form_field"]) == spec["before_value"]
    )
    if (seller_snapshot.get("url") != f'https://coconala.com/mypage/services/{source["service_id"]}'
            or not current_matches):
        raise RuntimeError("storefront_text_mutation_before_not_current")
    if spec["changed_field"] == "title":
        if spec["official_readback"].get("public_title") != f'{spec["proposed_value"]}ます':
            raise RuntimeError("storefront_title_readback_contract_invalid")
    if (spec["changed_field"] == "body"
            and spec["official_readback"].get("public_body_sha256")
            != hashlib.sha256(spec["proposed_value"].encode()).hexdigest()):
        raise RuntimeError("storefront_body_readback_contract_invalid")
    if (spec["changed_field"] == "package"
            and (spec["official_readback"].get("option_title") != spec["proposed_value"]
                 or type(spec["official_readback"].get("option_price_jpy")) is not int)):
        raise RuntimeError("storefront_package_readback_contract_invalid")
    if spec["changed_field"] == "FAQ":
        question, answer = _split_faq(spec["proposed_value"])
        if spec["official_readback"] != {"question": question, "answer": answer}:
            raise RuntimeError("storefront_faq_readback_contract_invalid")
    if spec["changed_field"] == "price":
        readback = spec["official_readback"]
        proposed_jpy = readback.get("public_price_jpy")
        before_label = f'{source["price_jpy"]:,}円'
        proposed_label = f"{proposed_jpy:,}円" if type(proposed_jpy) is int and proposed_jpy > 0 else None
        options = seller_snapshot.get("select_options", {}).get(spec["form_field"], [])
        option_pairs = {
            (str(row.get("value") or ""), str(row.get("label") or ""))
            for row in options if isinstance(row, dict)
        }
        if (readback != {
                "seller_option_value": spec["proposed_value"],
                "seller_option_label": proposed_label,
                "public_price_jpy": proposed_jpy,
            }
                or (spec["before_value"], before_label) not in option_pairs
                or (spec["proposed_value"], proposed_label) not in option_pairs):
            raise RuntimeError("storefront_price_option_binding_invalid")
    unsigned = {
        "version": 1, "platform": "coconala", "service_id": source["service_id"],
        "precondition_listing_version_sha256": source["service_version_sha256"],
        "changed_field": spec["changed_field"], "before_value": spec["before_value"],
        "proposed_value": spec["proposed_value"], "allowed_delta": [spec["form_field"]],
        "rollback_value": spec["rollback_value"], "official_readback": spec["official_readback"],
        "success_metric": spec["success_metric"], "observation_window_days": spec["observation_window_days"],
        "capability_family": spec["capability_family"], "evidence": spec["evidence"],
    }
    contract = _seal_mutation_contract(unsigned, capability_families)
    before = {spec["form_field"]: spec["before_value"]}
    after = {**before, spec["form_field"]: spec["proposed_value"]}
    delta = [key for key in sorted(set(before) | set(after)) if before.get(key) != after.get(key)]
    if delta != contract["allowed_delta"]:
        raise RuntimeError("storefront_text_mutation_multi_field_delta")
    return {"version": 1, "contract": contract, "before": before, "after": after, "delta": delta, "published": False}


def _render_prepared_mutation(
    state_dir: Path, seller_snapshot: dict, service_id: str, changed_field: str,
    capability_families: dict[str, str],
) -> dict | None:
    for path in sorted((state_dir / "effect-intents").glob("*.json")):
        try:
            intent = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (intent.get("status") not in {"prepared", "confirmed"} or intent.get("service_id") != service_id
                or intent.get("changed_field") != changed_field):
            continue
        contract = intent.get("mutation_contract")
        if not isinstance(contract, dict):
            raise RuntimeError("prepared_mutation_contract_missing")
        _validate_mutation_contract(contract, capability_families)
        field = contract["allowed_delta"][0]
        values = {str(row.get("name") or ""): str(row.get("value") or "")
                  for row in seller_snapshot.get("fields") or [] if isinstance(row, dict)}
        if values.get(field) != contract["proposed_value"]:
            return None
        return {"version": 1, "contract": contract, "before": {field: contract["before_value"]},
                "after": {field: contract["proposed_value"]}, "delta": [field], "published": True}
    return None


def _load_listing_contracts(
    root: Path, observed_contracts: list[dict], families_path: Path = DEFAULT_LISTING_CONTRACT_FAMILIES,
    created_path: Path | None = None,
) -> list[dict]:
    observed = {row["service_id"]: row for row in observed_contracts}
    loaded = []
    for path in sorted(root.glob("*.json")):
        try:
            contract = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError("listing_contract_invalid") from error
        service_id = str(contract.get("service_id") or "")
        source = observed.get(service_id)
        offer = contract.get("offer")
        playbook = contract.get("inquiry_playbook")
        if (contract.get("version") != 1 or contract.get("platform") != "coconala" or source is None
                or contract.get("public_url") != source["public_url"]
                or contract.get("service_version_sha256") != source["service_version_sha256"]
                or not isinstance(offer, dict) or offer.get("base_price_jpy") != source["price_jpy"]
                or not isinstance(playbook, dict)):
            raise RuntimeError(f"listing_contract_binding_invalid:{service_id or path.name}")
        patterns = playbook.get("answer_patterns")
        required_inputs = offer.get("required_inputs")
        if (not isinstance(patterns, list) or not patterns
                or not all(isinstance(row, dict) and str(row.get("intent") or "").strip()
                           and isinstance(row.get("triggers"), list) and row["triggers"]
                           and str(row.get("response") or "").strip() for row in patterns)
                or not isinstance(required_inputs, list) or not required_inputs):
            raise RuntimeError(f"listing_contract_playbook_invalid:{service_id}")
        canonical = json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        loaded.append({
            **contract,
            "contract_key": f"storefront:contract:v1:{service_id}:{hashlib.sha256(canonical.encode()).hexdigest()}",
            "source_path": str(path.resolve()), "observed_at_epoch": int(time.time()),
        })
    explicit_ids = {row["service_id"] for row in loaded}
    mappings, families = _load_capability_families(families_path)
    if created_path is not None:
        created_rows, created_error = _jsonl_rows(created_path)
        if created_error:
            raise RuntimeError("created_listing_family_ledger_invalid")
        for row in created_rows:
            service_id = str(row.get("draft_service_id") or "")
            family_name = row.get("capability_family")
            if row.get("status") in {"published", "already_public"} and service_id.isdigit():
                if service_id in mappings:
                    continue
                if not isinstance(family_name, str) or family_name not in families:
                    raise RuntimeError(f"created_listing_family_missing:{service_id}")
                mappings[service_id] = family_name
    for source in observed_contracts:
        service_id = source["service_id"]
        if service_id in explicit_ids:
            continue
        family_name = mappings.get(service_id)
        template = families.get(family_name)
        if not isinstance(family_name, str) or not isinstance(template, dict):
            raise RuntimeError(f"listing_contract_family_missing:{service_id}")
        required = ("inclusions", "deliverables", "required_inputs", "principles", "answer_patterns")
        if any(not isinstance(template.get(key), list) or not template[key] for key in required):
            raise RuntimeError(f"listing_contract_family_invalid:{family_name}")
        contract = {
            "version": 1, "platform": "coconala", "service_id": service_id,
            "service_version_sha256": source["service_version_sha256"],
            "public_url": source["public_url"],
            "offer": {
                "outcome": source["title"], "inclusions": template["inclusions"],
                "deliverables": template["deliverables"],
                "required_inputs": template["required_inputs"],
                "base_price_jpy": source["price_jpy"], "options": [],
            },
            "inquiry_playbook": {
                "principles": template["principles"],
                "required_clarifications": template["required_inputs"],
                "answer_patterns": template["answer_patterns"],
            },
            "generated_from_family": family_name,
            "handoff_required_fields": [
                "platform", "service_id", "service_version_sha256", "conversation_id",
                "origin", "observed_at_epoch",
            ],
        }
        patterns = contract["inquiry_playbook"]["answer_patterns"]
        if not all(
            isinstance(row, dict) and str(row.get("intent") or "").strip()
            and isinstance(row.get("triggers"), list) and row["triggers"]
            and str(row.get("response") or "").strip() for row in patterns
        ):
            raise RuntimeError(f"listing_contract_family_invalid:{family_name}")
        canonical = json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        loaded.append({
            **contract,
            "contract_key": f"storefront:contract:v1:{service_id}:{hashlib.sha256(canonical.encode()).hexdigest()}",
            "source_path": str(families_path.resolve()), "observed_at_epoch": int(time.time()),
        })
    if {row["service_id"] for row in loaded} != set(observed):
        raise RuntimeError("listing_contract_inventory_incomplete")
    return loaded


def _analytics_count(body: str, label: str, unit: str) -> int:
    match = re.search(rf"{re.escape(label)}\s+([0-9０-９,，]+)\s*{re.escape(unit)}", body)
    if match is None:
        raise RuntimeError(f"official_analytics_{label}_unreadable")
    digits = match.group(1).translate(str.maketrans("０１２３４５６７８９，", "0123456789,"))
    return int(digits.replace(",", ""))


def _collect_analytics(
    state_dir: Path, evidence_dir: Path, now: int, service_ids: list[str],
    default_tab_script: Path = DEFAULT_TAB,
) -> dict:
    import listing_inventory

    if not service_ids or len(service_ids) != len(set(service_ids)) or any(not value.isdigit() for value in service_ids):
        raise RuntimeError("official_analytics_service_ids_invalid")
    analytics_path = state_dir / "analytics.jsonl"
    previous: dict[str, dict] = {}
    if analytics_path.exists():
        for line in analytics_path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise RuntimeError("official_analytics_ledger_invalid") from error
            if isinstance(row, dict) and str(row.get("service_id") or "").isdigit():
                previous[str(row["service_id"])] = row
    snapshots = []
    for service_id in service_ids:
        url = f"https://coconala.com/mypage/analytics/{service_id}"
        observed: dict = {}
        period = None
        for attempt in range(3):
            opened = subprocess.run(
                [sys.executable, str(default_tab_script), "--owner", "gig-storefront-direct",
                 "--background", "open", url], capture_output=True, text=True, check=False, timeout=30,
            )
            tab = None
            try:
                tab = json.loads(opened.stdout)
                if opened.returncode != 0 or tab.get("ok") is not True:
                    raise RuntimeError("official_analytics_tab_open_failed")
                observed = asyncio.run(listing_inventory._eval_json(
                    str(tab["ws"]), url,
                    "JSON.stringify({url:location.href,title:document.title,body:document.body?document.body.innerText.slice(0,120000):''})",
                ))
            except (KeyError, json.JSONDecodeError) as error:
                raise RuntimeError("official_analytics_tab_open_invalid") from error
            finally:
                if isinstance(tab, dict) and tab.get("target_id"):
                    try:
                        subprocess.run(
                            [sys.executable, str(default_tab_script), "--owner", "gig-storefront-direct",
                             "close", str(tab["target_id"])], capture_output=True, text=True,
                            check=False, timeout=30,
                        )
                    except subprocess.TimeoutExpired:
                        # A dead CDP endpoint must not replace the original read
                        # failure or prevent run_once from writing a failed receipt.
                        pass
            body = str(observed.get("body") or "")
            period = re.search(
                r"対象期間：([0-9]{4}/[0-9]{2}/[0-9]{2})\s*-\s*([0-9]{4}/[0-9]{2}/[0-9]{2})", body,
            )
            if observed.get("url") == url and period is not None and "サービス別分析" in body:
                break
            if attempt < 2:
                time.sleep(1)
        if period is None or observed.get("url") != url or "サービス別分析" not in body:
            raw_path = evidence_dir / f"official-analytics-{service_id}.json"
            _atomic_write(raw_path, observed)
            metrics = {
                metric: {"status": "unavailable", "value": None,
                         "reason": "official_readback_failed_after_retries"}
                for metric in ("impressions", "views", "purchases", "gross_jpy", "favorites")
            }
            identity = {
                "service_id": service_id, "window_start": None, "window_end": None,
                "metrics": metrics, "content_sha256": hashlib.sha256(body.encode()).hexdigest(),
            }
            snapshot = {
                "version": 1, "snapshot_key": "storefront:analytics:v1:" + hashlib.sha256(
                    json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest(),
                "observed_at_epoch": now, "official": False, "service_id": service_id,
                "source_url": url, "window": {"start": None, "end": None, "complete": False},
                "metrics": metrics, "content_sha256": identity["content_sha256"],
                "evidence_path": str(raw_path),
            }
            _append_key_once(analytics_path, "snapshot_key", snapshot)
            snapshots.append(snapshot)
            continue
        raw_path = evidence_dir / f"official-analytics-{service_id}.json"
        _atomic_write(raw_path, observed)
        metrics = {
            "impressions": {"status": "unavailable", "value": None,
                            "reason": "seller_success_subscription_required"},
            "views": {"status": "known", "value": _analytics_count(body, "閲覧数", "回")},
            "purchases": {"status": "known", "value": _analytics_count(body, "販売数", "件")},
            "gross_jpy": {"status": "unavailable", "value": None,
                          "reason": "service_analytics_does_not_expose_sales_amount"},
            "favorites": {"status": "known", "value": _analytics_count(body, "お気に入り数", "回")},
        }
        identity = {
            "service_id": service_id, "window_start": period.group(1), "window_end": period.group(2),
            "metrics": metrics, "content_sha256": hashlib.sha256(body.encode()).hexdigest(),
        }
        snapshot = {
            "version": 1, "snapshot_key": "storefront:analytics:v1:" + hashlib.sha256(
                json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "observed_at_epoch": now, "official": True, "service_id": service_id,
            "source_url": url, "window": {"start": period.group(1), "end": period.group(2), "complete": True},
            "metrics": metrics, "content_sha256": identity["content_sha256"], "evidence_path": str(raw_path),
        }
        _append_key_once(analytics_path, "snapshot_key", snapshot)
        snapshots.append(snapshot)
    totals = {metric: sum(int(row["metrics"][metric]["value"]) for row in snapshots
                          if type(row["metrics"][metric]["value"]) is int)
              for metric in ("views", "purchases", "favorites")}
    metric_unknown_services = {
        metric: sum(type(row["metrics"][metric]["value"]) is not int for row in snapshots)
        for metric in totals
    }
    changes = {metric: 0 for metric in totals}
    unknown_changes = 0
    for snapshot in snapshots:
        prior = previous.get(snapshot["service_id"])
        if not isinstance(prior, dict) or prior.get("window") != snapshot["window"]:
            unknown_changes += 1
            continue
        valid = True
        for metric in changes:
            before = ((prior.get("metrics") or {}).get(metric) or {}).get("value")
            after = snapshot["metrics"][metric]["value"]
            if type(before) is not int or type(after) is not int or after < before:
                valid = False
                break
            changes[metric] += after - before
        if not valid:
            unknown_changes += 1
    target = next((row for row in snapshots if row["service_id"] == TARGET_SERVICE_ID), None)
    if target is None:
        raise RuntimeError("official_analytics_target_missing")
    windows = {
        json.dumps(row.get("window"), sort_keys=True, separators=(",", ":"))
        for row in snapshots
        if isinstance(row.get("window"), dict) and row["window"].get("complete") is True
    }
    window = json.loads(next(iter(windows))) if len(windows) == 1 else None
    return {**target, "catalog_metrics": {
        "status": "current_full", "observed_at_epoch": now,
        "window": window, "coverage": {"observed": len(snapshots), "expected": len(service_ids)},
        "services_observed": len(snapshots), "totals": totals, "changes": changes,
        "metric_unknown_services": metric_unknown_services,
        "change_unknown_services": unknown_changes,
    }}


def _inquiry_windows(path: Path, service_id: str, accepted_at: int, window_days: int) -> dict:
    if not path.is_file():
        return {"status": "unknown", "reason": "reply_transcripts_missing"}
    rows = []
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    except json.JSONDecodeError:
        return {"status": "unknown", "reason": "reply_transcripts_invalid"}
    timestamps = [row.get("sent_at") for row in rows
                  if type(row.get("sent_at")) is int and row["sent_at"] >= 1_700_000_000]
    pre_start = accepted_at - window_days * 86400
    if not timestamps or min(timestamps) > pre_start:
        return {"status": "unknown", "reason": "reply_history_does_not_cover_baseline"}
    first_seen: dict[str, int] = {}
    needle = f"https://coconala.com/services/{service_id}"
    for row in rows:
        talkroom_id, sent_at = str(row.get("talkroom_id") or ""), row.get("sent_at")
        evidence = json.dumps({
            "buyer_last_said": row.get("buyer_last_said"), "conversation": row.get("conversation")
        }, ensure_ascii=False)
        if talkroom_id and type(sent_at) is int and sent_at >= 1_700_000_000 and needle in evidence:
            first_seen[talkroom_id] = min(sent_at, first_seen.get(talkroom_id, sent_at))
    eligible_at = accepted_at + window_days * 86400
    return {
        "status": "known",
        "baseline": sum(pre_start <= ts < accepted_at for ts in first_seen.values()),
        "observed": sum(accepted_at <= ts < eligible_at for ts in first_seen.values()),
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _next_hypothesis(scorecard_path: Path, experiment: dict) -> dict | None:
    try:
        rows = json.loads(scorecard_path.read_text(encoding="utf-8"))["priority_backlog"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return None
    return next((row for row in rows if isinstance(row, dict) and not (
        str(row.get("service_id")) == str(experiment.get("service_id"))
        and row.get("field") == experiment.get("changed_field")
    )), None)


def _prepare_next_hypothesis(
    scorecard_path: Path, effects_path: Path, outcomes_path: Path,
    contracts: list[dict], now: int, mutation_contracts: list[dict] | None = None,
) -> dict | None:
    try:
        backlog = json.loads(scorecard_path.read_text(encoding="utf-8"))["priority_backlog"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise RuntimeError("storefront_scorecard_invalid") from error
    if not isinstance(backlog, list):
        raise RuntimeError("storefront_scorecard_invalid")
    effects = ([json.loads(line) for line in effects_path.read_text(encoding="utf-8").splitlines() if line]
               if effects_path.exists() else [])
    outcomes = ([json.loads(line) for line in outcomes_path.read_text(encoding="utf-8").splitlines() if line]
                if outcomes_path.exists() else [])
    terminal = {row.get("experiment_key") for row in outcomes if row.get("terminal") is True}
    active = [row for row in effects if row.get("status") == "accepted"
              and row.get("effect") == 1 and row.get("experiment_key") not in terminal]
    active_services = {str(row.get("service_id") or "") for row in active}
    completed = {(str(row.get("service_id")), str(row.get("changed_field")).lower())
                 for row in effects if row.get("status") == "accepted" and row.get("effect") == 1}
    versions = {str(row["service_id"]): row["service_version_sha256"] for row in contracts}
    field_alias = {"outcome": "title", "scope": "body"}
    rendered = {
        (str(row.get("service_id") or ""), str(row.get("changed_field") or "").lower()): row
        for row in (mutation_contracts or []) if isinstance(row, dict)
    }
    candidate = None
    mutation_contract = None
    for row in backlog:
        if not isinstance(row, dict):
            continue
        service_id = str(row.get("service_id") or "")
        field = field_alias.get(str(row.get("field") or "").lower(), str(row.get("field") or "").lower())
        contract = rendered.get((service_id, field))
        contract_current = (isinstance(contract, dict)
                            and contract.get("precondition_listing_version_sha256") == versions.get(service_id))
        if (service_id in versions and service_id not in active_services
                and (service_id, field) not in completed
                and (contract_current or field in GENERATED_MUTATION_FIELDS)):
            candidate, mutation_contract = row, contract
            break
    if candidate is None:
        return None
    identity = json.dumps(candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "version": 1,
        "hypothesis_key": "storefront:hypothesis:v1:" + hashlib.sha256(identity.encode()).hexdigest(),
        "prepared_at_epoch": now,
        "service_id": str(candidate["service_id"]),
        "service_version_sha256": versions[str(candidate["service_id"])],
        "field": field_alias.get(str(candidate["field"]).lower(), str(candidate["field"])),
        "portfolio_field": str(candidate["field"]),
        "before": candidate.get("before"),
        "success_metric": candidate.get("success_metric"),
        "reason": str(candidate.get("reason") or ""),
        "executable": mutation_contract is not None,
        "guard_reason": None if mutation_contract is not None else "proposal_contract_required",
        "active_experiment_key": active[0].get("experiment_key") if active else None,
        "mutation_contract_sha256": (
            mutation_contract["contract_sha256"] if mutation_contract is not None else None
        ),
    }


def _close_outcome(
    state_dir: Path, analytics: dict, reply_transcripts: Path, scorecard_path: Path, now: int,
) -> dict | None:
    experiments_path, outcomes_path = state_dir / "experiments.jsonl", state_dir / "outcomes.jsonl"
    experiments = [json.loads(line) for line in experiments_path.read_text(encoding="utf-8").splitlines() if line]
    outcomes = ([json.loads(line) for line in outcomes_path.read_text(encoding="utf-8").splitlines() if line]
                if outcomes_path.exists() else [])
    terminal = {row.get("experiment_key") for row in outcomes if row.get("terminal") is True}
    experiment = next((row for row in experiments
                       if row.get("status") == "accepted" and row.get("experiment_key") not in terminal), None)
    if experiment is None:
        return None
    window_days = experiment.get("observation_window_days")
    accepted_at = experiment.get("accepted_at_epoch")
    if type(window_days) is not int or window_days not in {7, 14} or type(accepted_at) is not int:
        raise RuntimeError("experiment_window_invalid")
    eligible_at = accepted_at + window_days * 86400
    inquiry = {"status": "not_evaluated"}
    decision, terminal_state, reason = "NO_OP", False, "measurement_window_ineligible"
    if now >= eligible_at:
        inquiry = _inquiry_windows(
            reply_transcripts, str(experiment.get("service_id") or ""), accepted_at, window_days,
        )
        if experiment.get("success_metric") != "inquiries":
            terminal_state, reason = True, "target_metric_evidence_unavailable"
        elif inquiry.get("status") != "known":
            terminal_state, reason = True, str(inquiry.get("reason") or "inquiry_evidence_unknown")
        elif inquiry["observed"] > inquiry["baseline"]:
            decision, terminal_state, reason = "KEEP", True, "inquiries_improved"
        elif inquiry["baseline"] > 0 and inquiry["observed"] < inquiry["baseline"]:
            decision, terminal_state, reason = "REVERT", True, "inquiries_declined"
        else:
            decision, terminal_state, reason = "NO_OP", True, "no_measured_inquiry_change"
    evidence = {
        "experiment_sha256": hashlib.sha256(json.dumps(
            experiment, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest(),
        "analytics_snapshot_key": analytics["snapshot_key"],
        "inquiry_source_sha256": inquiry.get("source_sha256"),
    }
    identity = json.dumps({
        "experiment_key": experiment["experiment_key"], "decision": decision,
        "terminal": terminal_state, "reason": reason, "evidence": evidence,
    }, sort_keys=True, separators=(",", ":"))
    receipt = {
        "version": 1, "outcome_key": "storefront:outcome:v1:" + hashlib.sha256(identity.encode()).hexdigest(),
        "observed_at_epoch": now, "experiment_key": experiment["experiment_key"],
        "service_id": experiment["service_id"], "decision": decision, "terminal": terminal_state,
        "reason": reason, "eligible_at_epoch": eligible_at, "metric": experiment.get("success_metric"),
        "baseline": inquiry.get("baseline"), "observed": inquiry.get("observed"), "evidence": evidence,
        "next_hypothesis": _next_hypothesis(scorecard_path, experiment) if terminal_state else None,
        "effect": 0,
    }
    _append_key_once(outcomes_path, "outcome_key", receipt)
    return receipt


def _service_contract(source: dict, observed_at: str) -> dict:
    service_id = str(source.get("service_id") or "")
    public_text = str(source.get("public_text") or "")
    public_hash = str(source.get("public_content_sha256") or "")
    public_headings = {line.strip() for line in public_text.splitlines()}
    contract = {
        "service_id": service_id, "public_url": str(source.get("public_url") or ""),
        "title": str(source.get("title") or "").strip(),
        "state": source.get("state"), "price_jpy": source.get("price_jpy"),
        "category": str(source.get("category") or "").strip(),
        "public_content_sha256": public_hash,
    }
    if (
        not service_id.isdigit() or contract["public_url"] != f"https://coconala.com/services/{service_id}"
        or not contract["title"] or contract["state"] not in {"公開中", "非公開", "下書き"}
        or type(contract["price_jpy"]) is not int or contract["price_jpy"] < 0
        or not contract["category"] or not public_text
        or not {"サービス内容", "購入にあたってのお願い"} <= public_headings
        or public_hash != hashlib.sha256(public_text.encode()).hexdigest()
    ):
        raise RuntimeError("official_service_contract_invalid")
    canonical = json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "version": 1, **contract, "scope_text": public_text,
        "service_version_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "observed_at": observed_at,
    }


def _append_contract_once(path: Path, contract: dict) -> bool:
    key = (contract["service_id"], contract["service_version_sha256"])
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise RuntimeError("offer_contract_ledger_invalid") from error
            if (row.get("service_id"), row.get("service_version_sha256")) == key:
                return False
    _append(path, contract)
    return True


def _lease(script: Path, command: str, task: str, lease: dict | None = None) -> dict:
    argv = [sys.executable, str(script), command, task]
    if lease is not None:
        argv.extend(("--token", str(lease["token"]), "--generation", str(lease["generation"])))
    completed = subprocess.run(argv, capture_output=True, text=True, check=False, timeout=45)
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"lease_{command}_invalid_json") from error
    if completed.returncode != 0 or result.get("ok") is not True:
        raise RuntimeError(f"lease_{command}_failed:{result.get('reason') or completed.returncode}")
    return result


def _receipt(pass_id: str, *, status: str, reason: str | None = None, **counts: object) -> dict:
    row = {
        "version": 1,
        "pass_id": pass_id,
        "observed_at_epoch": int(time.time()),
        "status": status,
        "decision": "no_op" if status == "completed" else None,
        "reason": reason,
        "actionable": 0,
        "effect": 0,
        "readback": 0,
        "duplicate": 0,
        **counts,
    }
    return row


def _collect_competitors(ws_url: str, evidence_dir: Path, own_ids: set[str]) -> dict:
    import listing_inventory

    rows = []
    for source_type, requested_url in COMPETITOR_SOURCES:
        requested = urlsplit(requested_url)
        requested_id = requested.path.removeprefix("/services/") if source_type == "service" else None
        if requested_id in own_ids:
            raise RuntimeError("competitor_source_is_own_service")
        observed = asyncio.run(listing_inventory._eval_json(
            ws_url,
            requested_url,
            "JSON.stringify({url:location.href,title:document.title,body:document.body ? document.body.innerText.slice(0,120000) : ''})",
        ))
        final_url = str(observed.get("url") or "")
        final = urlsplit(final_url)
        body = str(observed.get("body") or "")
        if final.scheme != "https" or final.hostname not in {"coconala.com", "www.coconala.com"}:
            raise RuntimeError("competitor_source_not_official")
        if source_type == "service" and final.path.rstrip("/") != requested.path:
            raise RuntimeError("competitor_service_redirected")
        if not body.strip():
            raise RuntimeError("competitor_source_empty")
        digest = hashlib.sha256(body.encode()).hexdigest()
        path = evidence_dir / f"competitor-{source_type}-{hashlib.sha256(requested_url.encode()).hexdigest()[:12]}.json"
        row = {
            "official": True,
            "observed": True,
            "source_type": source_type,
            "requested_url": requested_url,
            "url": final_url,
            "title": str(observed.get("title") or ""),
            "body": body,
            "content_sha256": digest,
            "observed_at_epoch": int(time.time()),
        }
        _atomic_write(path, row)
        rows.append({"source_type": source_type, "url": final_url, "path": str(path), "content_sha256": digest})
    manifest = {"version": 1, "sources": rows}
    _atomic_write(evidence_dir / "competitor-manifest.json", manifest)
    return manifest


def _observe_own_page(
    ws_url: str, evidence_dir: Path, name: str = "own-candidate.json",
    service_id: str = TARGET_SERVICE_ID,
) -> dict:
    import listing_inventory

    if not service_id.isdigit():
        raise RuntimeError("own_candidate_service_id_invalid")
    url = f"https://coconala.com/services/{service_id}"
    expression = """(async () => {
          const collapsedBodies = [...document.querySelectorAll(
            'button.c-contentsCollapse_readMoreButton'
          )];
          collapsedBodies.forEach(control => control.click());
          const closed = [...document.querySelectorAll(
            'a[aria-controls^="serviceContentsFaqAnswer"][aria-expanded="false"]'
          )];
          closed.forEach(control => control.click());
          if (collapsedBodies.length || closed.length) await new Promise(resolve => setTimeout(resolve, 500));
          const serviceImageIds = [...new Set([...document.querySelectorAll('.c-contentsImagesProduction img')]
            .map(image => (image.currentSrc || image.src || '').match(/service_images\\/original\\/([^/?]+)/)?.[1])
            .filter(Boolean))];
          return JSON.stringify({url:location.href,title:document.title,
            body:document.body ? document.body.innerText.slice(0,120000) : '',service_image_ids:serviceImageIds});
        })()"""
    observed = {}
    for attempt in range(3):
        observed = asyncio.run(listing_inventory._eval_json(ws_url, url, expression))
        body = str(observed.get("body") or "")
        image_ids = observed.get("service_image_ids")
        valid = (
            urlsplit(str(observed.get("url") or "")).path.rstrip("/") == f"/services/{service_id}"
            and bool(body.strip()) and isinstance(image_ids, list)
            and all(isinstance(value, str) and value for value in image_ids)
            and len(set(image_ids)) == len(image_ids)
        )
        if valid:
            break
        if attempt < 2:
            time.sleep(2)
    else:
        raise RuntimeError("own_candidate_readback_invalid")
    row = {
        "official": True,
        "observed": True,
        "service_id": service_id,
        "url": str(observed["url"]),
        "title": str(observed.get("title") or ""),
        "body": body,
        "service_image_ids": image_ids,
        "service_image_count": len(image_ids),
        "content_sha256": hashlib.sha256(body.encode()).hexdigest(),
        "listing_version_sha256": hashlib.sha256(json.dumps(
            {"body": body, "service_image_ids": image_ids}, ensure_ascii=False,
            sort_keys=True, separators=(",", ":"),
        ).encode()).hexdigest(),
        "observed_at_epoch": int(time.time()),
    }
    _atomic_write(evidence_dir / name, row)
    return row


def _judgement_prompt(own_page: dict, manifest: dict, capability_paths: set[str]) -> str:
    competitors = []
    for reference in manifest["sources"]:
        row = json.loads(Path(reference["path"]).read_text(encoding="utf-8"))
        competitors.append({"path": reference["path"], "url": row["url"], "body": row["body"][:12000]})
    capabilities = []
    for raw_path in sorted(capability_paths):
        path = Path(raw_path)
        capabilities.append({"path": raw_path, "content": path.read_text(encoding="utf-8")[:8000]})
    context = {
        "own": {"service_id": TARGET_SERVICE_ID, "url": own_page["url"], "body": own_page["body"][:24000]},
        "competitors": competitors,
        "capability_evidence": capabilities,
    }
    return """Judge one Coconala Storefront experiment from the JSON evidence below.
Return only the strict schema object. Model judgement may choose change or no_op; code owns every
mechanical guard and no seller effect occurs in this turn. The only supported change is service
4330368 field FAQ. Its exact current sentinel is FAQ_ABSENT only when the own public body has no
よくある質問 section. Propose one original Japanese FAQ grounded in this account's capability and
generalized competitor structure. Do not copy competitor prose, images, reviews, sales, or claims.
For change, cite exact supplied paths, choose one metric and 7 or 14 days, and return
experiment_key=null for parent derivation. For no_op, all change fields/metric/window/key are null
and no_op_reason is nonempty.\nCONTEXT_JSON=""" + json.dumps(context, ensure_ascii=False, separators=(",", ":"))


def _invoke_judge(
    *, runner: Path, schema: Path, workdir: Path, evidence_dir: Path,
    own_page: dict, manifest: dict, capability_paths: set[str], timeout_seconds: int,
) -> dict:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    child_env = os.environ.copy()
    completed = subprocess.run(
        [sys.executable, str(runner), "--task-class", "composition-agent", "--prompt-stdin",
         "--schema", str(schema), "--evidence-dir", str(evidence_dir),
         "--task-label", "gig-storefront-judge", "--loop", "gig", "--workdir", str(workdir),
         "--timeout-seconds", str(timeout_seconds)],
        input=_judgement_prompt(own_page, manifest, capability_paths),
        text=True,
        capture_output=True,
        env=child_env,
        timeout=timeout_seconds + 30,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()[-400:]
        raise RuntimeError(f"storefront_judge_failed:{completed.returncode}:{detail}")
    try:
        summary_path = evidence_dir / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        result_path = Path(str(summary["result_path"])).resolve()
        result_path.relative_to(evidence_dir.resolve())
        if summary.get("status") != "success" or min(summary_path.stat().st_mtime, result_path.stat().st_mtime) < started:
            raise ValueError("stale_or_unsuccessful")
        value = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise RuntimeError("storefront_judge_evidence_invalid") from error
    if not isinstance(value, dict):
        raise RuntimeError("storefront_judge_result_not_object")
    return value


def _proposal_prompt(
    hypothesis: dict, source: dict, seller_snapshot: dict, family_name: str, family: dict,
    manifest: dict, capability_paths: set[str],
) -> tuple[str, set[str]]:
    competitor_rows = []
    allowed_refs = {
        f"official:seller-form:{source['service_id']}",
        f"official:offer-contract:{source['service_id']}:{source['service_version_sha256']}",
        f"owned:capability-family:{family_name}",
    }
    for reference in manifest.get("sources", []):
        path = str(reference.get("path") or "")
        try:
            row = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError("storefront_proposal_competitor_evidence_invalid") from error
        allowed_refs.add(path)
        competitor_rows.append({"evidence_ref": path, "url": row.get("url"),
                                "body": str(row.get("body") or "")[:8000]})
    capabilities = []
    for raw_path in sorted(capability_paths):
        path = Path(raw_path)
        if not path.is_file():
            continue
        allowed_refs.add(raw_path)
        capabilities.append({"evidence_ref": raw_path,
                             "content": path.read_text(encoding="utf-8")[:6000]})
    context = {
        "gap": hypothesis,
        "official_offer": source,
        "seller_form": seller_snapshot,
        "capability_family": {"name": family_name, "contract": family},
        "competitors": competitor_rows,
        "owned_capability_evidence": capabilities,
        "allowed_evidence_refs": sorted(allowed_refs),
    }
    prompt = """Create exactly one Coconala Storefront improvement proposal from CONTEXT_JSON.
Return only the strict schema object. The selected service_id, changed_field and success_metric must
exactly equal gap.service_id, gap.field and gap.success_metric. Use only claims supported by the
owned capability family/offer. Competitors supply generalized structure only: never copy their
wording, images, reviews, sales, speed, guarantees or results. evidence entries must be exact values
from allowed_evidence_refs and must include the official offer ref and owned capability-family ref.
gap.executable=false with guard_reason=proposal_contract_required means this proposal must create the
missing contract; it is not a no-op reason and mutation_contract_sha256 is intentionally absent.
For title, return only the seller-form title stem (Coconala appends ます). For body, return a complete
Japanese replacement with outcome, inclusions, exclusions, required inputs and support boundary.
For image, proposed_value must be exactly three non-empty lines: a short headline, a supporting line,
then two or three short badges separated by `｜`. Use only supported offer/capability claims; do not put
price, delivery speed, review count, sales count, guarantees or competitor wording in the image.
For package, return one precise option title and proposed_price_jpy from the official option-price
select values visible in seller_form; for FAQ use `Q. ...\nA. ...`; for price return an exact seller
base-price select option value visible in seller_form. Change one field only. Choose change only when the
proposal is fully supported; otherwise choose no_op with all nullable change fields null and a concrete
no_op_reason. observation_window_days is 7 or 14. Do not claim that the proposal itself caused KPI
improvement.\nCONTEXT_JSON=""" + json.dumps(context, ensure_ascii=False, separators=(",", ":"))
    return prompt, allowed_refs


def _invoke_proposal(
    *, runner: Path, schema: Path, workdir: Path, evidence_dir: Path, hypothesis: dict,
    source: dict, seller_snapshot: dict, family_name: str, family: dict, manifest: dict,
    capability_paths: set[str], timeout_seconds: int,
) -> tuple[dict, dict, set[str]]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    prompt, allowed_refs = _proposal_prompt(
        hypothesis, source, seller_snapshot, family_name, family, manifest, capability_paths,
    )
    started = time.time()
    completed = subprocess.run(
        [sys.executable, str(runner), "--task-class", "storefront-proposal-agent", "--prompt-stdin",
         "--schema", str(schema), "--evidence-dir", str(evidence_dir),
         "--task-label", "gig-storefront-proposal", "--loop", "gig-storefront",
         "--workdir", str(workdir), "--timeout-seconds", str(timeout_seconds)],
        input=prompt, text=True, capture_output=True, env=os.environ.copy(),
        timeout=timeout_seconds + 30, check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()[-400:]
        raise RuntimeError(f"storefront_proposal_failed:{completed.returncode}:{detail}")
    try:
        summary_path = evidence_dir / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        result_path = Path(str(summary["result_path"])).resolve()
        result_path.relative_to(evidence_dir.resolve())
        if (summary.get("status") != "success"
                or summary.get("task_class") != "storefront-proposal-agent"
                or summary.get("selected_provider") != "codex"
                or summary.get("selected_model") != "gpt-5.6-terra"
                or summary.get("selected_effort") != "medium"
                or min(summary_path.stat().st_mtime, result_path.stat().st_mtime) < started):
            raise ValueError("stale_or_wrong_route")
        proposal = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise RuntimeError("storefront_proposal_evidence_invalid") from error
    route = {
        "task_class": summary["task_class"], "route": summary.get("route"),
        "provider": summary["selected_provider"], "model": summary["selected_model"],
        "effort": summary["selected_effort"], "summary_path": str(summary_path),
        "summary_sha256": hashlib.sha256(summary_path.read_bytes()).hexdigest(),
    }
    return proposal, route, allowed_refs


def _render_generated_image_asset(proposed: str, service_id: str, evidence_dir: Path) -> dict:
    from PIL import Image, ImageDraw, ImageFont

    lines = [line.strip() for line in proposed.splitlines() if line.strip()]
    if len(lines) != 3 or not (2 <= len(lines[0]) <= 28 and 2 <= len(lines[1]) <= 48):
        raise RuntimeError("storefront_generated_image_copy_invalid")
    badges = [value.strip() for value in lines[2].split("｜") if value.strip()]
    if len(badges) not in {2, 3} or any(len(value) > 24 for value in badges):
        raise RuntimeError("storefront_generated_image_badges_invalid")
    font_result = subprocess.run(
        ["fc-match", "-f", "%{file}", "Hiragino Sans"], capture_output=True, text=True,
        check=False, timeout=10,
    )
    font_path = Path(font_result.stdout.strip())
    if font_result.returncode != 0 or not font_path.is_file():
        raise RuntimeError("storefront_generated_image_font_missing")
    image = Image.new("RGB", (1220, 1016), "#111c50")
    draw = ImageDraw.Draw(image)
    for y in range(1016):
        ratio = y / 1015
        draw.line((0, y, 1220, y), fill=(17 + int(6 * ratio), 28 - int(16 * ratio), 80 - int(38 * ratio)))
    draw.rounded_rectangle((70, 70, 1150, 946), radius=42, outline="#6f83ff", width=3)

    def fitted(text: str, maximum: int, start: int) -> ImageFont.FreeTypeFont:
        size = start
        while size >= 28:
            font = ImageFont.truetype(str(font_path), size)
            if draw.textbbox((0, 0), text, font=font)[2] <= maximum:
                return font
            size -= 2
        raise RuntimeError("storefront_generated_image_text_too_wide")

    headline_font = fitted(lines[0], 1000, 82)
    support_font = fitted(lines[1], 1000, 42)
    draw.text((110, 260), lines[0], font=headline_font, fill="white")
    draw.text((112, 400), lines[1], font=support_font, fill="#dce3ff")
    badge_size = 27
    while badge_size >= 18:
        badge_font = ImageFont.truetype(str(font_path), badge_size)
        badge_widths = [draw.textbbox((0, 0), badge, font=badge_font)[2] + 70 for badge in badges]
        if sum(badge_widths) + 24 * (len(badges) - 1) <= 1020:
            break
        badge_size -= 1
    else:
        raise RuntimeError("storefront_generated_image_badges_too_wide")
    x = 110
    for index, (badge, width) in enumerate(zip(badges, badge_widths)):
        draw.rounded_rectangle((x, 600, x + width, 670), radius=35,
                               fill=("#ef4f55", "#35b777", "#7657db")[index])
        draw.text((x + 35, 618), badge, font=badge_font, fill="white")
        x += width + 24
    path = evidence_dir / f"generated-{service_id}-hero.png"
    image.save(path, format="PNG", optimize=False)
    data = path.read_bytes()
    return {"asset_sha256": hashlib.sha256(data).hexdigest(), "asset_path": str(path.resolve())}


def _create_proposal_prompt(
    source: dict, family_name: str, family: dict, demand: dict,
    capability_paths: set[str], catalog_titles: list[str],
) -> tuple[str, set[str]]:
    offer_ref = f"official:offer-contract:{source['service_id']}:{source['service_version_sha256']}"
    family_ref = f"owned:capability-family:{family_name}"
    demand_ref = str(demand["evidence_path"])
    allowed_refs = {offer_ref, family_ref, demand_ref}
    capabilities = []
    for raw_path in sorted(capability_paths):
        path = Path(raw_path)
        if path.is_file():
            allowed_refs.add(raw_path)
            capabilities.append({"evidence_ref": raw_path,
                                 "content": path.read_text(encoding="utf-8")[:6000]})
    context = {
        "source_offer": source,
        "capability_family": {"name": family_name, "contract": family},
        "demand": demand,
        "owned_capability_evidence": capabilities,
        "current_catalog_titles": catalog_titles,
        "allowed_evidence_refs": sorted(allowed_refs),
    }
    prompt = """Create one distinct Coconala service proposal from CONTEXT_JSON and return only the
strict schema object. The source_service_id must equal source_offer.service_id. The new service must
sell a narrower buyer-visible outcome supported by the same owned capability family; it must not
duplicate or merely rephrase any current_catalog_titles. Use the demand page only as demand evidence,
never copy seller wording, reviews, sales, guarantees or unsupported claims. Include exact evidence
refs for the official offer, owned family and demand evidence. The title_stem excludes the final
Japanese `ます`. head must state outcome, exact inclusions, exclusions, required inputs and support
boundary. body must state purchase inputs and unsupported work. image_copy is exactly three non-empty
lines: headline, supporting line, and two or three short badges separated by `｜`; do not include price,
speed, sales, reviews or guarantees. Price and paid option must be conservative. Choose create only
when the proposal is clearly distinct and supported. Otherwise choose no_op, set every nullable
commercial field and metric/window to null, and provide no_op_reason. Do not claim that creation itself
caused KPI improvement.\nCONTEXT_JSON=""" + json.dumps(context, ensure_ascii=False, separators=(",", ":"))
    return prompt, allowed_refs


def _invoke_create_proposal(
    *, runner: Path, schema: Path, workdir: Path, evidence_dir: Path, source: dict,
    family_name: str, family: dict, demand: dict, capability_paths: set[str],
    catalog_titles: list[str], timeout_seconds: int,
) -> tuple[dict, dict, set[str]]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    prompt, allowed_refs = _create_proposal_prompt(
        source, family_name, family, demand, capability_paths, catalog_titles,
    )
    started = time.time()
    completed = subprocess.run(
        [sys.executable, str(runner), "--task-class", "storefront-proposal-agent", "--prompt-stdin",
         "--schema", str(schema), "--evidence-dir", str(evidence_dir),
         "--task-label", "gig-storefront-create", "--loop", "gig-storefront",
         "--workdir", str(workdir), "--timeout-seconds", str(timeout_seconds)],
        input=prompt, text=True, capture_output=True, env=os.environ.copy(),
        timeout=timeout_seconds + 30, check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()[-400:]
        raise RuntimeError(f"storefront_create_proposal_failed:{completed.returncode}:{detail}")
    try:
        summary_path = evidence_dir / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        result_path = Path(str(summary["result_path"])).resolve()
        result_path.relative_to(evidence_dir.resolve())
        if (summary.get("status") != "success"
                or summary.get("task_class") != "storefront-proposal-agent"
                or summary.get("selected_provider") != "codex"
                or summary.get("selected_model") != "gpt-5.6-terra"
                or summary.get("selected_effort") != "medium"
                or min(summary_path.stat().st_mtime, result_path.stat().st_mtime) < started):
            raise ValueError("stale_or_wrong_route")
        proposal = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise RuntimeError("storefront_create_proposal_evidence_invalid") from error
    route = {"task_class": summary["task_class"], "route": summary.get("route"),
             "provider": summary["selected_provider"], "model": summary["selected_model"],
             "effort": summary["selected_effort"], "summary_path": str(summary_path)}
    return proposal, route, allowed_refs


def _seal_create_contract(
    proposal: dict, *, source: dict, family_name: str, allowed_refs: set[str],
    blueprint: dict, seller_snapshot: dict, draft_service_id: str, evidence_dir: Path,
) -> dict | None:
    nullable = ("source_service_id", "title_stem", "catchphrase", "head", "body",
                "display_price_jpy", "delivery_days", "paid_option_title",
                "paid_option_price_jpy", "image_copy", "success_metric",
                "observation_window_days")
    if proposal.get("decision") == "no_op":
        if any(proposal.get(key) is not None for key in nullable) or not str(
                proposal.get("no_op_reason") or "").strip():
            raise RuntimeError("storefront_create_noop_invalid")
        return None
    evidence = proposal.get("evidence")
    required = {
        f"official:offer-contract:{source['service_id']}:{source['service_version_sha256']}",
        f"owned:capability-family:{family_name}", str(blueprint["demand_evidence_path"]),
    }
    if (proposal.get("decision") != "create"
            or proposal.get("source_service_id") != source["service_id"]
            or proposal.get("success_metric") not in {"views_to_inquiry", "views_to_purchase"}
            or proposal.get("observation_window_days") not in {7, 14}
            or proposal.get("no_op_reason") is not None
            or not isinstance(evidence, list) or not required <= set(evidence)
            or not set(evidence) <= allowed_refs or not draft_service_id.isdigit()):
        raise RuntimeError("storefront_create_identity_invalid")
    title_stem = str(proposal.get("title_stem") or "").strip()
    catchphrase = str(proposal.get("catchphrase") or "").strip()
    head = str(proposal.get("head") or "").strip()
    body = str(proposal.get("body") or "").strip()
    option_title = str(proposal.get("paid_option_title") or "").strip()
    image_copy = str(proposal.get("image_copy") or "").strip()
    if (not title_stem or len(title_stem) > 23 or not 15 <= len(catchphrase) <= 30
            or not head or len(head) > 1000 or not body or len(body) > 500
            or not option_title or len(option_title) > 60
            or len([line for line in image_copy.splitlines() if line.strip()]) != 3
            or "｜" not in image_copy.splitlines()[-1]):
        raise RuntimeError("storefront_create_content_invalid")
    select_options = seller_snapshot.get("select_options") or {}
    display_price = proposal.get("display_price_jpy")
    price_option = next((row for row in select_options.get("data[Service][price]", [])
                         if str(row.get("label") or "").replace(",", "") == f"{display_price}円"), None)
    option_price = proposal.get("paid_option_price_jpy")
    option_price_row = next((row for row in select_options.get("data[Option][0][price]", [])
                             if str(row.get("label") or "").replace(",", "") == f"{option_price}円"), None)
    if type(display_price) is not int or price_option is None or type(option_price) is not int or option_price_row is None:
        raise RuntimeError("storefront_create_price_invalid")
    asset = _render_generated_image_asset(image_copy, draft_service_id, evidence_dir)
    unsigned = {
        "version": 1, "platform": "coconala",
        "candidate_key": f"storefront:create:v1:{hashlib.sha256(title_stem.encode()).hexdigest()}",
        "draft_service_id": draft_service_id,
        "draft_url": f"https://coconala.com/mypage/services/{draft_service_id}",
        "expected_public_url": f"https://coconala.com/services/{draft_service_id}",
        "origin": "storefront", "demand_evidence": blueprint["demand_evidence"],
        "capability_evidence": {"family": family_name, "source_service_id": source["service_id"]},
        "hero_image_contract": asset["asset_path"], "category": blueprint["category"],
        "public_fields": {"overview_input": title_stem, "expected_title": f"{title_stem}ます",
                          "catchphrase": catchphrase, "head": head,
                          "price_option_value": str(price_option["value"]),
                          "display_price_jpy": display_price,
                          "delivery_days": int(proposal["delivery_days"]), "order_limit": 1,
                          "body": body, "accept_estimates": True, "estimate_required": False},
        "category_specific": blueprint["category_specific"], "subscription": blueprint["subscription"],
        "paid_options": [{"title": option_title, "price_jpy": option_price, "opened": "1"}],
        "publication_gate": blueprint["publication_gate"], "proposal_evidence": evidence,
        "success_metric": proposal["success_metric"],
        "observation_window_days": proposal["observation_window_days"],
    }
    canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {**unsigned, "contract_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
            "hero_image": {"version": 1, "service_id": draft_service_id, "field": "image",
                           "mime_type": "image/png", "width": 1220, "height": 1016,
                           "claims": image_copy.splitlines(), **asset}}


def _seal_generated_proposal(
    proposal: dict, hypothesis: dict, source: dict, seller_snapshot: dict,
    family_name: str, capability_families: dict[str, str], allowed_refs: set[str],
    evidence_dir: Path, public_snapshot: dict,
) -> dict | None:
    if proposal.get("decision") == "no_op":
        if (any(proposal.get(key) is not None for key in (
                "service_id", "changed_field", "proposed_value", "success_metric",
                "observation_window_days", "proposed_price_jpy"))
                or not str(proposal.get("no_op_reason") or "").strip()):
            raise RuntimeError("storefront_generated_noop_invalid")
        return None
    field = str(hypothesis.get("field") or "")
    service_id = str(hypothesis.get("service_id") or "")
    evidence = proposal.get("evidence")
    required_refs = {
        f"official:offer-contract:{service_id}:{source['service_version_sha256']}",
        f"owned:capability-family:{family_name}",
    }
    if (proposal.get("decision") != "change" or proposal.get("service_id") != service_id
            or proposal.get("changed_field") != field
            or proposal.get("success_metric") != hypothesis.get("success_metric")
            or proposal.get("observation_window_days") not in {7, 14}
            or proposal.get("no_op_reason") is not None
            or not isinstance(evidence, list) or not evidence
            or not set(evidence) <= allowed_refs or not required_refs <= set(evidence)
            or capability_families.get(service_id) != family_name):
        raise RuntimeError("storefront_generated_proposal_identity_invalid")
    proposed = str(proposal.get("proposed_value") or "").strip()
    if field == "image":
        if (hypothesis.get("before") != 0 or not proposed
                or public_snapshot.get("service_id") != service_id
                or public_snapshot.get("service_image_ids") != []
                or not re.fullmatch(r"[0-9a-f]{64}", str(public_snapshot.get("listing_version_sha256") or ""))):
            raise RuntimeError("storefront_generated_image_before_invalid")
        asset = _render_generated_image_asset(proposed, service_id, evidence_dir)
        return _seal_mutation_contract({
            "version": 1, "platform": "coconala", "service_id": service_id,
            "precondition_listing_version_sha256": source["service_version_sha256"],
            "changed_field": "image", "before_value": {"service_image_ids": []},
            "proposed_value": asset,
            "allowed_delta": ["data[UploadedFile][n*][image_files]"],
            "rollback_value": {"service_image_ids": []},
            "official_readback": {"service_image_count": 1},
            "success_metric": proposal["success_metric"],
            "observation_window_days": proposal["observation_window_days"],
            "capability_family": family_name, "evidence": evidence,
        }, capability_families)
    fields = {str(row.get("name") or ""): row for row in seller_snapshot.get("fields", [])
              if isinstance(row, dict)}
    if field == "title":
        form_field = "data[Service][overview]"
    elif field == "body":
        form_field = "data[Service][head]"
    elif field == "price":
        form_field = "data[Service][price]"
    elif field == "package":
        if seller_snapshot.get("package_slot_added") is not True:
            raise RuntimeError("storefront_generated_package_requires_absent_slot")
        if len(proposed) > 60:
            raise RuntimeError("storefront_generated_package_title_too_long")
        form_field = "data[Option][0]"
    elif field == "FAQ":
        if any(name.startswith("data[Faq]") for name in fields):
            raise RuntimeError("storefront_generated_faq_requires_absent_slot")
        form_field = "data[Faq][0]"
    else:
        raise RuntimeError("storefront_generated_field_unsupported")
    before = ("FAQ_ABSENT" if field == "FAQ" else "PACKAGE_ABSENT" if field == "package"
              else str((fields.get(form_field) or {}).get("value") or ""))
    maximum = (fields.get(form_field) or {}).get("maxLength")
    if (not proposed or proposed == before or (type(maximum) is int and maximum > 0 and len(proposed) > maximum)):
        raise RuntimeError("storefront_generated_value_invalid")
    if field == "title":
        readback = {"public_title": f"{proposed}ます"}
    elif field == "body":
        readback = {"public_body_sha256": hashlib.sha256(proposed.encode()).hexdigest()}
    elif field == "FAQ":
        question, answer = _split_faq(proposed)
        readback = {"question": question, "answer": answer}
    elif field == "package":
        price_jpy = proposal.get("proposed_price_jpy")
        options = seller_snapshot.get("select_options", {}).get("data[Option][0][price]", [])
        selected = next((row for row in options
                         if str(row.get("value") or "") == str(price_jpy)), None)
        if (type(price_jpy) is not int or selected is None
                or str(selected.get("label") or "") != f"{price_jpy:,}円"):
            raise RuntimeError("storefront_generated_package_price_invalid")
        proposed = {"title": proposed, "price_jpy": price_jpy}
        readback = {"option_title": proposed["title"], "option_price_jpy": price_jpy}
    else:
        options = seller_snapshot.get("select_options", {}).get(form_field, [])
        selected = next((row for row in options if str(row.get("value") or "") == proposed), None)
        label = str((selected or {}).get("label") or "")
        match = re.fullmatch(r"([0-9,]+)円", label)
        if selected is None or match is None:
            raise RuntimeError("storefront_generated_price_option_invalid")
        readback = {"seller_option_value": proposed, "seller_option_label": label,
                    "public_price_jpy": int(match.group(1).replace(",", ""))}
    return _seal_mutation_contract({
        "version": 1, "platform": "coconala", "service_id": service_id,
        "precondition_listing_version_sha256": source["service_version_sha256"],
        "changed_field": field, "before_value": before, "proposed_value": proposed,
        "allowed_delta": [form_field], "rollback_value": before, "official_readback": readback,
        "success_metric": proposal["success_metric"],
        "observation_window_days": proposal["observation_window_days"],
        "capability_family": family_name, "evidence": evidence,
    }, capability_families)


def _experiment_key(service_id: str, field: str, proposed: object) -> str:
    canonical = (proposed.strip() if isinstance(proposed, str)
                 else json.dumps(proposed, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    return f"storefront:v1:{service_id}:{field}:{digest}"


def _image_mutation_contract(
    hypothesis: dict, own_page: dict, asset: dict, capability_families: dict[str, str],
) -> dict:
    if (hypothesis.get("service_id") != TARGET_SERVICE_ID or hypothesis.get("field") != "image"
            or hypothesis.get("before") != 0 or hypothesis.get("executable") is not True
            or hypothesis.get("success_metric") != "views_to_inquiry"):
        raise RuntimeError("storefront_image_hypothesis_invalid")
    if own_page.get("service_image_count") != 0 or own_page.get("service_image_ids") != []:
        raise RuntimeError("storefront_image_before_not_current")
    contract = {
        "version": 1, "platform": "coconala", "service_id": TARGET_SERVICE_ID,
        "precondition_listing_version_sha256": own_page["listing_version_sha256"],
        "changed_field": "image", "before_value": {"service_image_ids": []},
        "proposed_value": {
            "asset_sha256": asset["asset_sha256"],
            "asset_path": str(Path(asset["asset_path"]).resolve().relative_to(GIG_DIR.resolve())),
        },
        "allowed_delta": ["data[UploadedFile][n*][image_files]"],
        "rollback_value": {"service_image_ids": []},
        "official_readback": {"service_image_count": 1},
        "success_metric": "views_to_inquiry", "observation_window_days": 14,
        "capability_family": capability_families.get(TARGET_SERVICE_ID),
        "evidence": [asset["claim_source"], asset["platform_requirement_source"]],
    }
    return _seal_mutation_contract(contract, capability_families)


def _validate_image_mutation_contract(
    contract: dict, families_path: Path = DEFAULT_LISTING_CONTRACT_FAMILIES,
) -> None:
    mappings, _ = _load_capability_families(families_path)
    _validate_mutation_contract(contract, mappings)
    proposed = contract.get("proposed_value")
    if contract.get("changed_field") != "image" or not isinstance(proposed, dict):
        raise RuntimeError("storefront_image_mutation_contract_invalid")
    if contract.get("service_id") != GALLERY_SERVICE_ID:
        if (contract.get("before_value") != {"service_image_ids": []}
                or contract.get("allowed_delta") != ["data[UploadedFile][n*][image_files]"]
                or contract.get("rollback_value") != {"service_image_ids": []}
                or contract.get("official_readback") != {"service_image_count": 1}
                or set(proposed) != {"asset_sha256", "asset_path"}
                or not re.fullmatch(r"[0-9a-f]{64}", str(proposed.get("asset_sha256") or ""))):
            raise RuntimeError("storefront_image_mutation_contract_invalid")
        raw_asset = Path(str(proposed.get("asset_path") or ""))
        asset = raw_asset.resolve() if raw_asset.is_absolute() else (GIG_DIR / raw_asset).resolve()
        allowed_roots = (GIG_DIR.resolve(), (STATE_DIR / "storefront-direct").resolve())
        try:
            if not any(asset.is_relative_to(root) for root in allowed_roots):
                raise ValueError("outside_allowed_roots")
            data = asset.read_bytes()
        except (OSError, ValueError) as error:
            raise RuntimeError("storefront_image_asset_invalid") from error
        if (len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n"
                or struct.unpack(">II", data[16:24]) != (1220, 1016)
                or hashlib.sha256(data).hexdigest() != proposed["asset_sha256"]):
            raise RuntimeError("storefront_image_asset_identity_invalid")
        return
    before_ids = contract.get("before_value", {}).get("service_image_ids")
    rollback_ids = contract.get("rollback_value", {}).get("service_image_ids")
    assets, kept = proposed.get("replacement_assets"), proposed.get("kept_image_ids")
    readback, allowed = contract.get("official_readback"), contract.get("allowed_delta")
    if (not isinstance(before_ids, list) or len(before_ids) != 6 or rollback_ids != before_ids
            or not isinstance(assets, list) or len(assets) != 4
            or not isinstance(kept, list) or len(kept) != 2 or not set(kept) < set(before_ids)
            or allowed != ["data[UploadedFile][gallery][image_files]"]
            or not isinstance(readback, dict) or readback.get("service_image_count") != 6
            or set(readback.get("removed_image_ids") or []) != set(before_ids) - set(kept)
            or readback.get("kept_image_ids") != kept):
        raise RuntimeError("storefront_gallery_mutation_contract_invalid")
    for row in assets:
        if (not isinstance(row, dict) or set(row) != {
                "replace_image_id", "asset_sha256", "asset_path", "upload_field"}
                or row.get("replace_image_id") not in before_ids
                or not re.fullmatch(r"data\[UploadedFile]\[\d+]\[image_files]", str(row.get("upload_field") or ""))
                or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("asset_sha256") or ""))):
            raise RuntimeError("storefront_gallery_mutation_contract_invalid")


def _render_image_mutation(
    own_page: dict, asset: dict, capability_families: dict[str, str],
) -> dict:
    contract = _image_mutation_contract({
        "service_id": TARGET_SERVICE_ID, "field": "image", "before": 0,
        "executable": True, "success_metric": "views_to_inquiry",
    }, own_page, asset, capability_families)
    key = contract["allowed_delta"][0]
    before = {key: contract["before_value"]}
    after = {key: contract["proposed_value"]}
    delta = [name for name in sorted(set(before) | set(after)) if before.get(name) != after.get(name)]
    if delta != contract["allowed_delta"]:
        raise RuntimeError("storefront_image_mutation_multi_field_delta")
    return {"version": 1, "contract": contract, "before": before, "after": after,
            "delta": delta, "published": False}


def _render_gallery_mutation(
    own_page: dict, service_version_sha256: str, asset_contract: dict,
    capability_families: dict[str, str],
) -> dict:
    before_ids = list(asset_contract["before_image_ids"])
    if (own_page.get("service_id") != GALLERY_SERVICE_ID
            or own_page.get("service_image_ids") != before_ids):
        raise RuntimeError("storefront_gallery_before_not_current")
    replacements = []
    for row in asset_contract["replacements"]:
        match = re.search(r"-(\d+)\.png$", row["replace_image_id"])
        if match is None:
            raise RuntimeError("storefront_gallery_image_id_invalid")
        replacements.append({
            "replace_image_id": row["replace_image_id"],
            "asset_sha256": row["asset_sha256"],
            "asset_path": str(Path(row["asset_path"]).resolve().relative_to(GIG_DIR.resolve())),
            "upload_field": f"data[UploadedFile][{match.group(1)}][image_files]",
        })
    upload_fields = [row["upload_field"] for row in replacements]
    contract = {
        "version": 1, "platform": "coconala", "service_id": GALLERY_SERVICE_ID,
        "precondition_listing_version_sha256": service_version_sha256,
        "changed_field": "image", "before_value": {"service_image_ids": before_ids},
        "proposed_value": {
            "replacement_assets": replacements,
            "kept_image_ids": list(asset_contract["kept_image_ids"]),
        },
        "allowed_delta": ["data[UploadedFile][gallery][image_files]"],
        "rollback_value": {"service_image_ids": before_ids},
        "official_readback": {
            "service_image_count": 6,
            "removed_image_ids": [row["replace_image_id"] for row in asset_contract["replacements"]],
            "kept_image_ids": list(asset_contract["kept_image_ids"]),
        },
        "success_metric": "views_to_inquiry", "observation_window_days": 14,
        "capability_family": capability_families.get(GALLERY_SERVICE_ID),
        "evidence": [asset_contract["claim_source"], asset_contract["platform_requirement_source"]],
    }
    contract = _seal_mutation_contract(contract, capability_families)
    _validate_image_mutation_contract(contract)
    logical_field = contract["allowed_delta"][0]
    return {
        "version": 1, "contract": contract,
        "before": {logical_field: contract["before_value"]},
        "after": {logical_field: contract["proposed_value"]},
        "delta": contract["allowed_delta"], "published": False,
    }


def _render_published_gallery_mutation(state_dir: Path, own_page: dict) -> dict:
    for path in sorted((state_dir / "effect-intents").glob("*.json")):
        try:
            intent = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (intent.get("status") != "confirmed" or intent.get("effect_ledger_appended") is not True
                or intent.get("service_id") != GALLERY_SERVICE_ID
                or intent.get("changed_field") != "image"):
            continue
        contract = intent.get("mutation_contract")
        if not isinstance(contract, dict):
            raise RuntimeError("published_gallery_contract_missing")
        _validate_image_mutation_contract(contract)
        try:
            public_before = json.loads(Path(intent["public_before_path"]).read_text(encoding="utf-8"))
        except (OSError, KeyError, json.JSONDecodeError) as error:
            raise RuntimeError("published_gallery_before_evidence_missing") from error
        _validate_public_image_acceptance(public_before, own_page, contract)
        logical_field = contract["allowed_delta"][0]
        return {
            "version": 1, "contract": contract,
            "before": {logical_field: contract["before_value"]},
            "after": {logical_field: contract["proposed_value"]},
            "delta": contract["allowed_delta"], "published": True,
        }
    raise RuntimeError("storefront_gallery_before_not_current")


def _image_judgement(hypothesis: dict, contract: dict) -> dict:
    _validate_image_mutation_contract(contract)
    proposed = contract["proposed_value"]
    asset_digest = proposed.get("asset_sha256") if isinstance(proposed, dict) else None
    digest = str(asset_digest) if isinstance(asset_digest, str) and asset_digest else str(contract["contract_sha256"])
    return {
        "decision": "change", "service_id": contract["service_id"], "changed_field": "image",
        "before_value": hypothesis.get("before"), "proposed_value": digest,
        "hypothesis": str(hypothesis["reason"]), "competitor_evidence_paths": [],
        "capability_evidence_paths": [], "success_metric": contract["success_metric"],
        "observation_window_days": contract["observation_window_days"], "no_op_reason": None,
        "experiment_key": _experiment_key(contract["service_id"], "image", digest), "uncertainty": [],
    }


def _text_judgement(hypothesis: dict, contract: dict, effects_path: Path, now: int) -> dict:
    mappings, _ = _load_capability_families(DEFAULT_LISTING_CONTRACT_FAMILIES)
    _validate_mutation_contract(contract, mappings)
    if (hypothesis.get("service_id") != contract.get("service_id")
            or hypothesis.get("field") != contract.get("changed_field")
            or contract.get("changed_field") not in {"title", "body", "package", "price"}
            or hypothesis.get("mutation_contract_sha256") != contract.get("contract_sha256")
            or hypothesis.get("executable") is not True):
        raise RuntimeError("storefront_text_hypothesis_invalid")
    changed_field = str(contract["changed_field"])
    proposed = contract["proposed_value"]
    value = {
        "decision": "change", "service_id": contract["service_id"], "changed_field": changed_field,
        "before_value": contract["before_value"], "proposed_value": proposed,
        "hypothesis": str(hypothesis["reason"]), "competitor_evidence_paths": [],
        "capability_evidence_paths": [], "success_metric": contract["success_metric"],
        "observation_window_days": contract["observation_window_days"], "no_op_reason": None,
        "experiment_key": _experiment_key(contract["service_id"], changed_field, proposed), "uncertainty": [],
    }
    if effects_path.exists():
        for line in effects_path.read_text(encoding="utf-8").splitlines():
            effect = json.loads(line)
            if effect.get("status") != "accepted" or effect.get("effect") != 1:
                continue
            accepted_at = int(effect.get("accepted_at_epoch") or 0)
            if effect.get("experiment_key") == value["experiment_key"]:
                return _guarded_noop(value, "experiment_already_succeeded")
            if str(effect.get("service_id") or "") == contract["service_id"] and now - accepted_at < 604800:
                return _guarded_noop(value, "service_cooldown_7d")
    return value


def _guarded_noop(value: dict, reason: str) -> dict:
    return {
        **value,
        "decision": "no_op",
        "service_id": None,
        "changed_field": None,
        "before_value": None,
        "proposed_value": None,
        "success_metric": None,
        "observation_window_days": None,
        "no_op_reason": reason,
        "experiment_key": None,
    }


def _guard_judgement(
    value: dict,
    *,
    own_page: dict,
    competitor_manifest: dict,
    capability_paths: set[str],
    evidence_dir: Path,
    effects_path: Path,
    minimum_epoch: int,
    now: int,
) -> dict:
    if set(value) != JUDGEMENT_FIELDS:
        raise RuntimeError("judgement_fields_invalid")
    if not isinstance(value.get("hypothesis"), str) or not value["hypothesis"].strip() or len(value["hypothesis"]) > 1000:
        raise RuntimeError("judgement_hypothesis_invalid")
    uncertainty = value.get("uncertainty")
    if not isinstance(uncertainty, list) or len(uncertainty) > 16 or not all(
        isinstance(item, str) and 0 < len(item) <= 240 for item in uncertainty
    ):
        raise RuntimeError("judgement_uncertainty_invalid")
    if value.get("decision") == "no_op":
        if any(value.get(key) is not None for key in (
            "changed_field", "before_value", "proposed_value",
            "success_metric", "observation_window_days", "experiment_key",
        )) or not str(value.get("no_op_reason") or "").strip():
            raise RuntimeError("judgement_noop_contract_invalid")
        return _guarded_noop(value, str(value["no_op_reason"]))
    if value.get("decision") != "change":
        raise RuntimeError("judgement_decision_invalid")
    if value.get("service_id") != TARGET_SERVICE_ID or value.get("changed_field") != "FAQ":
        raise RuntimeError("judgement_not_single_supported_field")
    if value.get("before_value") != "FAQ_ABSENT" or "よくある質問" in str(own_page.get("body") or ""):
        raise RuntimeError("judgement_before_value_not_current")
    proposed = str(value.get("proposed_value") or "").strip()
    if not proposed or proposed == "FAQ_ABSENT" or len(proposed) > 4000:
        raise RuntimeError("judgement_proposed_value_invalid")

    owned = {str(row.get("path")): row for row in competitor_manifest.get("sources", []) if isinstance(row, dict)}
    references = value.get("competitor_evidence_paths")
    if not isinstance(references, list) or not references or not set(references) <= set(owned):
        raise RuntimeError("judgement_competitor_evidence_unowned")
    for reference in references:
        path = Path(reference).resolve()
        try:
            path.relative_to(evidence_dir.resolve())
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError) as error:
            raise RuntimeError("judgement_competitor_evidence_invalid") from error
        if (row.get("official") is not True or row.get("observed") is not True
                or int(row.get("observed_at_epoch") or 0) < minimum_epoch
                or row.get("content_sha256") != owned[reference].get("content_sha256")):
            raise RuntimeError("judgement_competitor_evidence_stale")
    capabilities = value.get("capability_evidence_paths")
    if not isinstance(capabilities, list) or not capabilities or not set(capabilities) <= capability_paths:
        raise RuntimeError("judgement_capability_evidence_unowned")
    if any(not Path(path).is_file() for path in capabilities):
        raise RuntimeError("judgement_capability_evidence_missing")
    if value.get("success_metric") not in {"inquiries", "purchases", "views_to_inquiry", "views_to_purchase"}:
        raise RuntimeError("judgement_success_metric_invalid")
    if value.get("observation_window_days") not in {7, 14}:
        raise RuntimeError("judgement_window_invalid")

    key = _experiment_key(TARGET_SERVICE_ID, "FAQ", proposed)
    if value.get("experiment_key") not in {None, key}:
        raise RuntimeError("judgement_experiment_key_invalid")
    if effects_path.exists():
        for line in effects_path.read_text(encoding="utf-8").splitlines():
            try:
                effect = json.loads(line)
            except json.JSONDecodeError as error:
                raise RuntimeError("effect_ledger_invalid") from error
            if effect.get("status") != "accepted" or effect.get("effect") != 1:
                continue
            accepted_at = int(effect.get("accepted_at_epoch") or 0)
            if effect.get("experiment_key") == key:
                return _guarded_noop(value, "experiment_already_succeeded")
            if effect.get("service_id") == TARGET_SERVICE_ID and now - accepted_at < 604800:
                return _guarded_noop(value, "service_cooldown_7d")
    return {**value, "experiment_key": key, "no_op_reason": None}


def _presend_guard(judgement: dict, own_page: dict, mutation_contract: dict | None = None) -> None:
    if judgement.get("decision") != "change":
        return
    if judgement.get("changed_field") == "image":
        if not isinstance(mutation_contract, dict):
            raise RuntimeError("presend_image_mutation_contract_missing")
        _validate_image_mutation_contract(mutation_contract)
        before_value = mutation_contract.get("before_value", {})
        expected_ids = before_value.get("service_image_ids")
        if (mutation_contract.get("contract_sha256") is None
                or judgement.get("service_id") != mutation_contract.get("service_id")
                or own_page.get("service_image_ids") != expected_ids):
            raise RuntimeError("presend_image_current_value_changed")
        return
    if (judgement.get("service_id") != TARGET_SERVICE_ID
            or judgement.get("changed_field") != "FAQ"
            or judgement.get("before_value") != "FAQ_ABSENT"
            or "よくある質問" in str(own_page.get("body") or "")):
        raise RuntimeError("presend_current_value_changed")


def _split_faq(proposed: str) -> tuple[str, str]:
    match = FAQ_PATTERN.fullmatch(proposed.strip())
    if match is None:
        raise RuntimeError("faq_proposal_format_invalid")
    question, answer = match.group("question").strip(), match.group("answer").strip()
    if not question or not answer or len(question) > 400 or len(answer) > 400:
        raise RuntimeError("faq_proposal_length_invalid")
    return question, answer


def _form_base_fields(snapshot: dict) -> list[dict]:
    fields = snapshot.get("fields")
    if not isinstance(fields, list):
        raise RuntimeError("seller_form_fields_invalid")
    return [row for row in fields if isinstance(row, dict) and not str(row.get("name") or "").startswith("data[Faq]")]


def _validate_form_delta(before: dict, after: dict, question: str, answer: str) -> None:
    if before.get("url") != f"https://coconala.com/mypage/services/{TARGET_SERVICE_ID}" or after.get("url") != before.get("url"):
        raise RuntimeError("seller_form_url_invalid")
    if _form_base_fields(before) != _form_base_fields(after):
        raise RuntimeError("seller_form_non_faq_changed")
    before_faq = [row for row in before["fields"] if str(row.get("name") or "").startswith("data[Faq]")]
    after_faq = [row for row in after["fields"] if str(row.get("name") or "").startswith("data[Faq]")]
    if before_faq or [(row.get("name"), row.get("value")) for row in after_faq] != [
        ("data[Faq][0][question]", question), ("data[Faq][0][answer]", answer),
    ]:
        raise RuntimeError("seller_form_faq_delta_invalid")


def _validate_public_acceptance(before: dict, after: dict, question: str, answer: str) -> None:
    url = f"https://coconala.com/services/{TARGET_SERVICE_ID}"
    if before.get("url") != url or after.get("url") != url:
        raise RuntimeError("public_readback_url_invalid")
    if before.get("content_sha256") == after.get("content_sha256"):
        raise RuntimeError("public_readback_hash_unchanged")
    before_body, after_body = str(before.get("body") or ""), str(after.get("body") or "")
    if question in before_body or answer in before_body or question not in after_body or answer not in after_body:
        raise RuntimeError("public_faq_readback_mismatch")


def _validate_public_image_acceptance(before: dict, after: dict, contract: dict) -> None:
    _validate_image_mutation_contract(contract)
    service_id = str(contract.get("service_id") or "")
    url = f"https://coconala.com/services/{service_id}"
    if before.get("url") != url or after.get("url") != url:
        raise RuntimeError("public_image_readback_url_invalid")
    if before.get("service_image_ids") != contract.get("rollback_value", {}).get("service_image_ids"):
        raise RuntimeError("public_image_before_invalid")
    expected = contract.get("official_readback", {}).get("service_image_count")
    if after.get("service_image_count") != expected or len(after.get("service_image_ids") or []) != expected:
        raise RuntimeError("public_image_count_mismatch")
    if service_id == GALLERY_SERVICE_ID:
        after_ids = after.get("service_image_ids") or []
        removed = set(contract["official_readback"]["removed_image_ids"])
        kept = contract["official_readback"]["kept_image_ids"]
        if (removed & set(after_ids) or not set(kept) <= set(after_ids)
                or after_ids[2] != kept[0] or after_ids[4] != kept[1]):
            raise RuntimeError("public_gallery_identity_or_order_mismatch")


def _validate_image_form_delta(before: dict, after: dict, contract: dict) -> None:
    _validate_image_mutation_contract(contract)
    url = f"https://coconala.com/mypage/services/{contract['service_id']}"
    if before.get("url") != url or after.get("url") != url:
        raise RuntimeError("seller_image_form_url_invalid")
    before_fields = [row for row in _form_base_fields(before) if not str(row.get("name") or "").startswith("data[UploadedFile]")]
    after_fields = [row for row in _form_base_fields(after) if not str(row.get("name") or "").startswith("data[UploadedFile]")]
    uploads = [row for row in after.get("fields") or [] if str(row.get("name") or "").startswith("data[UploadedFile]")]
    if before_fields != after_fields:
        raise RuntimeError("seller_image_non_image_changed")
    if contract["service_id"] != GALLERY_SERVICE_ID:
        if (any(str(row.get("name") or "").startswith("data[UploadedFile]") for row in before.get("fields") or [])
                or len(uploads) != 1
                or not re.fullmatch(r"data\[UploadedFile]\[n\d+]\[image_files]", str(uploads[0].get("name") or ""))):
            raise RuntimeError("seller_image_upload_field_invalid")
        return
    before_uploads = {str(row.get("name") or ""): str(row.get("value") or "")
                      for row in before.get("fields") or []
                      if str(row.get("name") or "").startswith("data[UploadedFile]")}
    after_uploads = {str(row.get("name") or ""): str(row.get("value") or "")
                     for row in uploads}
    changed = [name for name in sorted(set(before_uploads) | set(after_uploads))
               if before_uploads.get(name) != after_uploads.get(name)]
    expected = sorted(row["upload_field"] for row in contract["proposed_value"]["replacement_assets"])
    if changed != expected:
        raise RuntimeError("seller_gallery_upload_delta_invalid")


def _seller_snapshot(ws_url: str) -> dict:
    return _seller_snapshot_for(ws_url, TARGET_SERVICE_ID)


def _seller_snapshot_for(ws_url: str, service_id: str) -> dict:
    import listing_inventory

    url = f"https://coconala.com/mypage/services/{service_id}"
    required = {"data[Service][overview]", "data[Service][head]", "data[Service][price]"}
    last = {}
    for attempt in range(3):
        last = asyncio.run(listing_inventory._eval_json(ws_url, url, SELLER_FORM_EXPRESSION))
        names = {str(row.get("name") or "") for row in last.get("fields", []) if isinstance(row, dict)}
        if last.get("url") == url and required <= names:
            return last
        if attempt < 2:
            time.sleep(1)
    raise RuntimeError("seller_form_not_fully_hydrated")


async def _seller_package_snapshot_async(ws_url: str, service_id: str) -> dict:
    import websockets
    import listing_inventory

    url = f"https://coconala.com/mypage/services/{service_id}"
    async with websockets.connect(ws_url, ping_interval=None, open_timeout=10,
                                  max_size=40 * 1024 * 1024) as ws:
        cid = 1
        await listing_inventory._call(ws, "Page.enable", {}, cid); cid += 1
        await ws.send(json.dumps({"id": cid, "method": "Page.navigate", "params": {"url": url}})); cid += 1
        _, cid = await listing_inventory._wait_for_load(
            ws, asyncio.get_event_loop().time() + 15, cid,
        )

        async def evaluate(expression: str) -> object:
            nonlocal cid
            response = await listing_inventory._call(
                ws, "Runtime.evaluate", {"expression": expression, "returnByValue": True}, cid,
            )
            cid += 1
            return response.get("result", {}).get("result", {}).get("value")

        before = json.loads(str(await evaluate(SELLER_FORM_EXPRESSION) or "{}"))
        option_titles = [row for row in before.get("fields") or []
                         if re.fullmatch(r"data\[Option]\[\d+]\[title]", str(row.get("name") or ""))]
        if option_titles:
            return {**before, "package_slot_added": False}
        clicked = await evaluate(
            "(()=>{const b=document.querySelector('#addOption');if(!b)return false;b.click();return true})()"
        )
        if clicked is not True:
            raise RuntimeError("seller_package_add_control_missing")
        await asyncio.sleep(0.5)
        after = json.loads(str(await evaluate(SELLER_FORM_EXPRESSION) or "{}"))
        fields = {str(row.get("name") or ""): row for row in after.get("fields") or []}
        if not {"data[Option][0][title]", "data[Option][0][price]", "data[Option][0][opened]"} <= set(fields):
            raise RuntimeError("seller_package_slot_not_hydrated")
        return {**after, "package_slot_added": True}


def _seller_package_snapshot_for(ws_url: str, service_id: str) -> dict:
    return asyncio.run(_seller_package_snapshot_async(ws_url, service_id))


def _effect_intent_path(state_dir: Path, experiment_key: str) -> Path:
    digest = hashlib.sha256(experiment_key.encode()).hexdigest()
    return state_dir / "effect-intents" / f"{digest}.json"


def _pending_recovery(
    state_dir: Path, own_page: dict, ws_url: str | None = None, evidence_dir: Path | None = None,
) -> dict | None:
    body = str(own_page.get("body") or "")
    for path in sorted((state_dir / "effect-intents").glob("*.json")):
        try:
            intent = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if intent.get("status") not in {"prepared", "observed"}:
            continue
        if intent.get("changed_field") == "image":
            contract = intent.get("mutation_contract")
            if not isinstance(contract, dict):
                raise RuntimeError("pending_image_contract_missing")
            _validate_image_mutation_contract(contract)
            service_id = str(contract["service_id"])
            page = own_page
            if service_id != str(own_page.get("service_id") or ""):
                if ws_url is None or evidence_dir is None:
                    raise RuntimeError("pending_image_readback_context_missing")
                page = _observe_own_page(
                    ws_url, evidence_dir, f"recovery-public-{service_id}.json", service_id,
                )
            image_ids = page.get("service_image_ids")
            if service_id != GALLERY_SERVICE_ID and page.get("service_image_count") == 1:
                return {**intent, "intent_path": str(path), "_recovery_public_page": page}
            if service_id == GALLERY_SERVICE_ID:
                readback = contract["official_readback"]
                removed = set(readback["removed_image_ids"])
                kept = readback["kept_image_ids"]
                if (page.get("service_image_count") == 6 and isinstance(image_ids, list)
                        and not removed.intersection(image_ids) and set(kept) <= set(image_ids)):
                    return {**intent, "intent_path": str(path), "_recovery_public_page": page}
            if image_ids == contract["rollback_value"]["service_image_ids"]:
                continue
            raise RuntimeError("pending_image_effect_public_readback_invalid")
        if intent.get("changed_field") in {"title", "body", "package", "price"}:
            contract = intent.get("mutation_contract")
            if not isinstance(contract, dict) or ws_url is None or evidence_dir is None:
                raise RuntimeError("pending_text_contract_missing")
            mappings, _ = _load_capability_families(DEFAULT_LISTING_CONTRACT_FAMILIES)
            _validate_mutation_contract(contract, mappings)
            service_id = str(contract["service_id"])
            page = _observe_own_page(
                ws_url, evidence_dir, f"recovery-public-{service_id}.json", service_id,
            )
            seller = _seller_snapshot_for(ws_url, service_id)
            values = {str(row.get("name") or ""): str(row.get("value") or "")
                      for row in seller.get("fields") or [] if isinstance(row, dict)}
            if contract["changed_field"] == "package":
                proposed = contract["proposed_value"]
                current_matches = (
                    values.get("data[Option][0][title]") == proposed["title"]
                    and values.get("data[Option][0][price]") == str(proposed["price_jpy"])
                    and values.get("data[Option][0][opened]") == "1"
                )
                expected = str(proposed["title"])
                rollback_matches = not any(name.startswith("data[Option]") for name in values)
            else:
                current = values.get(contract["allowed_delta"][0])
                expected = (contract["official_readback"].get("public_title")
                            if contract["changed_field"] == "title"
                            else f"{int(contract['official_readback']['public_price_jpy']):,}円"
                            if contract["changed_field"] == "price" else contract["proposed_value"])
                current_matches = current == contract["proposed_value"]
                rollback_matches = current == contract["before_value"]
            if current_matches and expected in str(page.get("body") or ""):
                return {**intent, "intent_path": str(path), "_recovery_public_page": page,
                        "_recovery_seller_snapshot": seller}
            if rollback_matches:
                continue
            raise RuntimeError("pending_text_effect_public_readback_invalid")
        question, answer = str(intent.get("question") or ""), str(intent.get("answer") or "")
        if not question or not answer or len(question) > 400 or len(answer) > 400:
            raise RuntimeError("pending_effect_values_invalid")
        visible = (question in body, answer in body)
        if visible == (True, True):
            return {**intent, "intent_path": str(path)}
        if visible[0] != visible[1]:
            raise RuntimeError("pending_effect_partial_public_readback")
    return None


async def _execute_faq_effect_async(
    ws_url: str,
    *,
    question: str,
    answer: str,
    judgement: dict,
    public_before_path: Path,
    evidence_dir: Path,
    state_dir: Path,
) -> tuple[dict, dict, Path]:
    import websockets
    import listing_inventory

    edit_url = f"https://coconala.com/mypage/services/{TARGET_SERVICE_ID}"
    async with websockets.connect(ws_url, ping_interval=None, open_timeout=10, max_size=40 * 1024 * 1024) as ws:
        cid = 1
        await listing_inventory._call(ws, "Page.enable", {}, cid); cid += 1
        await ws.send(json.dumps({"id": cid, "method": "Page.navigate", "params": {"url": edit_url}})); cid += 1
        _, cid = await listing_inventory._wait_for_load(ws, asyncio.get_event_loop().time() + 15, cid)

        async def evaluate(expression: str) -> object:
            nonlocal cid
            response = await listing_inventory._call(
                ws, "Runtime.evaluate", {"expression": expression, "returnByValue": True}, cid,
            )
            cid += 1
            return response.get("result", {}).get("result", {}).get("value")

        before_raw = await evaluate(SELLER_FORM_EXPRESSION)
        before = json.loads(str(before_raw or "{}"))
        fill = await evaluate(
            "(()=>{"
            f"if(location.href!=={json.dumps(edit_url)})return JSON.stringify({{ok:false,reason:'edit_url'}});"
            "const form=document.forms[0],existing=[...form.elements].filter(e=>(e.name||'').startsWith('data[Faq]'));"
            "if(existing.length)return JSON.stringify({ok:false,reason:'faq_exists'});"
            "document.querySelector('#addQA')?.click();"
            "const q=document.querySelector('#Faq0Question'),a=document.querySelector('#Faq0Answer');"
            "if(!q||!a)return JSON.stringify({ok:false,reason:'faq_controls_missing'});"
            f"q.value={json.dumps(question)};a.value={json.dumps(answer)};"
            "for(const e of [q,a]){e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}))}"
            "const submit=form.querySelector('button.submitButton.js_button-edit[type=submit]');"
            "if(!submit)return JSON.stringify({ok:false,reason:'submit_missing'});"
            "submit.scrollIntoView({block:'center'});const r=submit.getBoundingClientRect();"
            "return JSON.stringify({ok:true,question:q.value,answer:a.value,rect:{x:r.left+r.width/2,y:r.top+r.height/2,w:r.width,h:r.height}})})()"
        )
        fill_result = json.loads(str(fill or "{}"))
        if fill_result.get("ok") is not True or fill_result.get("question") != question or fill_result.get("answer") != answer:
            raise RuntimeError(f"seller_faq_fill_failed:{fill_result.get('reason')}")
        after_raw = await evaluate(SELLER_FORM_EXPRESSION)
        after = json.loads(str(after_raw or "{}"))
        _validate_form_delta(before, after, question, answer)
        before_path, after_path = evidence_dir / "seller-form-before.json", evidence_dir / "seller-form-filled.json"
        _atomic_write(before_path, before)
        _atomic_write(after_path, after)
        intent_path = _effect_intent_path(state_dir, str(judgement["experiment_key"]))
        intent = {
            "version": 1, "status": "prepared", "service_id": TARGET_SERVICE_ID,
            "changed_field": "FAQ", "experiment_key": judgement["experiment_key"],
            "question": question, "answer": answer, "public_before_path": str(public_before_path),
            "seller_form_before_path": str(before_path), "prepared_at_epoch": int(time.time()),
            "effect_origin_pass_id": evidence_dir.name, "judgement": judgement,
        }
        _atomic_write(intent_path, intent)
        rect = fill_result["rect"]
        if min(float(rect.get("w") or 0), float(rect.get("h") or 0)) <= 0:
            raise RuntimeError("seller_submit_not_visible")
        for event_type in ("mousePressed", "mouseReleased"):
            await listing_inventory._call(ws, "Input.dispatchMouseEvent", {
                "type": event_type, "x": float(rect["x"]), "y": float(rect["y"]),
                "button": "left", "clickCount": 1,
            }, cid)
            cid += 1
        await asyncio.sleep(3)
        return before, after, intent_path


def _execute_faq_effect(**kwargs) -> tuple[dict, dict, Path]:
    return asyncio.run(_execute_faq_effect_async(**kwargs))


def _validate_text_form_delta(before: dict, after: dict, contract: dict) -> None:
    field = contract["allowed_delta"][0]
    url = f"https://coconala.com/mypage/services/{contract['service_id']}"
    if before.get("url") != url or after.get("url") != url:
        raise RuntimeError("seller_text_form_url_invalid")
    before_targets = [row for row in before.get("fields") or [] if row.get("name") == field]
    after_targets = [row for row in after.get("fields") or [] if row.get("name") == field]
    if (len(before_targets) != 1 or len(after_targets) != 1
            or before_targets[0].get("value") != contract["before_value"]
            or after_targets[0].get("value") != contract["proposed_value"]):
        raise RuntimeError("seller_text_value_mismatch")
    strip = lambda snapshot: [row for row in snapshot.get("fields") or [] if row.get("name") != field]
    if strip(before) != strip(after):
        raise RuntimeError("seller_text_non_target_changed")


def _validate_text_public_acceptance(before: dict, after: dict, contract: dict) -> None:
    url = f"https://coconala.com/services/{contract['service_id']}"
    readback = contract["official_readback"]
    if contract["changed_field"] == "package":
        expected = str(readback["option_title"])
        secondary = f"{int(readback['option_price_jpy']):,}円"
    elif contract["changed_field"] == "price":
        expected = f"{int(readback['public_price_jpy']):,}円"
        secondary = None
    else:
        expected = str(readback.get("public_title") or contract["proposed_value"])
        secondary = None
    if before.get("url") != url or after.get("url") != url:
        raise RuntimeError("public_text_readback_url_invalid")
    body = str(after.get("body") or "")
    if (before.get("content_sha256") == after.get("content_sha256") or expected not in body
            or (secondary is not None and secondary not in body)):
        raise RuntimeError("public_text_readback_mismatch")


def _validate_package_form_delta(before: dict, after: dict, contract: dict) -> None:
    url = f"https://coconala.com/mypage/services/{contract['service_id']}"
    if before.get("url") != url or after.get("url") != url:
        raise RuntimeError("seller_package_form_url_invalid")
    before_fields = {str(row.get("name") or ""): str(row.get("value") or "")
                     for row in before.get("fields") or [] if isinstance(row, dict)}
    after_fields = {str(row.get("name") or ""): str(row.get("value") or "")
                    for row in after.get("fields") or [] if isinstance(row, dict)}
    option_names = {name for name in set(before_fields) | set(after_fields) if name.startswith("data[Option]")}
    if any(name in before_fields for name in option_names):
        raise RuntimeError("seller_package_before_not_absent")
    expected = contract["proposed_value"]
    required = {
        "data[Option][0][service_id]": contract["service_id"],
        "data[Option][0][title]": expected["title"],
        "data[Option][0][price]": str(expected["price_jpy"]),
        "data[Option][0][opened]": "1",
    }
    unexpected = option_names - set(required)
    if ({name: after_fields.get(name) for name in required} != required
            or any(name != "data[Option][0][id]" or not after_fields.get(name, "").isdigit()
                   for name in unexpected)):
        raise RuntimeError("seller_package_value_mismatch")
    if ({name: value for name, value in before_fields.items() if not name.startswith("data[Option]")}
            != {name: value for name, value in after_fields.items() if not name.startswith("data[Option]")}):
        raise RuntimeError("seller_package_non_target_changed")


async def _execute_text_effect_async(
    ws_url: str, *, contract: dict, judgement: dict, public_before_path: Path,
    evidence_dir: Path, state_dir: Path,
) -> tuple[dict, dict, Path]:
    import websockets
    import listing_inventory

    mappings, _ = _load_capability_families(DEFAULT_LISTING_CONTRACT_FAMILIES)
    _validate_mutation_contract(contract, mappings)
    if contract.get("changed_field") not in {"title", "body", "price"} or judgement.get("experiment_key") != _experiment_key(
        contract["service_id"], str(contract["changed_field"]), str(contract["proposed_value"]),
    ):
        raise RuntimeError("seller_text_contract_invalid")
    edit_url = f"https://coconala.com/mypage/services/{contract['service_id']}"
    async with websockets.connect(ws_url, ping_interval=None, open_timeout=10, max_size=40 * 1024 * 1024) as ws:
        cid = 1
        await listing_inventory._call(ws, "Page.enable", {}, cid); cid += 1
        await ws.send(json.dumps({"id": cid, "method": "Page.navigate", "params": {"url": edit_url}})); cid += 1
        _, cid = await listing_inventory._wait_for_load(ws, asyncio.get_event_loop().time() + 15, cid)

        async def evaluate(expression: str) -> object:
            nonlocal cid
            response = await listing_inventory._call(
                ws, "Runtime.evaluate", {"expression": expression, "returnByValue": True}, cid,
            )
            cid += 1
            return response.get("result", {}).get("result", {}).get("value")

        before = json.loads(str(await evaluate(SELLER_FORM_EXPRESSION) or "{}"))
        field = contract["allowed_delta"][0]
        filled = json.loads(str(await evaluate(
            "JSON.stringify((()=>{const form=document.forms[0],field=" + json.dumps(field)
            + ",before=" + json.dumps(contract["before_value"], ensure_ascii=False)
            + ",proposed=" + json.dumps(contract["proposed_value"], ensure_ascii=False)
            + ";const e=form?.querySelector(`[name=\"${field}\"]`);"
            "if(!e||e.value!==before)return {ok:false,reason:'before_mismatch'};"
            "e.value=proposed;e.dispatchEvent(new Event('input',{bubbles:true}));"
            "e.dispatchEvent(new Event('change',{bubbles:true}));"
            "const submit=form.querySelector('button.submitButton.js_button-edit[type=submit]');"
            "if(!submit)return {ok:false,reason:'submit_missing'};submit.scrollIntoView({block:'center'});"
            "const r=submit.getBoundingClientRect();return {ok:true,value:e.value,"
            "rect:{x:r.left+r.width/2,y:r.top+r.height/2,w:r.width,h:r.height}}})())"
        ) or "{}"))
        if filled.get("ok") is not True or filled.get("value") != contract["proposed_value"]:
            raise RuntimeError(f"seller_text_fill_failed:{filled.get('reason')}")
        after = json.loads(str(await evaluate(SELLER_FORM_EXPRESSION) or "{}"))
        _validate_text_form_delta(before, after, contract)
        before_path, after_path = evidence_dir / "seller-form-before.json", evidence_dir / "seller-form-text-filled.json"
        _atomic_write(before_path, before); _atomic_write(after_path, after)
        intent_path = _effect_intent_path(state_dir, str(judgement["experiment_key"]))
        _atomic_write(intent_path, {
            "version": 1, "status": "prepared", "service_id": contract["service_id"],
            "changed_field": contract["changed_field"], "experiment_key": judgement["experiment_key"],
            "mutation_contract": contract, "public_before_path": str(public_before_path),
            "seller_form_before_path": str(before_path), "prepared_at_epoch": int(time.time()),
            "effect_origin_pass_id": evidence_dir.name, "judgement": judgement,
        })
        rect = filled["rect"]
        if min(float(rect.get("w") or 0), float(rect.get("h") or 0)) <= 0:
            raise RuntimeError("seller_text_submit_not_visible")
        for event_type in ("mousePressed", "mouseReleased"):
            await listing_inventory._call(ws, "Input.dispatchMouseEvent", {
                "type": event_type, "x": float(rect["x"]), "y": float(rect["y"]),
                "button": "left", "clickCount": 1,
            }, cid); cid += 1
        await asyncio.sleep(3)
        return before, after, intent_path


def _execute_text_effect(**kwargs) -> tuple[dict, dict, Path]:
    return asyncio.run(_execute_text_effect_async(**kwargs))


async def _execute_package_effect_async(
    ws_url: str, *, contract: dict, judgement: dict, public_before_path: Path,
    evidence_dir: Path, state_dir: Path,
) -> tuple[dict, dict, Path]:
    import websockets
    import listing_inventory

    mappings, _ = _load_capability_families(DEFAULT_LISTING_CONTRACT_FAMILIES)
    _validate_mutation_contract(contract, mappings)
    proposed = contract.get("proposed_value")
    if (contract.get("changed_field") != "package" or contract.get("before_value") != "PACKAGE_ABSENT"
            or contract.get("allowed_delta") != ["data[Option][0]"] or not isinstance(proposed, dict)
            or set(proposed) != {"title", "price_jpy"}
            or judgement.get("experiment_key") != _experiment_key(
                contract["service_id"], "package", proposed,
            )):
        raise RuntimeError("seller_package_contract_invalid")
    edit_url = f"https://coconala.com/mypage/services/{contract['service_id']}"
    async with websockets.connect(ws_url, ping_interval=None, open_timeout=10,
                                  max_size=40 * 1024 * 1024) as ws:
        cid = 1
        await listing_inventory._call(ws, "Page.enable", {}, cid); cid += 1
        await ws.send(json.dumps({"id": cid, "method": "Page.navigate", "params": {"url": edit_url}})); cid += 1
        _, cid = await listing_inventory._wait_for_load(
            ws, asyncio.get_event_loop().time() + 15, cid,
        )

        async def evaluate(expression: str) -> object:
            nonlocal cid
            response = await listing_inventory._call(
                ws, "Runtime.evaluate", {"expression": expression, "returnByValue": True}, cid,
            )
            cid += 1
            return response.get("result", {}).get("result", {}).get("value")

        before = json.loads(str(await evaluate(SELLER_FORM_EXPRESSION) or "{}"))
        filled = json.loads(str(await evaluate(
            "JSON.stringify((()=>{const form=document.forms[0];"
            "if(!form||[...form.elements].some(e=>(e.name||'').startsWith('data[Option]')))"
            "return {ok:false,reason:'package_not_absent'};"
            "const add=document.querySelector('#addOption');if(!add)return {ok:false,reason:'add_missing'};"
            "add.click();const title=form.querySelector('[name=\"data[Option][0][title]\"]'),"
            "price=form.querySelector('[name=\"data[Option][0][price]\"]'),"
            "opened=form.querySelector('[name=\"data[Option][0][opened]\"]');"
            "if(!title||!price||!opened)return {ok:false,reason:'controls_missing'};"
            "const proposed=" + json.dumps(proposed, ensure_ascii=False) + ";"
            "if(![...price.options].some(o=>o.value===String(proposed.price_jpy)))"
            "return {ok:false,reason:'price_option_missing'};"
            "title.value=proposed.title;price.value=String(proposed.price_jpy);opened.value='1';"
            "for(const e of [title,price,opened]){e.dispatchEvent(new Event('input',{bubbles:true}));"
            "e.dispatchEvent(new Event('change',{bubbles:true}))}"
            "const submit=form.querySelector('button.submitButton.js_button-edit[type=submit]');"
            "if(!submit)return {ok:false,reason:'submit_missing'};submit.scrollIntoView({block:'center'});"
            "const r=submit.getBoundingClientRect();return {ok:true,title:title.value,price:price.value,"
            "opened:opened.value,rect:{x:r.left+r.width/2,y:r.top+r.height/2,w:r.width,h:r.height}}})())"
        ) or "{}"))
        if (filled.get("ok") is not True or filled.get("title") != proposed["title"]
                or filled.get("price") != str(proposed["price_jpy"]) or filled.get("opened") != "1"):
            raise RuntimeError(f"seller_package_fill_failed:{filled.get('reason')}")
        after = json.loads(str(await evaluate(SELLER_FORM_EXPRESSION) or "{}"))
        _validate_package_form_delta(before, after, contract)
        before_path = evidence_dir / "seller-form-before.json"
        after_path = evidence_dir / "seller-form-package-filled.json"
        _atomic_write(before_path, before); _atomic_write(after_path, after)
        intent_path = _effect_intent_path(state_dir, str(judgement["experiment_key"]))
        _atomic_write(intent_path, {
            "version": 1, "status": "prepared", "service_id": contract["service_id"],
            "changed_field": "package", "experiment_key": judgement["experiment_key"],
            "mutation_contract": contract, "public_before_path": str(public_before_path),
            "seller_form_before_path": str(before_path), "prepared_at_epoch": int(time.time()),
            "effect_origin_pass_id": evidence_dir.name, "judgement": judgement,
        })
        rect = filled["rect"]
        if min(float(rect.get("w") or 0), float(rect.get("h") or 0)) <= 0:
            raise RuntimeError("seller_package_submit_not_visible")
        for event_type in ("mousePressed", "mouseReleased"):
            await listing_inventory._call(ws, "Input.dispatchMouseEvent", {
                "type": event_type, "x": float(rect["x"]), "y": float(rect["y"]),
                "button": "left", "clickCount": 1,
            }, cid); cid += 1
        await asyncio.sleep(3)
        return before, after, intent_path


def _execute_package_effect(**kwargs) -> tuple[dict, dict, Path]:
    return asyncio.run(_execute_package_effect_async(**kwargs))


async def _execute_image_effect_async(
    ws_url: str,
    *,
    contract: dict,
    judgement: dict,
    public_before_path: Path,
    evidence_dir: Path,
    state_dir: Path,
) -> tuple[dict, dict, Path]:
    import websockets
    import listing_inventory

    _validate_image_mutation_contract(contract)
    edit_url = f"https://coconala.com/mypage/services/{contract['service_id']}"
    async with websockets.connect(ws_url, ping_interval=None, open_timeout=10, max_size=40 * 1024 * 1024) as ws:
        cid = 1
        await listing_inventory._call(ws, "Page.enable", {}, cid); cid += 1
        await listing_inventory._call(ws, "DOM.enable", {}, cid); cid += 1
        await ws.send(json.dumps({"id": cid, "method": "Page.navigate", "params": {"url": edit_url}})); cid += 1
        _, cid = await listing_inventory._wait_for_load(ws, asyncio.get_event_loop().time() + 15, cid)

        async def evaluate(expression: str) -> object:
            nonlocal cid
            response = await listing_inventory._call(
                ws, "Runtime.evaluate", {"expression": expression, "returnByValue": True}, cid,
            )
            cid += 1
            return response.get("result", {}).get("result", {}).get("value")

        before = json.loads(str(await evaluate(SELLER_FORM_EXPRESSION) or "{}"))
        if contract["service_id"] != GALLERY_SERVICE_ID:
            click = json.loads(str(await evaluate(
                "JSON.stringify((()=>{const b=document.querySelector('.js_upload-select');"
                "if(!b)return {ok:false,reason:'image_add_missing'};b.click();return {ok:true}})())"
            ) or "{}"))
            if click.get("ok") is not True:
                raise RuntimeError(f"seller_image_add_failed:{click.get('reason')}")
            await asyncio.sleep(0.5)
            uploads = [("input.js_upload-button", contract["proposed_value"]["asset_path"])]
        else:
            uploads = []
            for row in contract["proposed_value"]["replacement_assets"]:
                match = re.search(r"-(\d+)\.png$", row["replace_image_id"])
                if match is None:
                    raise RuntimeError("seller_gallery_image_id_invalid")
                uploads.append((f'input[data-service-image-id="{match.group(1)}"]', row["asset_path"]))
        for selector, asset_path in uploads:
            document = await listing_inventory._call(ws, "DOM.getDocument", {"depth": -1, "pierce": True}, cid); cid += 1
            queried = await listing_inventory._call(ws, "DOM.querySelector", {
                "nodeId": document["result"]["root"]["nodeId"], "selector": selector,
            }, cid); cid += 1
            node_id = int(queried.get("result", {}).get("nodeId") or 0)
            if node_id <= 0:
                raise RuntimeError(f"seller_image_file_input_missing:{selector}")
            await listing_inventory._call(ws, "DOM.setFileInputFiles", {
                "nodeId": node_id, "files": [str((GIG_DIR / asset_path).resolve())],
            }, cid); cid += 1
            await asyncio.sleep(0.75)
        await asyncio.sleep(2)
        after = json.loads(str(await evaluate(SELLER_FORM_EXPRESSION) or "{}"))
        _validate_image_form_delta(before, after, contract)
        preview = json.loads(str(await evaluate(
            "JSON.stringify((()=>{const p=[...document.querySelectorAll('input[type=file]')]"
            ".filter(input=>input.files&&input.files.length===1);"
            "const s=document.querySelector('button.submitButton.js_button-edit[type=submit]');"
            f"if(p.length<{len(uploads)})return {{ok:false,reason:'preview_missing',count:p.length}};"
            "if(!s)return {ok:false,reason:'submit_missing'};"
            "s.scrollIntoView({block:'center'});const r=s.getBoundingClientRect();"
            "return {ok:true,rect:{x:r.left+r.width/2,y:r.top+r.height/2,w:r.width,h:r.height}}})())"
        ) or "{}"))
        if preview.get("ok") is not True:
            raise RuntimeError(f"seller_image_preview_failed:{preview.get('reason')}")
        before_path, after_path = evidence_dir / "seller-form-before.json", evidence_dir / "seller-form-image-filled.json"
        _atomic_write(before_path, before)
        _atomic_write(after_path, after)
        intent_path = _effect_intent_path(state_dir, str(judgement["experiment_key"]))
        intent = {
            "version": 1, "status": "prepared", "service_id": contract["service_id"],
            "changed_field": "image", "experiment_key": judgement["experiment_key"],
            "asset_path": contract["proposed_value"].get("asset_path"),
            "asset_sha256": contract["proposed_value"].get("asset_sha256"), "mutation_contract": contract,
            "public_before_path": str(public_before_path), "seller_form_before_path": str(before_path),
            "prepared_at_epoch": int(time.time()), "effect_origin_pass_id": evidence_dir.name,
            "judgement": judgement,
        }
        _atomic_write(intent_path, intent)
        rect = preview["rect"]
        if min(float(rect.get("w") or 0), float(rect.get("h") or 0)) <= 0:
            raise RuntimeError("seller_image_submit_not_visible")
        for event_type in ("mousePressed", "mouseReleased"):
            await listing_inventory._call(ws, "Input.dispatchMouseEvent", {
                "type": event_type, "x": float(rect["x"]), "y": float(rect["y"]),
                "button": "left", "clickCount": 1,
            }, cid)
            cid += 1
        await asyncio.sleep(3)
        return before, after, intent_path


def _execute_image_effect(**kwargs) -> tuple[dict, dict, Path]:
    return asyncio.run(_execute_image_effect_async(**kwargs))


def run_once(args: argparse.Namespace) -> tuple[int, dict]:
    started_at = time.monotonic()
    pass_id = args.pass_id or f"storefront-direct-{time.time_ns()}-{os.getpid()}"
    minimum_epoch = int(time.time())
    args.state_dir.mkdir(parents=True, exist_ok=True)
    output = args.output or args.state_dir / "current.json"
    if getattr(args, "auto_cadence", False):
        try:
            args.incremental = _auto_cadence_is_incremental(
                args.state_dir, minimum_epoch, int(args.full_interval_seconds),
            )
        except RuntimeError as error:
            row = _receipt(pass_id, status="failed", reason=str(error).strip() or type(error).__name__)
            row = _persist_receipt(args, output, row)
            return 1, row
    try:
        brake_held = args.operator_brake.exists()
    except OSError as error:
        row = _receipt(pass_id, status="failed", reason=f"operator_brake_check_failed:{error}")
        row = _persist_receipt(args, output, row)
        return 1, row
    if brake_held:
        row = _receipt(pass_id, status="operator_brake", reason="storefront_operator_brake_held")
        row = _persist_receipt(args, output, row)
        return 0, row

    lock_path = args.state_dir / "owner.lock"
    with lock_path.open("a+", encoding="utf-8") as owner_lock:
        try:
            fcntl.flock(owner_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            row = _receipt(pass_id, status="busy", reason="storefront_owner_busy")
            row = _persist_receipt(args, output, row)
            return 0, row

        lease = None
        released = False
        try:
            browser = subprocess.run(
                ["/bin/bash", str(args.ensure_browser_script)],
                capture_output=True, text=True, check=False, timeout=60,
            )
            if browser.returncode != 0 or browser.stdout.strip() not in {"ALIVE", "RECOVERED"}:
                detail = (browser.stdout.strip() or browser.stderr.strip() or "unknown")[:200]
                raise RuntimeError(f"storefront_browser_unavailable:{detail}")
            task = f"gig-storefront-direct-{pass_id}"
            lease = _lease(args.lease_script, "acquire", task)
            ws_url = str(lease.get("ws") or "")
            if not ws_url.startswith("ws://"):
                raise RuntimeError("lease_ws_invalid")
            import listing_inventory

            inventory_path = args.state_dir / "evidence" / pass_id / "official-inventory.json"
            inventory = listing_inventory.observe_storefront(
                output_path=inventory_path, ws_url=ws_url, include_contract_sources=True,
            )
            observed = int(inventory.get("service_count") or 0)
            if observed <= 0 or observed != len(inventory.get("services") or []):
                raise RuntimeError("official_inventory_empty_or_invalid")
            contract_sources = inventory.get("_contract_sources")
            source_dicts = isinstance(contract_sources, list) and all(
                isinstance(source, dict) for source in contract_sources
            )
            source_ids = [source.get("service_id") for source in contract_sources] if source_dicts else []
            inventory_ids = {
                str(service.get("service_id"))
                for service in inventory["services"]
                if isinstance(service, dict)
            }
            if (
                not source_dicts
                or len(contract_sources) != observed
                or not all(type(service_id) is str and service_id.isdigit() for service_id in source_ids)
                or len(set(source_ids)) != len(source_ids)
                or set(source_ids) != inventory_ids
            ):
                raise RuntimeError("official_service_contract_invalid")
            expected_catalog_sha256 = str(
                getattr(args, "expected_catalog_sha256", "") or ""
            ).strip().lower()
            if expected_catalog_sha256 and (
                not re.fullmatch(r"[0-9a-f]{64}", expected_catalog_sha256)
                or str(inventory.get("content_sha256") or "").lower() != expected_catalog_sha256
            ):
                raise RuntimeError("official_catalog_version_stale")
            validated_contracts = [
                _service_contract(source, str(inventory["observed_at"])) for source in contract_sources
            ]
            if getattr(args, "incremental", False):
                cutoff = int(getattr(args, "accounting_cutoff_epoch", 0) or time.time())
                if cutoff <= 0:
                    raise RuntimeError("incremental_cutoff_invalid")
                listing_contracts = _load_listing_contracts(
                    getattr(args, "listing_contract_dir", DEFAULT_LISTING_CONTRACT_DIR), validated_contracts,
                    getattr(args, "listing_contract_families", DEFAULT_LISTING_CONTRACT_FAMILIES),
                    args.state_dir / "new-listing-drafts.jsonl",
                )
                funnel = _join_funnel(
                    args.state_dir, validated_contracts,
                    getattr(args, "reply_transcripts", DEFAULT_REPLY_TRANSCRIPTS),
                    getattr(args, "applied", DEFAULT_APPLIED), getattr(args, "earnings", DEFAULT_EARNINGS),
                    getattr(args, "projects_dir", DEFAULT_PROJECTS), cutoff,
                    getattr(args, "negotiate_run_log", DEFAULT_NEGOTIATE_RUN_LOG),
                )
                portfolio = _allocate_portfolio(
                    args.state_dir, validated_contracts, funnel,
                    getattr(args, "scorecard", DEFAULT_SCORECARD), cutoff,
                )
                inquiry_context = _materialize_inquiry_context(
                    args.state_dir, listing_contracts,
                    getattr(args, "negotiate_context_acks", DEFAULT_NEGOTIATE_CONTEXT_ACKS), cutoff,
                )
                catalog_analytics = _last_known_good_catalog_analytics(
                    args.state_dir, source_ids, cutoff,
                )
                competitor_evidence = _last_full_competitor_evidence(args.state_dir, cutoff)
                contract_count = sum(int(_append_contract_once(
                    args.state_dir / "offer-contracts.jsonl", contract,
                )) for contract in validated_contracts)
                listing_contract_count = sum(int(_append_key_once(
                    args.state_dir / "listing-contracts.jsonl", "contract_key", contract,
                )) for contract in listing_contracts)
                release = _lease(args.lease_script, "release", task, lease)
                released = release.get("released") == task
                if not released:
                    raise RuntimeError("lease_release_unproven")
                analytics_epoch = int((catalog_analytics or {}).get("observed_at_epoch") or 0)
                row = _receipt(
                    pass_id, status="completed", reason="incremental_catalog_funnel_readback",
                    official_services_read=observed, competitor_evidence_count=None,
                    competitor_evidence=competitor_evidence,
                    offer_contracts_appended=contract_count,
                    listing_contracts_appended=listing_contract_count,
                    listing_contracts_active=len(listing_contracts),
                    listing_contracts_total=sum(1 for line in
                        (args.state_dir / "listing-contracts.jsonl").read_text(encoding="utf-8").splitlines()
                        if line.strip()),
                    inventory_content_sha256=inventory.get("content_sha256"),
                    incremental_public_readback=1, catalog_analytics=catalog_analytics,
                    funnel=funnel, portfolio=portfolio, inquiry_context=inquiry_context,
                    new_listing_draft={"status": "not_checked_incremental", "effect": 0,
                                       "readback": 0, "public_effect": 0},
                    accounting={"cutoff_epoch": cutoff, "minute": cutoff // 60,
                                "hour": cutoff // 3600, "day": cutoff // 86400,
                                "analytics_observed_at_epoch": analytics_epoch},
                    runtime_seconds=round(time.monotonic() - started_at, 3),
                    lease={"task": task, "context_id": lease.get("context_id"),
                           "target_id": lease.get("target_id"), "generation": lease.get("generation"),
                           "released": True},
                )
                row = _persist_receipt(args, output, row)
                return 0, row
            capability_families, capability_templates = _load_capability_families(
                getattr(args, "listing_contract_families", DEFAULT_LISTING_CONTRACT_FAMILIES),
            )
            presentation_snapshot = _seller_snapshot_for(ws_url, "4308502")
            scope_snapshot = _seller_snapshot_for(ws_url, "4244910")
            title_render = _render_prepared_mutation(
                args.state_dir, presentation_snapshot, "4308502", "title", capability_families,
            ) or _render_text_mutation(
                getattr(args, "title_mutation", DEFAULT_TITLE_MUTATION), validated_contracts,
                presentation_snapshot, capability_families,
            )
            body_render = _render_text_mutation(
                getattr(args, "body_mutation", DEFAULT_BODY_MUTATION), validated_contracts,
                presentation_snapshot, capability_families,
            )
            scope_render = _render_prepared_mutation(
                args.state_dir, scope_snapshot, "4244910", "body", capability_families,
            ) or _render_text_mutation(
                getattr(args, "scope_mutation", DEFAULT_SCOPE_MUTATION), validated_contracts,
                scope_snapshot, capability_families,
            )
            package_render = _render_text_mutation(
                getattr(args, "package_mutation", DEFAULT_PACKAGE_MUTATION), validated_contracts,
                presentation_snapshot, capability_families,
            )
            faq_render = _render_text_mutation(
                getattr(args, "faq_mutation", DEFAULT_FAQ_MUTATION), validated_contracts,
                presentation_snapshot, capability_families,
            )
            price_render = _render_text_mutation(
                getattr(args, "price_mutation", DEFAULT_PRICE_MUTATION), validated_contracts,
                presentation_snapshot, capability_families,
            )
            title_render_path = inventory_path.parent / "mutation-render-title.json"
            body_render_path = inventory_path.parent / "mutation-render-body.json"
            scope_render_path = inventory_path.parent / "mutation-render-scope.json"
            package_render_path = inventory_path.parent / "mutation-render-package.json"
            faq_render_path = inventory_path.parent / "mutation-render-faq.json"
            price_render_path = inventory_path.parent / "mutation-render-price.json"
            _atomic_write(title_render_path, title_render)
            _atomic_write(body_render_path, body_render)
            _atomic_write(scope_render_path, scope_render)
            _atomic_write(package_render_path, package_render)
            _atomic_write(faq_render_path, faq_render)
            _atomic_write(price_render_path, price_render)
            listing_contracts = _load_listing_contracts(
                getattr(args, "listing_contract_dir", DEFAULT_LISTING_CONTRACT_DIR), validated_contracts,
                getattr(args, "listing_contract_families", DEFAULT_LISTING_CONTRACT_FAMILIES),
                args.state_dir / "new-listing-drafts.jsonl",
            )
            competitor_manifest = _collect_competitors(
                ws_url,
                inventory_path.parent,
                {str(row.get("service_id")) for row in inventory["services"]},
            )
            own_page = _observe_own_page(ws_url, inventory_path.parent)
            image_asset = _load_image_contract(getattr(args, "image_contract", DEFAULT_IMAGE_CONTRACT))
            image_render = _render_image_mutation(own_page, image_asset, capability_families)
            image_render_path = inventory_path.parent / "mutation-render-image.json"
            _atomic_write(image_render_path, image_render)
            gallery_page = _observe_own_page(
                ws_url, inventory_path.parent, "own-gallery-candidate.json", GALLERY_SERVICE_ID,
            )
            gallery_asset = _load_gallery_contract(
                getattr(args, "gallery_contract", DEFAULT_GALLERY_CONTRACT)
            )
            gallery_source = next(
                (row for row in validated_contracts if row["service_id"] == GALLERY_SERVICE_ID), None
            )
            if gallery_source is None:
                raise RuntimeError("storefront_gallery_offer_contract_missing")
            gallery_render = (_render_gallery_mutation(
                gallery_page, gallery_source["service_version_sha256"],
                gallery_asset, capability_families,
            ) if gallery_page.get("service_image_ids") == gallery_asset["before_image_ids"]
                else _render_published_gallery_mutation(args.state_dir, gallery_page))
            gallery_render_path = inventory_path.parent / "mutation-render-gallery.json"
            _atomic_write(gallery_render_path, gallery_render)
            mutation_contracts = [render["contract"] for render in (
                image_render, gallery_render, title_render, body_render, scope_render,
                package_render, faq_render, price_render,
            )]
            analytics = _collect_analytics(
                args.state_dir, inventory_path.parent, int(time.time()), sorted(inventory_ids),
                getattr(args, "default_tab_script", DEFAULT_TAB),
            )
            funnel = _join_funnel(
                args.state_dir, validated_contracts,
                getattr(args, "reply_transcripts", DEFAULT_REPLY_TRANSCRIPTS),
                getattr(args, "applied", DEFAULT_APPLIED), getattr(args, "earnings", DEFAULT_EARNINGS),
                getattr(args, "projects_dir", DEFAULT_PROJECTS), int(time.time()),
                getattr(args, "negotiate_run_log", DEFAULT_NEGOTIATE_RUN_LOG),
            )
            portfolio = _allocate_portfolio(
                args.state_dir, validated_contracts, funnel,
                getattr(args, "scorecard", DEFAULT_SCORECARD), int(time.time()),
            )
            inquiry_context = _materialize_inquiry_context(
                args.state_dir, listing_contracts,
                getattr(args, "negotiate_context_acks", DEFAULT_NEGOTIATE_CONTEXT_ACKS), int(time.time()),
            )
            next_hypothesis = _prepare_next_hypothesis(
                getattr(args, "scorecard", DEFAULT_SCORECARD),
                args.state_dir / "effects.jsonl", args.state_dir / "outcomes.jsonl",
                validated_contracts, int(time.time()), mutation_contracts,
            )
            pending_effect = None
            proposal_agent = None
            generated_render = None
            generated_render_path = None
            capability_paths = {str(Path(path).resolve()) for path in args.capability_evidence}
            recovery = _pending_recovery(args.state_dir, own_page, ws_url, inventory_path.parent)
            if recovery is not None:
                judgement = recovery.get("judgement")
                if not isinstance(judgement, dict):
                    raise RuntimeError("pending_effect_judgement_missing")
                if (recovery.get("changed_field") not in {"FAQ", "image", "title", "body", "package", "price"}
                        or (recovery.get("changed_field") == "FAQ"
                            and recovery.get("service_id") != TARGET_SERVICE_ID)
                        or recovery.get("experiment_key") != judgement.get("experiment_key")):
                    raise RuntimeError("pending_effect_identity_invalid")
                public_before = json.loads(Path(recovery["public_before_path"]).read_text(encoding="utf-8"))
                seller_before = json.loads(Path(recovery["seller_form_before_path"]).read_text(encoding="utf-8"))
                seller_after = recovery.get("_recovery_seller_snapshot") or _seller_snapshot_for(
                    ws_url, str(recovery["service_id"]),
                )
                if recovery["changed_field"] == "image":
                    mutation_contract = recovery.get("mutation_contract")
                    if not isinstance(mutation_contract, dict):
                        raise RuntimeError("pending_image_mutation_contract_missing")
                    recovery_page = recovery.get("_recovery_public_page", own_page)
                    if not isinstance(recovery_page, dict):
                        raise RuntimeError("pending_image_public_readback_missing")
                    _validate_public_image_acceptance(public_before, recovery_page, mutation_contract)
                elif recovery["changed_field"] in {"title", "body", "package", "price"}:
                    mutation_contract = recovery.get("mutation_contract")
                    if not isinstance(mutation_contract, dict):
                        raise RuntimeError("pending_text_mutation_contract_missing")
                    recovery_page = recovery.get("_recovery_public_page")
                    if not isinstance(recovery_page, dict):
                        raise RuntimeError("pending_text_public_readback_missing")
                    _validate_text_public_acceptance(public_before, recovery_page, mutation_contract)
                    if recovery["changed_field"] == "package":
                        _validate_package_form_delta(seller_before, seller_after, mutation_contract)
                    else:
                        _validate_text_form_delta(seller_before, seller_after, mutation_contract)
                else:
                    question, answer = str(recovery["question"]), str(recovery["answer"])
                    _validate_public_acceptance(public_before, own_page, question, answer)
                    _validate_form_delta(seller_before, seller_after, question, answer)
                seller_after_path = inventory_path.parent / "seller-form-recovered.json"
                _atomic_write(seller_after_path, seller_after)
                judgement_path = inventory_path.parent / "judgement-recovered.json"
                _atomic_write(judgement_path, judgement)
                intent_path = Path(recovery["intent_path"])
                durable_recovery = {key: value for key, value in recovery.items()
                                    if key != "intent_path" and not key.startswith("_")}
                _atomic_write(intent_path, {
                    **durable_recovery, "status": "observed",
                    "public_after_path": str(
                        inventory_path.parent / (
                            f"recovery-public-{recovery['service_id']}.json"
                            if recovery["changed_field"] in {"title", "body", "package", "price", "image"}
                            and recovery["service_id"] != TARGET_SERVICE_ID else "own-candidate.json"
                        )
                    ),
                    "seller_form_after_path": str(seller_after_path),
                    "observed_at_epoch": int(time.time()),
                })
                pending_effect = {
                    "intent_path": intent_path, "changed_field": recovery["changed_field"],
                    "public_before_path": Path(recovery["public_before_path"]),
                    "public_after_path": inventory_path.parent / (
                        f"recovery-public-{recovery['service_id']}.json"
                        if recovery["changed_field"] in {"title", "body", "package", "price", "image"}
                        and recovery["service_id"] != TARGET_SERVICE_ID else "own-candidate.json"
                    ),
                    "seller_form_before_path": Path(recovery["seller_form_before_path"]),
                    "seller_form_after_path": seller_after_path, "recovered": True,
                }
                if recovery["changed_field"] == "FAQ":
                    pending_effect.update({"question": question, "answer": answer})
            else:
                proposal_noop = None
                if (next_hypothesis is not None
                        and next_hypothesis.get("guard_reason") == "proposal_contract_required"):
                    proposal_service_id = str(next_hypothesis["service_id"])
                    proposal_source = next(
                        (row for row in validated_contracts if row["service_id"] == proposal_service_id), None,
                    )
                    family_name = capability_families.get(proposal_service_id)
                    family = capability_templates.get(str(family_name or ""))
                    if proposal_source is None or not isinstance(family_name, str) or not isinstance(family, dict):
                        raise RuntimeError("storefront_proposal_context_missing")
                    proposal_snapshot = (
                        presentation_snapshot if proposal_service_id == "4308502"
                        else scope_snapshot if proposal_service_id == "4244910"
                        else _seller_package_snapshot_for(ws_url, proposal_service_id)
                        if next_hypothesis.get("field") == "package"
                        else _seller_snapshot_for(ws_url, proposal_service_id)
                    )
                    proposal_snapshot_path = inventory_path.parent / f"proposal-seller-{proposal_service_id}.json"
                    _atomic_write(proposal_snapshot_path, proposal_snapshot)
                    proposal_public = _observe_own_page(
                        ws_url, inventory_path.parent, f"proposal-public-{proposal_service_id}.json",
                        proposal_service_id,
                    )
                    proposal, proposal_agent, allowed_refs = _invoke_proposal(
                        runner=args.runner,
                        schema=getattr(args, "proposal_schema", DEFAULT_PROPOSAL_SCHEMA),
                        workdir=args.workdir,
                        evidence_dir=inventory_path.parent / "proposal-agent", hypothesis=next_hypothesis,
                        source=proposal_source, seller_snapshot=proposal_snapshot,
                        family_name=family_name, family=family, manifest=competitor_manifest,
                        capability_paths=capability_paths, timeout_seconds=args.timeout_seconds,
                    )
                    generated_contract = _seal_generated_proposal(
                        proposal, next_hypothesis, proposal_source, proposal_snapshot,
                        family_name, capability_families, allowed_refs, inventory_path.parent,
                        proposal_public,
                    )
                    _atomic_write(inventory_path.parent / "proposal-record.json", {
                        "version": 1, "proposal": proposal, "route": proposal_agent,
                        "service_id": proposal_service_id, "changed_field": next_hypothesis["field"],
                        "contract_sha256": (generated_contract or {}).get("contract_sha256"),
                    })
                    if generated_contract is None:
                        proposal_noop = proposal
                    else:
                        field = generated_contract["allowed_delta"][0]
                        generated_render = {
                            "version": 1, "contract": generated_contract,
                            "before": {field: generated_contract["before_value"]},
                            "after": {field: generated_contract["proposed_value"]},
                            "delta": [field], "published": False,
                        }
                        generated_render_path = inventory_path.parent / "mutation-render-generated.json"
                        _atomic_write(generated_render_path, generated_render)
                        mutation_contracts.append(generated_contract)
                        next_hypothesis = _prepare_next_hypothesis(
                            getattr(args, "scorecard", DEFAULT_SCORECARD),
                            args.state_dir / "effects.jsonl", args.state_dir / "outcomes.jsonl",
                            validated_contracts, int(time.time()), mutation_contracts,
                        )
                mutation_contract = None
                if proposal_noop is not None:
                    judgement = _guarded_noop({
                        "decision": "no_op", "service_id": None, "changed_field": None,
                        "before_value": None, "proposed_value": None,
                        "hypothesis": str(proposal_noop["hypothesis"]),
                        "competitor_evidence_paths": [], "capability_evidence_paths": [],
                        "success_metric": None, "observation_window_days": None,
                        "no_op_reason": str(proposal_noop["no_op_reason"]),
                        "experiment_key": None, "uncertainty": proposal_noop.get("uncertainty", []),
                    }, str(proposal_noop["no_op_reason"]))
                elif next_hypothesis is None:
                    judgement = _guarded_noop({
                        "decision": "no_op", "service_id": None, "changed_field": None,
                        "before_value": None, "proposed_value": None,
                        "hypothesis": "No current unfenced backlog item has an exact executable mutation contract.",
                        "competitor_evidence_paths": [], "capability_evidence_paths": [],
                        "success_metric": None, "observation_window_days": None,
                        "no_op_reason": "no_executable_unfenced_mutation_contract",
                        "experiment_key": None, "uncertainty": [],
                    }, "no_executable_unfenced_mutation_contract")
                elif not next_hypothesis["executable"]:
                    raw_judgement = {
                        "decision": "no_op", "service_id": None, "changed_field": None,
                        "before_value": None, "proposed_value": None,
                        "hypothesis": str(next_hypothesis["reason"]),
                        "competitor_evidence_paths": [], "capability_evidence_paths": [],
                        "success_metric": None, "observation_window_days": None,
                        "no_op_reason": str(next_hypothesis["guard_reason"]),
                        "experiment_key": None, "uncertainty": [],
                    }
                    judgement = _guard_judgement(
                        raw_judgement,
                        own_page=own_page, competitor_manifest=competitor_manifest,
                        capability_paths=capability_paths, evidence_dir=inventory_path.parent,
                        effects_path=args.state_dir / "effects.jsonl", minimum_epoch=minimum_epoch,
                        now=int(time.time()),
                    )
                elif next_hypothesis is not None and next_hypothesis.get("field") == "image":
                    mutation_contract = next((contract for contract in mutation_contracts
                                              if contract["contract_sha256"]
                                              == next_hypothesis["mutation_contract_sha256"]), None)
                    if mutation_contract is None:
                        raise RuntimeError("storefront_image_mutation_contract_missing")
                    _atomic_write(inventory_path.parent / "mutation-contract.json", mutation_contract)
                    judgement = _image_judgement(next_hypothesis, mutation_contract)
                elif next_hypothesis is not None and next_hypothesis.get("field") in {
                    "title", "body", "package", "price",
                }:
                    mutation_contract = next((contract for contract in mutation_contracts
                                              if contract["contract_sha256"]
                                              == next_hypothesis["mutation_contract_sha256"]), None)
                    if mutation_contract is None:
                        raise RuntimeError("storefront_text_mutation_contract_missing")
                    _atomic_write(inventory_path.parent / "mutation-contract.json", mutation_contract)
                    judgement = _text_judgement(
                        next_hypothesis, mutation_contract, args.state_dir / "effects.jsonl", int(time.time()),
                    )
                else:
                    raw_judgement = _invoke_judge(
                        runner=args.runner, schema=args.schema, workdir=args.workdir,
                        evidence_dir=inventory_path.parent / "judge", own_page=own_page,
                        manifest=competitor_manifest, capability_paths=capability_paths,
                        timeout_seconds=args.timeout_seconds,
                    )
                    judgement = _guard_judgement(
                        raw_judgement,
                        own_page=own_page, competitor_manifest=competitor_manifest,
                        capability_paths=capability_paths, evidence_dir=inventory_path.parent,
                        effects_path=args.state_dir / "effects.jsonl", minimum_epoch=minimum_epoch,
                        now=int(time.time()),
                    )
                judgement_path = inventory_path.parent / "judgement.json"
                _atomic_write(judgement_path, judgement)
                if judgement["decision"] == "change":
                    presend_path = inventory_path.parent / "presend-own-page.json"
                    presend = _observe_own_page(
                        ws_url, inventory_path.parent, presend_path.name, str(judgement["service_id"]),
                    )
                    if judgement["changed_field"] not in {"title", "body", "package", "price"}:
                        _presend_guard(judgement, presend, mutation_contract)
                    if args.effect:
                        if judgement["changed_field"] == "image":
                            seller_before, _, intent_path = _execute_image_effect(
                                ws_url=ws_url, contract=mutation_contract, judgement=judgement,
                                public_before_path=presend_path, evidence_dir=inventory_path.parent,
                                state_dir=args.state_dir,
                            )
                        elif judgement["changed_field"] == "package":
                            seller_before, _, intent_path = _execute_package_effect(
                                ws_url=ws_url, contract=mutation_contract, judgement=judgement,
                                public_before_path=presend_path, evidence_dir=inventory_path.parent,
                                state_dir=args.state_dir,
                            )
                        elif judgement["changed_field"] in {"title", "body", "price"}:
                            seller_before, _, intent_path = _execute_text_effect(
                                ws_url=ws_url, contract=mutation_contract, judgement=judgement,
                                public_before_path=presend_path, evidence_dir=inventory_path.parent,
                                state_dir=args.state_dir,
                            )
                        else:
                            question, answer = _split_faq(str(judgement["proposed_value"]))
                            seller_before, _, intent_path = _execute_faq_effect(
                                ws_url=ws_url, question=question, answer=answer, judgement=judgement,
                                public_before_path=presend_path, evidence_dir=inventory_path.parent,
                                state_dir=args.state_dir,
                            )
                        public_after_path = inventory_path.parent / "after-public.json"
                        public_after = _observe_own_page(
                            ws_url, inventory_path.parent, public_after_path.name, str(judgement["service_id"]),
                        )
                        seller_after = _seller_snapshot_for(ws_url, str(judgement["service_id"]))
                        if judgement["changed_field"] == "image":
                            _validate_public_image_acceptance(presend, public_after, mutation_contract)
                        elif judgement["changed_field"] in {"title", "body", "package", "price"}:
                            _validate_text_public_acceptance(presend, public_after, mutation_contract)
                            if judgement["changed_field"] == "package":
                                _validate_package_form_delta(seller_before, seller_after, mutation_contract)
                            else:
                                _validate_text_form_delta(seller_before, seller_after, mutation_contract)
                        else:
                            _validate_public_acceptance(presend, public_after, question, answer)
                            _validate_form_delta(seller_before, seller_after, question, answer)
                        seller_after_path = inventory_path.parent / "seller-form-after.json"
                        _atomic_write(seller_after_path, seller_after)
                        intent = json.loads(intent_path.read_text(encoding="utf-8"))
                        _atomic_write(intent_path, {
                            **intent, "status": "observed", "public_after_path": str(public_after_path),
                            "seller_form_after_path": str(seller_after_path),
                            "observed_at_epoch": int(time.time()),
                        })
                        pending_effect = {
                            "intent_path": intent_path, "changed_field": judgement["changed_field"],
                            "public_before_path": presend_path, "public_after_path": public_after_path,
                            "seller_form_before_path": Path(intent["seller_form_before_path"]),
                            "seller_form_after_path": seller_after_path, "recovered": False,
                        }
                        if judgement["changed_field"] == "FAQ":
                            pending_effect.update({"question": question, "answer": answer})
            _lease(args.lease_script, "heartbeat", task, lease)
            release = _lease(args.lease_script, "release", task, lease)
            released = release.get("released") == task
            if not released:
                raise RuntimeError("lease_release_unproven")

            import storefront_draft

            new_listing_path = getattr(args, "new_listing_contract", DEFAULT_NEW_LISTING_CONTRACT)
            new_listing_contract = storefront_draft.load_contract(new_listing_path)
            create_family = None
            create_draft_claim = None
            fixed_candidate_public = new_listing_contract["draft_service_id"] in inventory_ids
            if fixed_candidate_public and next_hypothesis is None and observed < 20:
                source_service_id = new_listing_contract["draft_service_id"]
                create_source = next((row for row in validated_contracts
                                      if row["service_id"] == source_service_id), None)
                create_family = capability_families.get(source_service_id)
                create_template = capability_templates.get(str(create_family or ""))
                if create_source is None or not isinstance(create_family, str) or not isinstance(create_template, dict):
                    raise RuntimeError("storefront_create_source_contract_missing")
                demand = {**new_listing_contract["demand_evidence"],
                          "evidence_path": str(Path(new_listing_path).resolve())}
                create_proposal, create_route, create_allowed_refs = _invoke_create_proposal(
                    runner=getattr(args, "runner", DEFAULT_RUNNER),
                    schema=getattr(args, "create_proposal_schema", DEFAULT_CREATE_PROPOSAL_SCHEMA),
                    workdir=args.workdir,
                    evidence_dir=inventory_path.parent / "create-proposal-agent",
                    source=create_source, family_name=create_family, family=create_template,
                    demand=demand, capability_paths=capability_paths,
                    catalog_titles=[str(row.get("title") or "") for row in inventory["services"]],
                    timeout_seconds=args.timeout_seconds,
                )
                proposal_agent = create_route
                if create_proposal.get("decision") == "create" and args.effect:
                    create_draft_claim = storefront_draft.create_or_claim_blank_draft(
                        getattr(args, "default_tab_script", DEFAULT_TAB)
                    )
                    blueprint = {**new_listing_contract,
                                 "demand_evidence_path": str(Path(new_listing_path).resolve())}
                    new_listing_contract = _seal_create_contract(
                        create_proposal, source=create_source, family_name=create_family,
                        allowed_refs=create_allowed_refs, blueprint=blueprint,
                        seller_snapshot=_seller_snapshot_for(ws_url, source_service_id),
                        draft_service_id=str(create_draft_claim["draft_service_id"]),
                        evidence_dir=inventory_path.parent / "create-contract",
                    )
                    if new_listing_contract is None:
                        raise RuntimeError("storefront_create_contract_missing")
                    _atomic_write(inventory_path.parent / "generated-create-contract.json",
                                  new_listing_contract)
            candidate_id = new_listing_contract["draft_service_id"]
            candidate_public = candidate_id in inventory_ids
            duplicate_title = any(
                str(service.get("title") or "") == new_listing_contract["public_fields"]["expected_title"]
                and str(service.get("service_id") or "") != candidate_id
                for service in inventory["services"] if isinstance(service, dict)
            )
            known_draft_image_identity = None
            draft_ledger_path = args.state_dir / "new-listing-drafts.jsonl"
            if draft_ledger_path.exists():
                for line in reversed(draft_ledger_path.read_text(encoding="utf-8").splitlines()):
                    try:
                        prior_draft = json.loads(line)
                    except json.JSONDecodeError as error:
                        raise RuntimeError("new_listing_draft_ledger_invalid") from error
                    if (prior_draft.get("contract_sha256") == new_listing_contract["contract_sha256"]
                            and prior_draft.get("status") == "published"):
                        known_draft_image_identity = str(prior_draft.get("public_image_identity") or "")
                        if not known_draft_image_identity:
                            try:
                                prior_public = json.loads(
                                    Path(str(prior_draft["evidence_path"])).read_text(encoding="utf-8")
                                )
                            except (OSError, KeyError, json.JSONDecodeError) as error:
                                raise RuntimeError("published_draft_evidence_missing") from error
                            for image_url in prior_public.get("images") or []:
                                match = re.search(
                                    r"service_images/original/([A-Za-z0-9-]+\.(?:png|jpe?g|webp))",
                                    str(image_url), re.IGNORECASE,
                                )
                                if match is not None:
                                    known_draft_image_identity = match.group(1)
                                    break
                        if not known_draft_image_identity:
                            raise RuntimeError("published_draft_image_identity_missing")
                        break
            draft_result = (storefront_draft.readback_published_draft(
                new_listing_contract,
                getattr(args, "default_tab_script", DEFAULT_TAB),
                inventory_path.parent,
                known_image_identity=known_draft_image_identity,
            ) if candidate_public else (
                storefront_draft.prepare_draft(
                    new_listing_contract,
                    getattr(args, "default_tab_script", DEFAULT_TAB),
                    inventory_path.parent,
                )
                if args.effect else {
                    "version": 1,
                    "candidate_key": new_listing_contract["candidate_key"],
                    "contract_sha256": new_listing_contract["contract_sha256"],
                    "draft_service_id": new_listing_contract["draft_service_id"],
                    "status": "effect_disabled",
                    "effect": 0,
                    "readback": 0,
                    "public_effect": 0,
                }
            ))
            conflicting_hypothesis = (
                next_hypothesis
                if next_hypothesis is not None
                and str(next_hypothesis.get("service_id") or "") == candidate_id
                and next_hypothesis.get("guard_reason")
                else None
            )
            publication_guard = (
                "already_public" if candidate_public
                else "duplicate_listing_title" if duplicate_title
                else "catalog_capacity_exhausted" if observed >= 20
                else "existing_listing_effect_open" if pending_effect is not None
                else str(conflicting_hypothesis["guard_reason"])
                if conflicting_hypothesis is not None else None
            )
            if publication_guard is not None:
                draft_result = {**draft_result, "publication_guard": publication_guard}
            elif args.effect:
                draft_result = storefront_draft.publish_draft(
                    new_listing_contract,
                    getattr(args, "default_tab_script", DEFAULT_TAB),
                    inventory_path.parent,
                )
            draft_result = {**draft_result,
                            "capability_family": create_family or capability_families.get(candidate_id),
                            "blank_draft_claim": create_draft_claim}

            for name in STATE_FILES:
                path = args.state_dir / name
                if not path.exists():
                    path.touch(mode=0o600)
            contract_count = 0
            for contract in validated_contracts:
                contract_count += int(_append_contract_once(
                    args.state_dir / "offer-contracts.jsonl",
                    contract,
                ))
            listing_contract_count = 0
            for contract in listing_contracts:
                listing_contract_count += int(_append_key_once(
                    args.state_dir / "listing-contracts.jsonl", "contract_key", contract,
                ))
            listing_contract_total = sum(
                1 for line in (args.state_dir / "listing-contracts.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
            _append_key_once(
                args.state_dir / "new-listing-drafts.jsonl",
                "contract_sha256",
                draft_result,
            )
            accepted_effect = 0
            accepted_readback = 0
            if pending_effect is not None:
                effect_row = {
                    "version": 1, "status": "accepted", "effect": 1,
                    "accepted_at_epoch": int(time.time()),
                    "pass_id": pass_id, "effect_origin_pass_id": (
                        json.loads(pending_effect["intent_path"].read_text(encoding="utf-8"))
                        .get("effect_origin_pass_id", pass_id)
                    ),
                    "service_id": str(judgement["service_id"]), "changed_field": pending_effect["changed_field"],
                    "before_value": judgement.get("before_value"), "after_value": judgement.get("proposed_value"),
                    "experiment_key": judgement["experiment_key"],
                    "public_before_path": str(pending_effect["public_before_path"]),
                    "public_after_path": str(pending_effect["public_after_path"]),
                    "seller_form_before_path": str(pending_effect["seller_form_before_path"]),
                    "seller_form_after_path": str(pending_effect["seller_form_after_path"]),
                    "recovered": pending_effect["recovered"],
                }
                if pending_effect["changed_field"] == "FAQ":
                    effect_row.update({
                        "question": pending_effect["question"], "answer": pending_effect["answer"],
                    })
                elif pending_effect["changed_field"] == "image":
                    effect_row.update({
                        "asset_sha256": judgement.get("proposed_value"),
                        "public_image_ids": json.loads(
                            Path(pending_effect["public_after_path"]).read_text(encoding="utf-8")
                        ).get("service_image_ids"),
                    })
                else:
                    effect_row["contract_sha256"] = str(
                        json.loads(pending_effect["intent_path"].read_text(encoding="utf-8"))
                        .get("mutation_contract", {}).get("contract_sha256") or ""
                    )
                appended = _append_effect_once(args.state_dir / "effects.jsonl", effect_row)
                _append_effect_once(args.state_dir / "experiments.jsonl", {
                    "version": 1, "status": "accepted", "experiment_key": judgement["experiment_key"],
                    "service_id": str(judgement["service_id"]), "changed_field": pending_effect["changed_field"],
                    "accepted_at_epoch": effect_row["accepted_at_epoch"],
                    "success_metric": judgement.get("success_metric"),
                    "observation_window_days": judgement.get("observation_window_days"),
                    "baseline_analytics_snapshot_key": analytics["snapshot_key"],
                })
                intent = json.loads(pending_effect["intent_path"].read_text(encoding="utf-8"))
                _atomic_write(pending_effect["intent_path"], {
                    **intent, "status": "confirmed", "confirmed_at_epoch": int(time.time()),
                    "effect_ledger_appended": appended,
                })
                accepted_effect = int(appended and not pending_effect["recovered"])
                accepted_readback = 1
            outcome = _close_outcome(
                args.state_dir, analytics,
                getattr(args, "reply_transcripts", DEFAULT_REPLY_TRANSCRIPTS),
                getattr(args, "scorecard", DEFAULT_SCORECARD), int(time.time()),
            )
            if next_hypothesis is not None:
                _append_key_once(
                    args.state_dir / "prepared-hypotheses.jsonl", "hypothesis_key", next_hypothesis,
                )
            row = _receipt(
                pass_id,
                status="completed",
                reason=("public_accepted" if pending_effect is not None
                        else "judgement_ready" if judgement["decision"] == "change"
                        else str(judgement["no_op_reason"])),
                decision=judgement["decision"],
                actionable=int(judgement["decision"] == "change"),
                effect=accepted_effect,
                readback=accepted_readback,
                official_services_read=observed,
                offer_contracts_appended=contract_count,
                listing_contracts_appended=listing_contract_count,
                listing_contracts_active=len(listing_contracts),
                listing_contracts_total=listing_contract_total,
                competitor_evidence_count=len(competitor_manifest["sources"]),
                inventory_content_sha256=inventory.get("content_sha256"),
                judgement_path=str(judgement_path),
                service_id=judgement.get("service_id"),
                changed_field=judgement.get("changed_field"),
                experiment_key=judgement.get("experiment_key"),
                public_after_path=(str(pending_effect["public_after_path"]) if pending_effect else None),
                recovered_effect=bool(pending_effect and pending_effect["recovered"]),
                analytics_snapshot_key=analytics["snapshot_key"],
                catalog_analytics=analytics.get("catalog_metrics"),
                funnel=funnel,
                portfolio=portfolio,
                inquiry_context=inquiry_context,
                new_listing_draft=draft_result,
                outcome=outcome,
                next_hypothesis=next_hypothesis,
                proposal_agent=proposal_agent,
                mutation_renders=[{
                    "changed_field": render["contract"]["changed_field"],
                    "service_id": render["contract"]["service_id"],
                    "contract_sha256": render["contract"]["contract_sha256"],
                    "delta": render["delta"], "published": False, "evidence_path": str(path),
                } for render, path in (
                    (image_render, image_render_path),
                    (title_render, title_render_path), (body_render, body_render_path),
                    (package_render, package_render_path), (faq_render, faq_render_path),
                    (price_render, price_render_path),
                )] + ([{
                    "changed_field": generated_render["contract"]["changed_field"],
                    "service_id": generated_render["contract"]["service_id"],
                    "contract_sha256": generated_render["contract"]["contract_sha256"],
                    "delta": generated_render["delta"], "published": False,
                    "evidence_path": str(generated_render_path), "generated": True,
                }] if generated_render is not None else []),
                lease={
                    "task": task,
                    "context_id": lease.get("context_id"),
                    "target_id": lease.get("target_id"),
                    "generation": lease.get("generation"),
                    "released": True,
                },
            )
            row = _persist_receipt(args, output, row)
            return 0, row
        except (OSError, RuntimeError, TypeError, ValueError, subprocess.SubprocessError) as error:
            if lease is not None and not released:
                try:
                    release = _lease(args.lease_script, "release", task, lease)
                    released = release.get("released") == task
                except (OSError, RuntimeError, TypeError, ValueError, subprocess.SubprocessError):
                    pass
            row = _receipt(pass_id, status="failed", reason=str(error).strip() or type(error).__name__,
                           lease={"task": task, "released": released} if lease is not None else None)
            row = _persist_receipt(args, output, row)
            return 1, row
        finally:
            if lease is not None and not released:
                try:
                    _lease(args.lease_script, "release", task, lease)
                except (OSError, RuntimeError, TypeError, ValueError, subprocess.SubprocessError):
                    pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--operator-brake", type=Path, default=Path(os.environ.get("GIG_OPERATOR_BRAKE_FILE", DEFAULT_BRAKE)))
    parser.add_argument("--lease-script", type=Path, default=DEFAULT_LEASE)
    parser.add_argument("--ensure-browser-script", type=Path, default=DEFAULT_ENSURE_BROWSER)
    parser.add_argument("--default-tab-script", type=Path, default=DEFAULT_TAB)
    parser.add_argument("--runner", type=Path, default=DEFAULT_RUNNER)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--proposal-schema", type=Path, default=DEFAULT_PROPOSAL_SCHEMA)
    parser.add_argument("--create-proposal-schema", type=Path, default=DEFAULT_CREATE_PROPOSAL_SCHEMA)
    parser.add_argument("--scorecard", type=Path, default=DEFAULT_SCORECARD)
    parser.add_argument("--image-contract", type=Path, default=DEFAULT_IMAGE_CONTRACT)
    parser.add_argument("--gallery-contract", type=Path, default=DEFAULT_GALLERY_CONTRACT)
    parser.add_argument("--title-mutation", type=Path, default=DEFAULT_TITLE_MUTATION)
    parser.add_argument("--body-mutation", type=Path, default=DEFAULT_BODY_MUTATION)
    parser.add_argument("--scope-mutation", type=Path, default=DEFAULT_SCOPE_MUTATION)
    parser.add_argument("--package-mutation", type=Path, default=DEFAULT_PACKAGE_MUTATION)
    parser.add_argument("--faq-mutation", type=Path, default=DEFAULT_FAQ_MUTATION)
    parser.add_argument("--price-mutation", type=Path, default=DEFAULT_PRICE_MUTATION)
    parser.add_argument("--listing-contract-dir", type=Path, default=DEFAULT_LISTING_CONTRACT_DIR)
    parser.add_argument(
        "--listing-contract-families", type=Path, default=DEFAULT_LISTING_CONTRACT_FAMILIES,
    )
    parser.add_argument("--new-listing-contract", type=Path, default=DEFAULT_NEW_LISTING_CONTRACT)
    parser.add_argument("--reply-transcripts", type=Path, default=DEFAULT_REPLY_TRANSCRIPTS)
    parser.add_argument("--applied", type=Path, default=DEFAULT_APPLIED)
    parser.add_argument("--earnings", type=Path, default=DEFAULT_EARNINGS)
    parser.add_argument("--projects-dir", type=Path, default=DEFAULT_PROJECTS)
    parser.add_argument(
        "--negotiate-context-acks", type=Path, default=DEFAULT_NEGOTIATE_CONTEXT_ACKS,
    )
    parser.add_argument("--negotiate-run-log", type=Path, default=DEFAULT_NEGOTIATE_RUN_LOG)
    parser.add_argument("--workdir", type=Path, default=Path.home())
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--capability-evidence", type=Path, action="append", default=list(DEFAULT_CAPABILITIES))
    parser.add_argument("--effect", action="store_true")
    parser.add_argument("--incremental", action="store_true")
    parser.add_argument("--auto-cadence", action="store_true")
    parser.add_argument("--full-interval-seconds", type=int, default=1800)
    parser.add_argument("--accounting-cutoff-epoch", type=int, default=0)
    parser.add_argument("--expected-catalog-sha256", default="")
    parser.add_argument("--pass-id")
    parser.add_argument("--telegram-database", type=Path, default=DEFAULT_TELEGRAM_DATABASE)
    parser.add_argument("--telegram-receipt-dir", type=Path, default=DEFAULT_TELEGRAM_RECEIPTS)
    parser.add_argument("--telegram-target", default=os.environ.get("GIG_REPORT_CHAT", ""))
    parser.add_argument("--openclaw", type=Path, default=Path("/opt/homebrew/bin/openclaw"))
    args = parser.parse_args()
    code, row = run_once(args)
    print(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
