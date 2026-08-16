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
DEFAULT_SCORECARD = GIG_DIR / "config" / "storefront-catalog-scorecard.json"
DEFAULT_REPLY_TRANSCRIPTS = Path.home() / "gig" / "reply-transcripts.jsonl"
DEFAULT_CAPABILITIES = (
    Path.home() / "gig" / "projects" / "5138597" / "state.json",
    Path.home() / "gig" / "projects" / "5138597" / "acceptance" / "v4-acceptance-evidence.json",
)
DEFAULT_TELEGRAM_DATABASE = Path.home() / "gig" / "telegram-outbox.sqlite3"
DEFAULT_TELEGRAM_RECEIPTS = Path.home() / "gig" / "telegram-delivery-receipts"
STATE_FILES = (
    "effects.jsonl", "experiments.jsonl", "offer-contracts.jsonl", "attribution-map.jsonl",
    "analytics.jsonl", "outcomes.jsonl", "prepared-hypotheses.jsonl", "listing-contracts.jsonl",
    "new-listing-drafts.jsonl",
)
TARGET_SERVICE_ID = "4330368"
DEFAULT_IMAGE_CONTRACT = GIG_DIR / "assets" / "storefront" / TARGET_SERVICE_ID / "image-contract.json"
DEFAULT_TITLE_MUTATION = GIG_DIR / "contracts" / "storefront" / "mutations" / "4308502-title-v1.json"
DEFAULT_BODY_MUTATION = GIG_DIR / "contracts" / "storefront" / "mutations" / "4308502-body-v1.json"
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
SELLER_FORM_EXPRESSION = r'''JSON.stringify((()=>{const form=document.forms[0];return{url:location.href,action:form?.action||null,method:form?.method||null,fields:form?[...form.elements].filter(e=>e.name).map(e=>({name:e.name,type:e.type||null,value:e.value||'',checked:!!e.checked})):[],select_options:form?Object.fromEntries([...form.elements].filter(e=>e.name&&e.tagName==='SELECT').map(e=>[e.name,[...e.options].map(o=>({value:o.value,label:(o.textContent||'').trim()}))])):{}}})())'''
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


def _report_message(row: dict) -> str:
    failed = int(row.get("status") == "failed")
    hypothesis = row.get("next_hypothesis") if isinstance(row.get("next_hypothesis"), dict) else {}
    contract_delta = int(row.get("listing_contracts_appended") or 0)
    catalog = row.get("catalog_analytics") if isinstance(row.get("catalog_analytics"), dict) else {}
    totals = catalog.get("totals") if isinstance(catalog.get("totals"), dict) else {}
    changes = catalog.get("changes") if isinstance(catalog.get("changes"), dict) else {}
    metric_unknown = (
        catalog.get("metric_unknown_services")
        if isinstance(catalog.get("metric_unknown_services"), dict) else {}
    )
    draft = row.get("new_listing_draft") if isinstance(row.get("new_listing_draft"), dict) else {}
    effect = max(int(row.get("effect") or 0), int(draft.get("effect") or 0),
                 int(draft.get("public_effect") or 0))
    next_action = (
        "失敗stageを自動修復して同じ境界から再開" if failed
        else "全出品adapterをversioned mutation contractへ共通化" if draft.get("status") == "already_public"
        else "公式readbackとoutcome ledgerを照合" if effect
        else f"{hypothesis.get('service_id')}/{hypothesis.get('field')}の実行harnessを継続"
        if hypothesis else "scorecard先頭の実行可能gapを選択"
    )
    lines = [
        "Codex::: 🏪 ココナラ Storefront hourly",
        f"✅ 公式出品 {int(row.get('official_services_read') or 0)}件 / 競合証拠 {int(row.get('competitor_evidence_count') or 0)}件",
        f"📊 actionable {int(row.get('actionable') or 0)} / effect {effect} / readback {int(row.get('readback') or 0)} / duplicate {int(row.get('duplicate') or 0)}",
        (f"📚 公開contract {int(row.get('listing_contracts_active') or 0)}件 / "
         f"version履歴 {int(row.get('listing_contracts_total') or 0)}件 / 今回追加 {contract_delta}件"),
        (f"📝 新規出品draft {draft.get('draft_service_id') or 'なし'} / "
         f"更新 {int(draft.get('effect') or 0)} / 照合 {int(draft.get('readback') or 0)} / "
         f"画像 {int(draft.get('image_count') or 0)} / 公開 {int(draft.get('public_effect') or 0)} / "
         f"状態 {draft.get('status') or 'なし'}"),
        (f"📈 直近30日: 閲覧 {int(totals.get('views') or 0)} / 販売 {int(totals.get('purchases') or 0)} / "
         f"お気に入り {int(totals.get('favorites') or 0)} | 前回比 閲覧 {int(changes.get('views') or 0):+d} / "
         f"販売 {int(changes.get('purchases') or 0):+d} / 現在値不明 {int(metric_unknown.get('views') or 0)}件 / "
         f"前回比不明 {int(catalog.get('change_unknown_services') or 0)}件"),
        f"🧪 次候補 {hypothesis.get('service_id') or 'なし'} / {hypothesis.get('field') or 'なし'} / 実行可能 {str(bool(hypothesis.get('executable'))).lower()}",
        f"🛡️ fence {hypothesis.get('guard_reason') or row.get('reason') or 'なし'}",
        f"🔧 次の一手: {next_action}",
    ]
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
    digest = hashlib.sha256(message.encode()).hexdigest()
    return f"gig:telegram:storefront-noop:v1:{digest}", "storefront_direct_noop", True


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


def _load_listing_contracts(
    root: Path, observed_contracts: list[dict], families_path: Path = DEFAULT_LISTING_CONTRACT_FAMILIES,
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
    return {**target, "catalog_metrics": {"services_observed": len(snapshots), "totals": totals,
                                           "changes": changes,
                                           "metric_unknown_services": metric_unknown_services,
                                           "change_unknown_services": unknown_changes}}


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
    contracts: list[dict], now: int,
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
    active = next((row for row in effects if row.get("status") == "accepted"
                   and row.get("effect") == 1 and row.get("experiment_key") not in terminal), None)
    completed = {(str(row.get("service_id")), str(row.get("changed_field")).lower())
                 for row in effects if row.get("status") == "accepted" and row.get("effect") == 1}
    versions = {str(row["service_id"]): row["service_version_sha256"] for row in contracts}
    candidate = next((row for row in backlog if isinstance(row, dict)
                      and str(row.get("service_id")) in versions
                      and (str(row.get("service_id")), str(row.get("field")).lower()) not in completed), None)
    if candidate is None:
        return None
    identity = json.dumps(candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "version": 1,
        "hypothesis_key": "storefront:hypothesis:v1:" + hashlib.sha256(identity.encode()).hexdigest(),
        "prepared_at_epoch": now,
        "service_id": str(candidate["service_id"]),
        "service_version_sha256": versions[str(candidate["service_id"])],
        "field": str(candidate["field"]),
        "before": candidate.get("before"),
        "success_metric": candidate.get("success_metric"),
        "reason": str(candidate.get("reason") or ""),
        "executable": active is None,
        "guard_reason": None if active is None else "active_experiment_measurement_open",
        "active_experiment_key": active.get("experiment_key") if active else None,
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


def _observe_own_page(ws_url: str, evidence_dir: Path, name: str = "own-candidate.json") -> dict:
    import listing_inventory

    url = f"https://coconala.com/services/{TARGET_SERVICE_ID}"
    observed = asyncio.run(listing_inventory._eval_json(
        ws_url,
        url,
        """(async () => {
          const closed = [...document.querySelectorAll(
            'a[aria-controls^="serviceContentsFaqAnswer"][aria-expanded="false"]'
          )];
          closed.forEach(control => control.click());
          if (closed.length) await new Promise(resolve => setTimeout(resolve, 500));
          const serviceImageIds = [...new Set([...document.querySelectorAll('.c-contentsImagesProduction img')]
            .map(image => (image.currentSrc || image.src || '').match(/service_images\\/original\\/([^/?]+)/)?.[1])
            .filter(Boolean))];
          return JSON.stringify({url:location.href,title:document.title,
            body:document.body ? document.body.innerText.slice(0,120000) : '',service_image_ids:serviceImageIds});
        })()""",
    ))
    body = str(observed.get("body") or "")
    image_ids = observed.get("service_image_ids")
    if (urlsplit(str(observed.get("url") or "")).path.rstrip("/") != f"/services/{TARGET_SERVICE_ID}" or not body.strip()
            or not isinstance(image_ids, list) or not all(isinstance(value, str) and value for value in image_ids)
            or len(set(image_ids)) != len(image_ids)):
        raise RuntimeError("own_candidate_readback_invalid")
    row = {
        "official": True,
        "observed": True,
        "service_id": TARGET_SERVICE_ID,
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
    if (child_env.get("ANICCA_BUDGET_REQUIRED") == "1"
            or child_env.get("ANICCA_PASS_TOKEN_BUDGET")
            or child_env.get("ANICCA_LOOP_DAILY_TOKEN_BUDGET")):
        child_env["ANICCA_BUDGET_SCOPE_ID"] = f"gig-storefront-direct:{evidence_dir.parent.name}"
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


def _experiment_key(service_id: str, field: str, proposed: str) -> str:
    digest = hashlib.sha256(proposed.strip().encode()).hexdigest()
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
    if (contract.get("service_id") != TARGET_SERVICE_ID or contract.get("changed_field") != "image"
            or contract.get("before_value") != {"service_image_ids": []}
            or contract.get("allowed_delta") != ["data[UploadedFile][n*][image_files]"]
            or contract.get("rollback_value") != {"service_image_ids": []}
            or contract.get("official_readback") != {"service_image_count": 1}
            or not isinstance(proposed, dict) or set(proposed) != {"asset_sha256", "asset_path"}
            or not re.fullmatch(r"[0-9a-f]{64}", str(proposed.get("asset_sha256") or ""))):
        raise RuntimeError("storefront_image_mutation_contract_invalid")


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


def _image_judgement(hypothesis: dict, contract: dict) -> dict:
    _validate_image_mutation_contract(contract)
    digest = str(contract["proposed_value"]["asset_sha256"])
    return {
        "decision": "change", "service_id": contract["service_id"], "changed_field": "image",
        "before_value": 0, "proposed_value": digest,
        "hypothesis": str(hypothesis["reason"]), "competitor_evidence_paths": [],
        "capability_evidence_paths": [], "success_metric": contract["success_metric"],
        "observation_window_days": contract["observation_window_days"], "no_op_reason": None,
        "experiment_key": _experiment_key(contract["service_id"], "image", digest), "uncertainty": [],
    }


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
            if now - accepted_at < 86400:
                return _guarded_noop(value, "account_effect_budget_24h")
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
        if (mutation_contract.get("contract_sha256") is None
                or mutation_contract.get("precondition_listing_version_sha256") != own_page.get("listing_version_sha256")
                or judgement.get("service_id") != mutation_contract.get("service_id") or judgement.get("before_value") != 0
                or own_page.get("service_image_count") != 0 or own_page.get("service_image_ids") != []):
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
    if (before.get("listing_version_sha256") != contract.get("precondition_listing_version_sha256")
            or before.get("service_image_ids") != contract.get("rollback_value", {}).get("service_image_ids")):
        raise RuntimeError("public_image_before_invalid")
    expected = contract.get("official_readback", {}).get("service_image_count")
    if after.get("service_image_count") != expected or len(after.get("service_image_ids") or []) != expected:
        raise RuntimeError("public_image_count_mismatch")
    if before.get("listing_version_sha256") == after.get("listing_version_sha256"):
        raise RuntimeError("public_image_version_unchanged")


def _validate_image_form_delta(before: dict, after: dict, contract: dict) -> None:
    _validate_image_mutation_contract(contract)
    url = f"https://coconala.com/mypage/services/{contract['service_id']}"
    if before.get("url") != url or after.get("url") != url:
        raise RuntimeError("seller_image_form_url_invalid")
    before_fields = [row for row in _form_base_fields(before) if not str(row.get("name") or "").startswith("data[UploadedFile]")]
    after_fields = [row for row in _form_base_fields(after) if not str(row.get("name") or "").startswith("data[UploadedFile]")]
    uploads = [row for row in after.get("fields") or [] if str(row.get("name") or "").startswith("data[UploadedFile]")]
    if before_fields != after_fields or any(
        str(row.get("name") or "").startswith("data[UploadedFile]") for row in before.get("fields") or []
    ):
        raise RuntimeError("seller_image_non_image_changed")
    if len(uploads) != 1 or not re.fullmatch(r"data\[UploadedFile]\[n\d+]\[image_files]", str(uploads[0].get("name") or "")):
        raise RuntimeError("seller_image_upload_field_invalid")


def _seller_snapshot(ws_url: str) -> dict:
    return _seller_snapshot_for(ws_url, TARGET_SERVICE_ID)


def _seller_snapshot_for(ws_url: str, service_id: str) -> dict:
    import listing_inventory

    return asyncio.run(listing_inventory._eval_json(
        ws_url, f"https://coconala.com/mypage/services/{service_id}", SELLER_FORM_EXPRESSION,
    ))


def _effect_intent_path(state_dir: Path, experiment_key: str) -> Path:
    digest = hashlib.sha256(experiment_key.encode()).hexdigest()
    return state_dir / "effect-intents" / f"{digest}.json"


def _pending_recovery(state_dir: Path, own_page: dict) -> dict | None:
    body = str(own_page.get("body") or "")
    for path in sorted((state_dir / "effect-intents").glob("*.json")):
        try:
            intent = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if intent.get("status") not in {"prepared", "observed"}:
            continue
        if intent.get("changed_field") == "image":
            image_ids = own_page.get("service_image_ids")
            if own_page.get("service_image_count") == 1 and isinstance(image_ids, list) and len(image_ids) == 1:
                return {**intent, "intent_path": str(path)}
            if own_page.get("service_image_count") == 0 and image_ids == []:
                continue
            raise RuntimeError("pending_image_effect_public_readback_invalid")
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
        click = json.loads(str(await evaluate(
            "JSON.stringify((()=>{const b=document.querySelector('.js_upload-select');"
            "if(!b)return {ok:false,reason:'image_add_missing'};b.click();return {ok:true}})())"
        ) or "{}"))
        if click.get("ok") is not True:
            raise RuntimeError(f"seller_image_add_failed:{click.get('reason')}")
        await asyncio.sleep(0.5)
        document = await listing_inventory._call(ws, "DOM.getDocument", {"depth": -1, "pierce": True}, cid); cid += 1
        queried = await listing_inventory._call(ws, "DOM.querySelector", {
            "nodeId": document["result"]["root"]["nodeId"], "selector": "input.js_upload-button",
        }, cid); cid += 1
        node_id = int(queried.get("result", {}).get("nodeId") or 0)
        if node_id <= 0:
            raise RuntimeError("seller_image_file_input_missing")
        await listing_inventory._call(ws, "DOM.setFileInputFiles", {
            "nodeId": node_id, "files": [str((GIG_DIR / contract["proposed_value"]["asset_path"]).resolve())],
        }, cid); cid += 1
        await asyncio.sleep(2)
        after = json.loads(str(await evaluate(SELLER_FORM_EXPRESSION) or "{}"))
        _validate_image_form_delta(before, after, contract)
        preview = json.loads(str(await evaluate(
            "JSON.stringify((()=>{const p=document.querySelector('.js_image-thumbnail[style*=\"blob:\"]');"
            "const s=document.querySelector('button.submitButton.js_button-edit[type=submit]');"
            "if(!p)return {ok:false,reason:'preview_missing'};if(!s)return {ok:false,reason:'submit_missing'};"
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
            "asset_path": str(contract["proposed_value"]["asset_path"]),
            "asset_sha256": contract["proposed_value"]["asset_sha256"], "mutation_contract": contract,
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
    pass_id = args.pass_id or f"storefront-direct-{time.time_ns()}-{os.getpid()}"
    minimum_epoch = int(time.time())
    args.state_dir.mkdir(parents=True, exist_ok=True)
    output = args.output or args.state_dir / "current.json"
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
            validated_contracts = [
                _service_contract(source, str(inventory["observed_at"])) for source in contract_sources
            ]
            capability_families, _ = _load_capability_families(
                getattr(args, "listing_contract_families", DEFAULT_LISTING_CONTRACT_FAMILIES),
            )
            presentation_snapshot = _seller_snapshot_for(ws_url, "4308502")
            title_render = _render_text_mutation(
                getattr(args, "title_mutation", DEFAULT_TITLE_MUTATION), validated_contracts,
                presentation_snapshot, capability_families,
            )
            body_render = _render_text_mutation(
                getattr(args, "body_mutation", DEFAULT_BODY_MUTATION), validated_contracts,
                presentation_snapshot, capability_families,
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
            package_render_path = inventory_path.parent / "mutation-render-package.json"
            faq_render_path = inventory_path.parent / "mutation-render-faq.json"
            price_render_path = inventory_path.parent / "mutation-render-price.json"
            _atomic_write(title_render_path, title_render)
            _atomic_write(body_render_path, body_render)
            _atomic_write(package_render_path, package_render)
            _atomic_write(faq_render_path, faq_render)
            _atomic_write(price_render_path, price_render)
            listing_contracts = _load_listing_contracts(
                getattr(args, "listing_contract_dir", DEFAULT_LISTING_CONTRACT_DIR), validated_contracts,
                getattr(args, "listing_contract_families", DEFAULT_LISTING_CONTRACT_FAMILIES),
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
            analytics = _collect_analytics(
                args.state_dir, inventory_path.parent, int(time.time()), sorted(inventory_ids),
                getattr(args, "default_tab_script", DEFAULT_TAB),
            )
            next_hypothesis = _prepare_next_hypothesis(
                getattr(args, "scorecard", DEFAULT_SCORECARD),
                args.state_dir / "effects.jsonl", args.state_dir / "outcomes.jsonl",
                validated_contracts, int(time.time()),
            )
            pending_effect = None
            recovery = _pending_recovery(args.state_dir, own_page)
            if recovery is not None:
                judgement = recovery.get("judgement")
                if not isinstance(judgement, dict):
                    raise RuntimeError("pending_effect_judgement_missing")
                if (recovery.get("service_id") != TARGET_SERVICE_ID
                        or recovery.get("changed_field") not in {"FAQ", "image"}
                        or recovery.get("experiment_key") != judgement.get("experiment_key")):
                    raise RuntimeError("pending_effect_identity_invalid")
                public_before = json.loads(Path(recovery["public_before_path"]).read_text(encoding="utf-8"))
                seller_before = json.loads(Path(recovery["seller_form_before_path"]).read_text(encoding="utf-8"))
                seller_after = _seller_snapshot(ws_url)
                if recovery["changed_field"] == "image":
                    mutation_contract = recovery.get("mutation_contract")
                    if not isinstance(mutation_contract, dict):
                        raise RuntimeError("pending_image_mutation_contract_missing")
                    _validate_public_image_acceptance(public_before, own_page, mutation_contract)
                else:
                    question, answer = str(recovery["question"]), str(recovery["answer"])
                    _validate_public_acceptance(public_before, own_page, question, answer)
                    _validate_form_delta(seller_before, seller_after, question, answer)
                seller_after_path = inventory_path.parent / "seller-form-recovered.json"
                _atomic_write(seller_after_path, seller_after)
                judgement_path = inventory_path.parent / "judgement-recovered.json"
                _atomic_write(judgement_path, judgement)
                intent_path = Path(recovery["intent_path"])
                durable_recovery = {key: value for key, value in recovery.items() if key != "intent_path"}
                _atomic_write(intent_path, {
                    **durable_recovery, "status": "observed",
                    "public_after_path": str(inventory_path.parent / "own-candidate.json"),
                    "seller_form_after_path": str(seller_after_path),
                    "observed_at_epoch": int(time.time()),
                })
                pending_effect = {
                    "intent_path": intent_path, "changed_field": recovery["changed_field"],
                    "public_before_path": Path(recovery["public_before_path"]),
                    "public_after_path": inventory_path.parent / "own-candidate.json",
                    "seller_form_before_path": Path(recovery["seller_form_before_path"]),
                    "seller_form_after_path": seller_after_path, "recovered": True,
                }
                if recovery["changed_field"] == "FAQ":
                    pending_effect.update({"question": question, "answer": answer})
            else:
                capability_paths = {str(Path(path).resolve()) for path in args.capability_evidence}
                mutation_contract = None
                if next_hypothesis is not None and not next_hypothesis["executable"]:
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
                    mutation_contract = _image_mutation_contract(
                        next_hypothesis, own_page, image_asset, capability_families,
                    )
                    _atomic_write(inventory_path.parent / "mutation-contract.json", mutation_contract)
                    judgement = _image_judgement(next_hypothesis, mutation_contract)
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
                    presend = _observe_own_page(ws_url, inventory_path.parent, presend_path.name)
                    _presend_guard(judgement, presend, mutation_contract)
                    if args.effect:
                        if judgement["changed_field"] == "image":
                            seller_before, _, intent_path = _execute_image_effect(
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
                        public_after = _observe_own_page(ws_url, inventory_path.parent, public_after_path.name)
                        seller_after = _seller_snapshot(ws_url)
                        if judgement["changed_field"] == "image":
                            _validate_public_image_acceptance(presend, public_after, mutation_contract)
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

            new_listing_contract = storefront_draft.load_contract(
                getattr(args, "new_listing_contract", DEFAULT_NEW_LISTING_CONTRACT)
            )
            candidate_id = new_listing_contract["draft_service_id"]
            candidate_public = candidate_id in inventory_ids
            duplicate_title = any(
                str(service.get("title") or "") == new_listing_contract["public_fields"]["expected_title"]
                and str(service.get("service_id") or "") != candidate_id
                for service in inventory["services"] if isinstance(service, dict)
            )
            draft_result = (storefront_draft.readback_published_draft(
                new_listing_contract,
                getattr(args, "default_tab_script", DEFAULT_TAB),
                inventory_path.parent,
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
                    "service_id": TARGET_SERVICE_ID, "changed_field": pending_effect["changed_field"],
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
                else:
                    effect_row.update({
                        "asset_sha256": judgement.get("proposed_value"),
                        "public_image_ids": json.loads(
                            Path(pending_effect["public_after_path"]).read_text(encoding="utf-8")
                        ).get("service_image_ids"),
                    })
                appended = _append_effect_once(args.state_dir / "effects.jsonl", effect_row)
                _append_effect_once(args.state_dir / "experiments.jsonl", {
                    "version": 1, "status": "accepted", "experiment_key": judgement["experiment_key"],
                    "service_id": TARGET_SERVICE_ID, "changed_field": pending_effect["changed_field"],
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
                new_listing_draft=draft_result,
                outcome=outcome,
                next_hypothesis=next_hypothesis,
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
                )],
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
            row = _receipt(pass_id, status="failed", reason=str(error),
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
    parser.add_argument("--scorecard", type=Path, default=DEFAULT_SCORECARD)
    parser.add_argument("--image-contract", type=Path, default=DEFAULT_IMAGE_CONTRACT)
    parser.add_argument("--title-mutation", type=Path, default=DEFAULT_TITLE_MUTATION)
    parser.add_argument("--body-mutation", type=Path, default=DEFAULT_BODY_MUTATION)
    parser.add_argument("--package-mutation", type=Path, default=DEFAULT_PACKAGE_MUTATION)
    parser.add_argument("--faq-mutation", type=Path, default=DEFAULT_FAQ_MUTATION)
    parser.add_argument("--price-mutation", type=Path, default=DEFAULT_PRICE_MUTATION)
    parser.add_argument("--listing-contract-dir", type=Path, default=DEFAULT_LISTING_CONTRACT_DIR)
    parser.add_argument(
        "--listing-contract-families", type=Path, default=DEFAULT_LISTING_CONTRACT_FAMILIES,
    )
    parser.add_argument("--new-listing-contract", type=Path, default=DEFAULT_NEW_LISTING_CONTRACT)
    parser.add_argument("--reply-transcripts", type=Path, default=DEFAULT_REPLY_TRANSCRIPTS)
    parser.add_argument("--workdir", type=Path, default=Path.home())
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--capability-evidence", type=Path, action="append", default=list(DEFAULT_CAPABILITIES))
    parser.add_argument("--effect", action="store_true")
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
