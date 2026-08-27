#!/usr/bin/env python3
"""
library-structural-analyze.py — Convert raw Apify TikTok scrapes into
structured pattern-<family>.jsonl entries for the content factory library.

Bible (HARD RULE #15): scrape ONCE, generate FOREVER from this library.
Adrià: clone-don't-template. StudyTok Hermes: 1 viral → 100 variations.

Input:  ~/.openclaw/state/content-library/raw-<niche>.jsonl
Output: ~/.openclaw/state/content-library/pattern-<family>.jsonl

Each pattern entry:
{
  "source_url": "https://www.tiktok.com/...",
  "source_id": "<tiktok video id>",
  "scraped_at": "2026-05-29T03:30Z",
  "niche_tags": ["mental-health", "ja"],
  "hook": "first non-empty line",
  "structure": {
    "char_count": 248,
    "line_count": 5,
    "hashtag_count": 3,
    "emoji_count": 2,
    "has_cta": true,
    "type": "slideshow"|"video"|"long-caption"
  },
  "emotion": "anxious|empowered|sad|grateful|...",
  "observed": {
    "views": 31500000, "likes": 1200000, "shares": 80000, "comments": 12000,
    "saves": 50000
  },
  "music_id": "...",
  "author": "@xxx",
  "lastUsed": null,    # filled when a propose-*.sh picks this entry for posting
  "status": "active"   # "killed" if performance crashed in account-history
}

family mapping (niche → which cron families can pull from this pattern):
  mental-health-ja        → card-ja, 4.7-ja, iam-ja, mantra-ja, larry-ja
  mental-health-en        → card-en, 4.7-en, iam-en, larry-en
  lockscreen-widget       → widget-ja, widget-en
  affirmation-slideshow-ja → card-ja, 4.7-ja, iam-ja, mantra-ja, larry-ja
  monk-wisdom              → monk-en
  honne-relationship       → honne-ja
"""
import json, os, re, sys, time
from pathlib import Path

LIB = Path.home() / ".openclaw" / "state" / "content-library"

FAMILY_MAP = {
    "mental-health-ja":           ["card-ja", "4.7-ja", "iam-ja", "mantra-ja", "larry-ja"],
    "mental-health-en":           ["card-en", "4.7-en", "iam-en", "larry-en"],
    "lockscreen-widget":          ["widget-ja", "widget-en"],
    "affirmation-slideshow-ja":   ["card-ja", "4.7-ja", "iam-ja", "mantra-ja", "larry-ja"],
    "monk-wisdom":                ["monk-en"],
    "honne-relationship":         ["honne-ja"],
}

EMOJI = re.compile(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]")
CTA_HINTS = re.compile(r"(?:#anicca|アニッチャ|try (?:our|this) app|download|アプリ|今すぐ|保存版|comment .* below|fr |真似してみて)", re.I)
HASHTAG = re.compile(r"#[^\s#]+")
# crude emotion lexicon (jp+en common viral patterns)
EMOTION_LEX = {
    "anxious": ["不安","anxiety","worried","nervous","ストレス","stress","panic","パニック"],
    "sad":     ["寂しい","sad","lonely","cry","泣","heartbroken","失恋","depressed","depression"],
    "empowered": ["大丈夫","you got this","believe","信じて","強い","powerful","自分らしく","heal","回復","recovery","grow","成長"],
    "grateful": ["ありがとう","grateful","gratitude","blessed","祝福"],
    "anger":   ["怒","angry","upset","mad","ムカ"],
    "calm":    ["静","calm","peaceful","落ち着","relax","mindful","瞑想","meditation"],
}

def detect_emotion(text):
    t = text.lower()
    best = ("calm", 0)
    for emo, words in EMOTION_LEX.items():
        score = sum(1 for w in words if w.lower() in t)
        if score > best[1]:
            best = (emo, score)
    return best[0]

def detect_type(text):
    """slideshow caption tends to be long/multi-line+CTA, video caption tends short."""
    lines = [l for l in text.splitlines() if l.strip()]
    if len(lines) >= 4 and len(text) > 150:
        return "slideshow"
    if len(text) > 80:
        return "long-caption"
    return "video"

def hook_of(text):
    for line in text.splitlines():
        line = line.strip()
        # skip pure-hashtag lines, pure-emoji lines
        if not line: continue
        stripped = HASHTAG.sub("", line).strip()
        if not stripped: continue
        if EMOJI.sub("", stripped).strip() == "": continue
        return line[:200]
    return text[:80]

def parse_niche(niche, raw_path):
    out = []
    for line in open(raw_path):
        line = line.strip()
        if not line: continue
        try:
            it = json.loads(line)
        except: continue
        if it.get("isAd"): continue
        text = (it.get("text") or "").strip()
        if not text: continue
        views = it.get("playCount") or 0
        if views < 1000: continue
        hook = hook_of(text)
        if not hook: continue
        hashtags = HASHTAG.findall(text)
        emojis = EMOJI.findall(text)
        entry = {
            "source_url": it.get("webVideoUrl",""),
            "source_id":  it.get("id",""),
            "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "niche_tags": niche.split("-"),
            "hook": hook,
            "structure": {
                "char_count":    len(text),
                "line_count":    len([l for l in text.splitlines() if l.strip()]),
                "hashtag_count": len(hashtags),
                "emoji_count":   len(emojis),
                "has_cta":       bool(CTA_HINTS.search(text)),
                "type":          detect_type(text),
            },
            "emotion": detect_emotion(text),
            "observed": {
                "views":    views,
                "likes":    it.get("diggCount") or 0,
                "shares":   it.get("shareCount") or 0,
                "comments": it.get("commentCount") or 0,
                "saves":    it.get("collectCount") or 0,
            },
            "music_id": (it.get("musicMeta") or {}).get("musicId",""),
            "author":   (it.get("authorMeta") or {}).get("name",""),
            "lastUsed": None,
            "status":   "active",
        }
        out.append(entry)
    return out

def main():
    LIB.mkdir(parents=True, exist_ok=True)
    # per family, accumulate entries
    fam_buckets = {fam: [] for fams in FAMILY_MAP.values() for fam in fams}
    total = 0
    for niche, families in FAMILY_MAP.items():
        raw = LIB / f"raw-{niche}.jsonl"
        if not raw.exists():
            print(f"  ⚠️ {niche}: raw file missing — skip", file=sys.stderr); continue
        entries = parse_niche(niche, raw)
        for fam in families:
            fam_buckets[fam].extend(entries)
        total += len(entries)
        print(f"  {niche}: {len(entries)} entries → fams={families}")
    # write each pattern-<family>.jsonl (sort by views desc for quick winner pick)
    for fam, entries in fam_buckets.items():
        entries.sort(key=lambda e: -e["observed"]["views"])
        out = LIB / f"pattern-{fam}.jsonl"
        with open(out, "w") as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        print(f"  → pattern-{fam}.jsonl: {len(entries)} entries (top views: {entries[0]['observed']['views']:,} | hook: {entries[0]['hook'][:50]!r})" if entries else f"  → pattern-{fam}.jsonl: 0")
    print(f"\nTOTAL entries processed: {total}")

if __name__ == "__main__":
    main()
