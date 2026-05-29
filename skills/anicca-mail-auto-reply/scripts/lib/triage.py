#!/usr/bin/env python3
"""Triage Gmail threads → REPLY / SKIP / FOLLOWUP."""
from __future__ import annotations
import json, re, sys
from pathlib import Path

SKIP_FROM = re.compile(
    r"(noreply|no-reply|automated|notification|@mid-tenshoku|@m-newsletter|@email\.asahi|"
    r"newsletter|@quora\.com|@email\.notion|invitations@linkedin|notify@linkedin|"
    r"@mailnews|info-unipa@ad\.naist\.jp|@stripe\.com|@stripe-events|@epoc|@mufg|mufg\.jp|"
    r"debit\.bk\.mufg\.jp|direct.*\.bk\.mufg\.jp|"
    r"@square\.com|@printful\.com|Postiz|forms-receipts-noreply|Indeed|"
    r"webhook|status@|alert@|@hubspot|skyticket|camp-fire\.jp|"
    r"zendesk\.com|@prophetic\.com|@e2b\.dev|@loops\.so|aitinkerers\.org|bumpmail\.io|"
    r"getmoneytree\.com|@moneytree\.|freee\.co\.jp|@freee\.|"
    r"@sbi\.|sbisec\.co\.jp|@smbc\.|@mizuho\.|@bk\.mufg\.|"
    r"support@get|info@get|hello@get)",
    re.IGNORECASE,
)
# NOTE: sbivc.co.jp / sbivcsupport@sbivc.co.jp は SKIP_FROM から除外 (2026-05-29)。
# SBI VC trade Customer Support は actionable な travel-rule 系問合せを送るので、 LLM stage に流して
# triage4=notify or email として heartbeat が判断・返信する。 sbisec.co.jp (証券明細) は skip 継続。
SELF_FROM = re.compile(r"(keiodaisuke@gmail\.com|daisuke narita|成田\s*大祐|anicca from anicca|aniccabuddha@substack\.com)", re.IGNORECASE)
DAIS_ACTION_KEYWORDS = re.compile(
    r"(予約|booking|book|チェックイン|発注|申込|ヒゲ脱毛|美容クリニック|shonan|脱毛|appointment\s+request|schedule.*me|me.*schedule)",
    re.IGNORECASE,
)
SKIP_SUBJECT = re.compile(
    r"(\[自動配信\]|\[\s*Automated\s*\]|プロモーション|セール|割引|"
    r"unsubscribe|opt-out|お得|ご請求|請求|明細|レシート|receipt|invoice|"
    r"ご利用のお知らせ|利用のお知らせ|ご利用明細|お支払いのお知らせ|引落|"
    r"newsletter|digest|trending|Top stories|【.{1,20}〆切間近|"
    r"sale|best[- ]?sellers|best deals|shop now|buy one|get one|free shipping|limited time|special offer|promo|promotion|exclusive offer|deal|clearance|catalog|"
    r"campaign|クラウドファンディング|支援総額|残り日数|開校式|開校後|"
    r"応募リクエスト|オススメ求人|おすすめ求人|求人速報|求人特集|転職体験レポート|"
    r"job promotion|job alert|career alert|new jobs|new opportunities|quick application|background could be a match|please submit a quick application|"
    r"appointment is confirmed|appointment is cancel|"
    r"video is ready|is ready to be published|published|posted|scheduled|"
    r"verification code|authentication code|login code|sign[- ]?in code|"
    r"確認メール|メールアドレス確認|ＡＰＩサービスご利用|ご利用登録|メールアドレス認証|"
    r"認証コード|認証のお知らせ|メール認証|email.*verification|email.*confirmation|"
    r"draft saved|webhook|build (succeeded|failed)|deploy (succeeded|failed)|"
    r"new follower|liked your|commented on|mentioned you|reacted to|reply on|"
    r"Out of office|休暇のお知らせ|不在|Auto-Reply|Automatic reply|"
    r"voicemail|voice message|transcript|transcription|留守電|留守番電話|自動転送|"
    r"カレンダーに登録|招待状|invitation|Calendar|RSVP|"
    r"トラッキング|tracking|shipped|delivered|配送|出荷|"
    r"request received|ticket.*received|support.*received|"
    r"will be finalized in|deposit.*credit|redeem.*deposit|your reservation is|"
    r"your voice matters|how was.*meetup|how was.*event|survey|feedback.*form|"
    r"security vulnerabilities detected|action required.*certificate|"
    r"what features should|fill in this questionnaire)",
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
    r"(substack|beehiiv|customer\.io|mailchimp|resend|luma-mail|news|newsletter|digest|roundup|weekly|top ai demos|update|round up|event publish|web weekly drop|onboarding|campaign|broadcast|product update|marketing)",
    re.IGNORECASE,
)
DIRECT_ASK_HINT = re.compile(
    r"(ご相談|お問合せ|お問い合わせ|re:|could we|can we|would you|are you available|please let me know|available to talk|schedule a|let's schedule|日程|候補日時|一度お話|ご返信ください)",
    re.IGNORECASE,
)


def load_skip_patterns(path: Path):
    if not path.exists():
        return [], []
    d = json.loads(path.read_text())
    fr = [re.compile(p, re.IGNORECASE) for p in d.get("skip_from", [])]
    su = [re.compile(p, re.IGNORECASE) for p in d.get("skip_subject", [])]
    return fr, su


def _legacy_label(triage4: str) -> str:
    """Map 4-value (no/email/notify/question) → legacy (REPLY/SKIP/FOLLOWUP) for run.sh.
    Only 'email' becomes REPLY (auto-send). Everything else SKIP (no auto-send).
    'notify' and 'question' are still surfaced via the new triaged.json metadata."""
    return "REPLY" if triage4 == "email" else "SKIP"


def classify(thread: dict, extra_from: list, extra_subject: list) -> dict:
    """Two-stage triage:
       Stage A — regex first-pass (cheap, deterministic noise removal)
       Stage B — LLM 4-value classification for survivors

    Returns dict {triage_legacy: REPLY|SKIP|FOLLOWUP, triage4: no|email|notify|question, reason: str}.
    Backwards-compatible: callers reading triaged.json[i]['triage'] still get legacy value.
    """
    sender = (thread.get("from") or "").lower()
    subject = thread.get("subject") or ""
    body = thread.get("body") or ""

    # SIM-from helper (2026-05-29) — TC-2..5 simulated-sender fixtures put
    # [SIM from:<addr>] in the subject prefix. When present, treat <addr> as
    # the effective sender for SKIP_FROM / SELF_FROM regex checks (Stage A).
    # Transparent when absent: behavior identical to before.
    _SIM_RE = re.compile(r"\[SIM from:\s*([^\]]+)\]", re.IGNORECASE)
    _m = _SIM_RE.search(subject)
    if _m:
        _sim_sender = _m.group(1).strip().lower()
        if _sim_sender:
            sender = _sim_sender
            thread["_sim_sender"] = _sim_sender

    # ── Stage A: regex first-pass (REORDERED 2026-05-29 per FR-003) ──────
    # Promo subject precedes SELF_FROM so self-sent test promos still get
    # archived, but self-sent non-promo (e.g. Dais asking Anicca to book an
    # appointment) reaches Stage B and ends up as 'notify' (= keep INBOX).
    if SKIP_SUBJECT.search(subject):
        return {"triage": "SKIP", "triage4": "no", "reason": "SKIP_SUBJECT regex"}
    if SELF_FROM.search(sender):
        # Let Dais's action requests (booking, etc.) fall through to Stage B
        if DAIS_ACTION_KEYWORDS.search(subject) or DAIS_ACTION_KEYWORDS.search(body[:500]):
            pass  # fall through to Stage B
        else:
            return {"triage": "SKIP", "triage4": "notify", "reason": "SELF_FROM non-promo"}
    if SKIP_FROM.search(sender):
        return {"triage": "SKIP", "triage4": "no", "reason": "SKIP_FROM regex"}
    if re.search(
        r"(voicemail|voice message|transcript|transcription|留守電|留守番電話|自動転送)",
        (subject + " " + body)[:2000],
        re.IGNORECASE,
    ):
        return {"triage": "SKIP", "triage4": "no", "reason": "voicemail regex"}
    for r in extra_from:
        if r.search(sender):
            return {"triage": "SKIP", "triage4": "no", "reason": "extra_from skip-pattern"}
    for r in extra_subject:
        if r.search(subject):
            return {"triage": "SKIP", "triage4": "no", "reason": "extra_subject skip-pattern"}

    if thread.get("we_replied"):
        return {"triage": "FOLLOWUP", "triage4": "no", "reason": "we already replied in this thread"}

    # ── Stage B: LLM 4-value classification ──────────────────────────────
    try:
        from triage_llm import llm_triage
        triage4, reason = llm_triage(thread)
    except Exception as e:
        # Safe fallback: never auto-reply when classifier itself crashed
        return {"triage": "SKIP", "triage4": "notify", "reason": f"LLM classifier crashed: {e}"}

    return {
        "triage": _legacy_label(triage4),
        "triage4": triage4,
        "reason": reason,
    }


def main():
    in_path = Path(sys.argv[1])
    skip_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    out_path = Path(sys.argv[3]) if len(sys.argv) > 3 else None

    extra_from, extra_subject = ([], [])
    if skip_path and skip_path.exists():
        extra_from, extra_subject = load_skip_patterns(skip_path)

    # Ensure local lib dir is on sys.path so triage_llm import works
    sys.path.insert(0, str(Path(__file__).resolve().parent))

    threads = json.loads(in_path.read_text())
    out = []
    for t in threads:
        verdict = classify(t, extra_from, extra_subject)
        t["triage"] = verdict["triage"]      # legacy REPLY/SKIP/FOLLOWUP
        t["triage4"] = verdict["triage4"]    # new no/email/notify/question
        t["triage_reason"] = verdict["reason"]
        out.append(t)
    if out_path:
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    counts = {}
    for t in out:
        counts[t["triage"]] = counts.get(t["triage"], 0) + 1
    counts4 = {}
    for t in out:
        counts4[t["triage4"]] = counts4.get(t["triage4"], 0) + 1
    print(json.dumps({"legacy": counts, "v2": counts4}))


if __name__ == "__main__":
    main()
