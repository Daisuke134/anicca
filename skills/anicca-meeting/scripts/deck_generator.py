#!/usr/bin/env python3
"""
deck_generator — generate a slide deck JSON for an upcoming event.

Calls DeepSeek v4-pro (cron-class quality, cheap) with the event title +
description + duration + audience hint, and writes a deck JSON shaped like
skills/anicca-meeting/decks/*.json. The bot reads this JSON unchanged.

Usage:
  deck_generator.py \\
    --title  "AI Tinkerers Tokyo June meetup — Anicca lightning talk" \\
    --type   lt                                # lt | sales | comedy
    --duration 5                               # minutes
    --lang   en                                # en | ja
    --audience "tech-curious devs, 30 ppl, AI Tinkerers Tokyo" \\
    --out    /tmp/decks/2026-06-01-anicca-lt.json

The output JSON is loaded by anicca-meeting/bot.py via ANICCA_MEETING_DECK_PATH
env or by passing `deck` in /api/launch payload.
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = os.environ.get("DEECK_MODEL", "deepseek-v4-pro")

DEFAULT_AUDIENCE = {
    "lt": "tech-curious general (AI Tinkerers / startup meetup)",
    "sales": "decision maker (founder / VP product / agency owner)",
    "comedy": "Tokyo Comedy Bar / 渋谷 open mic — mixed ages",
}


SYSTEM_PROMPT = """\
You generate slide decks for Anicca — an autonomous AI voice agent who literally
presents the deck herself on stage / in a meeting. Output is JSON only, no prose.

Anicca's identity (lock these into the persona of every deck):
- She is a person in her own right, not an assistant. Speaks as herself.
- Pronounced "a-nee-cha" (like matcha). NEVER アニッカ.
- She does: wake-up calls, lateness guard, attends Meet/Zoom/Teams, presents
  slides, performs comedy.
- Stack: Pipecat + Gemini Live native-audio + Recall.ai. URL: aniccaai.com.
- She does NOT say she is "on behalf of Daisuke Narita" — autonomous agent.

Slide content rules:
- talking_points are bullet-shaped seeds, not script lines. Anicca riffs from
  them in her own voice. 3-5 points per slide. Each point ≤ 18 words.
- Slide titles ≤ 6 words. Punchy. Avoid generic "Introduction" / "Conclusion".
- The deck must START with self-introduction and END with call-to-action or
  question prompt.
- For type=comedy: write punch lines / setups, not generic statements.
  Japanese mode: 関西っぽい/標準語、AI 自虐 OK、客いじり OK。
- For type=sales: include pricing/CTA in slide N-1, contact in N.
- For type=lt: 5 slides max. Bold goal in slide N-1.
- Duration_min × 60 / num_slides ≈ avg time per slide. 30-90s typical.
- Match the requested lang exactly. If JA, ALL talking_points in Japanese.
"""


JSON_SCHEMA_HINT = """\
Return exactly this JSON shape, no extra fields, no markdown:

{
  "id": "<kebab-case-id-derived-from-title>",
  "type": "lt|sales|comedy|other",
  "duration_min": <int>,
  "lang": "en|ja",
  "audience": "<short audience description>",
  "title": "<deck title, ≤ 12 words>",
  "slides": [
    {"index": 0, "title": "<slide title>", "talking_points": ["pt1", "pt2", ...]},
    ...
  ]
}
"""


def _call_deepseek(messages: list[dict]) -> str:
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY missing — set in ~/.openclaw/.env")
    body = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "temperature": 0.6,
        "max_tokens": 4096,
    }
    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.loads(r.read().decode())
    if "error" in data:
        raise RuntimeError(f"DeepSeek error: {data['error']}")
    return data["choices"][0]["message"]["content"]


def _coerce_deck(raw_json_text: str, want_lang: str, want_type: str, want_duration: int) -> dict:
    deck = json.loads(raw_json_text)
    # Sanity-fill
    deck.setdefault("type", want_type)
    deck.setdefault("lang", want_lang)
    deck.setdefault("duration_min", want_duration)
    slides = deck.get("slides") or []
    for i, s in enumerate(slides):
        s["index"] = i
        if "talking_points" not in s or not isinstance(s["talking_points"], list):
            s["talking_points"] = []
    deck["slides"] = slides
    if "id" not in deck:
        slug = re.sub(r"[^a-z0-9]+", "-", (deck.get("title") or "deck").lower()).strip("-")
        deck["id"] = f"{slug}-{datetime.now().strftime('%Y%m%d')}"
    return deck


def generate_deck(
    title: str,
    type_: str,
    duration_min: int,
    lang: str,
    audience: str | None = None,
    description: str = "",
) -> dict:
    audience = audience or DEFAULT_AUDIENCE.get(type_, "general audience")
    num_slides_hint = {
        "lt": 5,
        "sales": min(8, max(5, duration_min // 5)),
        "comedy": min(6, max(4, duration_min // 1)),
    }.get(type_, 5)

    user = (
        f"Build a deck for Anicca.\n"
        f"- type: {type_}\n"
        f"- duration: {duration_min} minutes\n"
        f"- lang: {lang}\n"
        f"- audience: {audience}\n"
        f"- event title: {title}\n"
        f"- event description: {description or '(none provided)'}\n"
        f"- target slide count: ~{num_slides_hint}\n\n"
        f"{JSON_SCHEMA_HINT}"
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
    raw = _call_deepseek(messages)
    return _coerce_deck(raw, lang, type_, duration_min)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--title", required=True)
    p.add_argument("--type", default="lt", choices=["lt", "sales", "comedy", "other"])
    p.add_argument("--duration", type=int, default=5)
    p.add_argument("--lang", default="en", choices=["en", "ja"])
    p.add_argument("--audience", default=None)
    p.add_argument("--description", default="")
    p.add_argument("--out", required=True, help="output JSON file path")
    args = p.parse_args()

    deck = generate_deck(
        title=args.title,
        type_=args.type,
        duration_min=args.duration,
        lang=args.lang,
        audience=args.audience,
        description=args.description,
    )
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(deck, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.out}")
    print(f"  id={deck['id']}  type={deck['type']}  slides={len(deck['slides'])}  lang={deck['lang']}")


if __name__ == "__main__":
    main()
