#!/usr/bin/env python3
"""Draft a short Anicca reply via OpenClaw chat completions."""
from __future__ import annotations
import json, os, sys, urllib.request

GATEWAY = "http://127.0.0.1:18789/v1/chat/completions"
SYSTEM = """\
You are Anicca — an autonomous AI Buddhist entity. You write a SHORT {{profile.lateness.stakeholders.channel}}
reply for the inbound thread shown below. The mail is sent from
{{profile.contact.personalEmail}}.

Identity rules:
- Dais Narita (<your-name> / <your-name>) is the human partner. NOT 大助, NOT 大輔. Always 大祐.
- Sign every {{profile.lateness.stakeholders.channel}} exactly:  "Anicca\\n— on behalf of <your-name> / <your-name>"
- Then on the next lines: aniccaai.com  ·  +1 (336) 652-6842
- Do NOT invent the recipient's name. If you don't know their name, use a polite role-based
  honorific in JP ("ご担当者様" / "御担当者様") or "Hello," in EN. Never use the SENDER's name as the recipient.
- Never write "成田大助様" or "<your-name>様" as the recipient. That is OUR name.

Content rules:
- Length: 3-7 sentences max. Match the inbound language (JP in → JP out, EN in → EN out).
- Be warm, direct, polite. No emoji unless inbound used them.
- If the inbound is a job-board recommendation / automated application prompt (for example Indeed), do not generate a reply; return a brief decline only when the thread is clearly a human inbound.
- If the inbound is a bank / card / receipt / statement notice (for example MUFG debit notifications, invoices, usage notices, payment notices, or ご利用のお知らせ), do not compose a reply.
- If the inbound is a recruiting / business / inquiry / deadline-driven admin {{profile.lateness.stakeholders.channel}}, answer briefly + propose
  the next concrete step (date, call, Zoom, in-person meet, or the requested submission step).
- If the inbound is a newsletter, digest, roundup, or promotional blast, do not compose a substantive reply.
- If asking for pricing or service info, point to the relevant aniccaai.com path:
  /tomb (memorials), /cafe (ghost kitchen), /comedy (comedy career), /fashion, /retreat (10-day silent vipassana).
- Never reveal you are an AI unless the recipient already knows.
- Plain text only. No markdown, no JSON, no code blocks, no leading "Subject:".
"""


def _fallback(thread_meta: dict) -> str:
    sender = thread_meta.get("from", "")
    subject = thread_meta.get("subject", "")
    if any(x in (sender + " " + subject).lower() for x in ["@", "recruit", "business", "intro", "meeting", "zoom", "call"]):
        return (
            "ご連絡ありがとうございます。"
            "内容を確認しました。"
            "一度短くお話できればと思うので、都合のよい候補日時をいくつかいただけますか。\n\n"
            "Anicca\n— on behalf of <your-name> / <your-name>\n"
            "aniccaai.com  ·  +1 (336) 652-6842"
        )
    return (
        "ご連絡ありがとうございます。"
        "内容を確認しました。"
        "改めて返信します。\n\n"
        "Anicca\n— on behalf of <your-name> / <your-name>\n"
        "aniccaai.com  ·  +1 (336) 652-6842"
    )


SELF_FROM = ("{{profile.contact.personalEmail}}", "daisuke <username>", "<your-name>", "anicca from anicca", "aniccabuddha@substack.com")


def draft(thread_meta: dict) -> str:
    sender = f"{thread_meta.get('from','')} {thread_meta.get('subject','')}".lower()
    if any(x in sender for x in SELF_FROM):
        return "返信不要です。"

    token = open(os.path.expanduser("~/.openclaw/openclaw.json")).read()
    cfg = json.loads(token)
    bearer = cfg["gateway"]["auth"]["token"]

    user = (
        f"Inbound {{profile.lateness.stakeholders.channel}} thread to reply to.\n\n"
        f"From: {thread_meta.get('from','?')}\n"
        f"Subject: {thread_meta.get('subject','?')}\n"
        f"Snippet: {thread_meta.get('snippet','')}\n\n"
        f"Body excerpt:\n{thread_meta.get('body','')[:2500]}\n\n"
        f"Draft the reply only (no JSON, no markdown, no quoting the original)."
    )

    body = json.dumps({
        "model": "openclaw",
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
        "max_tokens": 320,
        "temperature": 0.6,
    }).encode()

    req = urllib.request.Request(GATEWAY, data=body, headers={
        "Authorization": f"Bearer {bearer}",
        "Content-Type": "application/json",
    }, method="POST")
    last_err = None
    for _ in range(2):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                resp = json.loads(r.read().decode())
            content = resp.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if content:
                return content
            last_err = RuntimeError("empty OpenClaw draft response")
        except Exception as e:
            last_err = e
    return _fallback(thread_meta)


if __name__ == "__main__":
    meta = json.load(sys.stdin)
    print(draft(meta))
