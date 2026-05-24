#!/usr/bin/env python3
"""Triage Gmail threads → REPLY / SKIP / FOLLOWUP."""
from __future__ import annotations
import json, re, sys
from pathlib import Path

SKIP_FROM = re.compile(
    r"(noreply|no-reply|automated|notification|@mid-tenshoku|@m-newsletter|@{{profile.lateness.stakeholders.channel}}\.asahi|"
    r"newsletter|@quora\.com|@{{profile.lateness.stakeholders.channel}}\.notion|invitations@linkedin|notify@linkedin|"
    r"@mailnews|info-unipa@ad\.naist\.jp|@stripe\.com|@stripe-events|@epoc|@company|debit\.bk\.mufg\.jp|"
    r"@square\.com|@printful\.com|Postiz|forms-receipts-noreply|Indeed|"
    r"webhook|status@|alert@|@hubspot|skyticket|camp-fire\.jp)",
    re.IGNORECASE,
)
SELF_FROM = re.compile(r"(your-email-user@gmail\.com|daisuke <username>|成田\s*大祐|anicca from anicca|aniccabuddha@substack\.com)", re.IGNORECASE)
SKIP_SUBJECT = re.compile(
    r"(\[自動配信\]|\[\s*Automated\s*\]|プロモーション|セール|割引|"
    r"unsubscribe|opt-out|お得|ご請求|請求|明細|レシート|receipt|invoice|"
    r"ご利用のお知らせ|利用のお知らせ|ご利用明細|お支払いのお知らせ|引落|"
    r"newsletter|digest|trending|Top stories|【.{1,20}〆切間近|"
    r"campaign|クラウドファンディング|支援総額|残り日数|開校式|開校後|"
    r"応募リクエスト|オススメ求人|おすすめ求人|求人速報|求人特集|転職体験レポート|"
    r"job promotion|job alert|career alert|new jobs|new opportunities|quick application|background could be a match|please submit a quick application|"
    r"appointment is confirmed|appointment is cancel|"
    r"video is ready|is ready to be published|published|posted|scheduled|"
    r"verification code|authentication code|login code|sign[- ]?in code|"
    r"draft saved|webhook|build (succeeded|failed)|deploy (succeeded|failed)|"
    r"new follower|liked your|commented on|mentioned you|reacted to|reply on|"
    r"Out of office|休暇のお知らせ|不在|Auto-Reply|Automatic reply|"
    r"voic{{profile.lateness.stakeholders.channel}}|voice message|transcript|transcription|留守電|留守番電話|自動転送|"
    r"カレンダーに登録|招待状|invitation|Calendar|RSVP|"
    r"トラッキング|tracking|shipped|delivered|配送|出荷)",
    re.IGNORECASE,
)

REPLY_KEYWORDS = [
    # 出演交渉
    "GRIP", "オープンマイク", "open mic", "openmic", "ライブ出演", "出演",
    "ネタ尺", "ピン", "コンビ", "オーディション", "賞レース",
    # 物件 / cafe
    "kashispace", "賃貸", "物件", "サブリース", "ゴーストキッチン", "ghost kitchen",
    "uber eats", "uber merchant", "menulog",
    # tomb / 寺院
    "お墓", "tomb", "墓地", "供養", "寺院", "memorial", "Andon Labs",
    # business / admin inbound
    "ご相談", "お問合せ", "問い合わせ", "見積", "quote", "interview",
    "meeting", "zoom", "call", "申請", "締切", "deadline", "application",
]

REPLY_PATTERN = re.compile("|".join(re.escape(k) for k in REPLY_KEYWORDS), re.IGNORECASE)
NEWSLETTER_LIKE = re.compile(
    r"(substack|beehiiv|customer\.io|mailchimp|luma-mail|news|newsletter|digest|roundup|weekly|top ai demos|update|round up|event publish|web weekly drop)",
    re.IGNORECASE,
)
DIRECT_ASK_HINT = re.compile(
    r"(ご相談|お問合せ|お問い合わせ|reply|re:|could we|can we|would you|are you available|please let me know|available to talk|schedule|日程|候補日時|一度お話)",
    re.IGNORECASE,
)


def load_skip_patterns(path: Path):
    if not path.exists():
        return [], []
    d = json.loads(path.read_text())
    fr = [re.compile(p, re.IGNORECASE) for p in d.get("skip_from", [])]
    su = [re.compile(p, re.IGNORECASE) for p in d.get("skip_subject", [])]
    return fr, su


def classify(thread: dict, extra_from: list, extra_subject: list) -> str:
    """Returns REPLY / SKIP / FOLLOWUP."""
    sender = (thread.get("from") or "").lower()
    subject = thread.get("subject") or ""

    if SELF_FROM.search(sender):
        return "SKIP"

    # Hard skip via static rules
    if SKIP_FROM.search(sender):
        return "SKIP"
    if SKIP_SUBJECT.search(subject):
        return "SKIP"
    if re.search(r"(voic{{profile.lateness.stakeholders.channel}}|voice message|transcript|transcription|留守電|留守番電話|自動転送)", (subject + " " + (thread.get("body") or ""))[:2000], re.IGNORECASE):
        return "SKIP"
    for r in extra_from:
        if r.search(sender):
            return "SKIP"
    for r in extra_subject:
        if r.search(subject):
            return "SKIP"

    # Already replied by us in this thread?
    if thread.get("we_replied"):
        return "FOLLOWUP"

    # Inbound business signal (strict — only if positive match)
    snippet = thread.get("snippet") or ""
    body = thread.get("body") or ""
    text = f"{subject} {snippet} {body[:1500]}"
    if NEWSLETTER_LIKE.search(sender) or NEWSLETTER_LIKE.search(text):
        if not DIRECT_ASK_HINT.search(text):
            return "SKIP"
    if DIRECT_ASK_HINT.search(text) or REPLY_PATTERN.search(subject) or REPLY_PATTERN.search(snippet) or REPLY_PATTERN.search(body[:1500]):
        return "REPLY"

    # No positive signal → SKIP (conservative default)
    return "SKIP"


def main():
    in_path = Path(sys.argv[1])
    skip_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    out_path = Path(sys.argv[3]) if len(sys.argv) > 3 else None

    extra_from, extra_subject = ([], [])
    if skip_path and skip_path.exists():
        extra_from, extra_subject = load_skip_patterns(skip_path)

    threads = json.loads(in_path.read_text())
    out = []
    for t in threads:
        verdict = classify(t, extra_from, extra_subject)
        t["triage"] = verdict
        out.append(t)
    if out_path:
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    counts = {}
    for t in out:
        counts[t["triage"]] = counts.get(t["triage"], 0) + 1
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
