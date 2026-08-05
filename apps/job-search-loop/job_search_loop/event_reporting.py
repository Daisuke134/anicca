from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from urllib.parse import urlsplit


KINDS = frozenset({
    "application", "recruiter_interest", "interview", "offer", "rejection",
    "operational_delay",
})
REQUIRED_KEYS = frozenset({
    "version", "event_id", "kind", "company", "title", "stage",
    "occurred_at", "next_action", "links",
})


def _validated(facts: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(facts, dict) or set(facts) != REQUIRED_KEYS:
        raise ValueError("event facts contract is invalid")
    if facts.get("version") != 1 or facts.get("kind") not in KINDS:
        raise ValueError("event facts kind/version is invalid")
    for key in ("event_id", "company", "title", "stage", "occurred_at", "next_action"):
        value = facts.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"event fact {key} is invalid")
        if re.search(r"(?:/Users/|~/\.local|file://)", value, re.IGNORECASE):
            raise ValueError("private filesystem path is forbidden")
    links = facts.get("links")
    if not isinstance(links, dict):
        raise ValueError("event links are invalid")
    for label, url in links.items():
        if not isinstance(label, str) or not label.strip() or not isinstance(url, str):
            raise ValueError("event link is invalid")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("event links must use HTTPS")
    return facts


def render_event_message(facts: dict[str, Any]) -> str:
    value = _validated(facts)
    headings = {
        "application": f"💼 {value['company']}への応募が完了しました！",
        "recruiter_interest": f"✨ {value['company']}の採用担当から返信が届きました。",
        "interview": f"🎉 {value['company']}の選考が前進しました！",
        "offer": f"🚀🎊 {value['company']}からオファーが届きました！",
        "rejection": f"{value['company']}は今回は次の選考へ進みませんでした。",
        "operational_delay": f"⚠️ {value['company']}の処理状況を確認しています。",
    }
    closings = {
        "application": "これから返信を追跡します。",
        "recruiter_interest": "内容を確認し、次の選考対応を進めます。",
        "interview": "これは大きな前進です。面接準備を進めます。",
        "offer": "条件を正確に確認し、承諾はあなたが決めるまで行いません。",
        "rejection": "事実を学習データに反映し、次の応募を改善して続けます。",
        "operational_delay": value["next_action"],
    }
    lines = [
        headings[value["kind"]], "",
        f"職種: {value['title']}",
        f"現在の段階: {value['stage']}",
        f"確認時刻: {value['occurred_at']}", "",
        closings[value["kind"]],
    ]
    for label, url in value["links"].items():
        lines.append(f"[{label}]({url})")
    message = "\n".join(lines)
    if len(message) > 4096:
        raise ValueError("event message exceeds Telegram limit")
    return message


def validate_event_message(
    facts: dict[str, Any], message: str
) -> dict[str, str]:
    value = _validated(facts)
    if not isinstance(message, str) or message != render_event_message(value):
        raise ValueError("Telegram event message fact or tone drift")
    facts_json = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return {
        "status": "valid",
        "event_id": value["event_id"],
        "kind": value["kind"],
        "facts_sha256": hashlib.sha256(facts_json.encode("utf-8")).hexdigest(),
        "message_sha256": hashlib.sha256(message.encode("utf-8")).hexdigest(),
    }
