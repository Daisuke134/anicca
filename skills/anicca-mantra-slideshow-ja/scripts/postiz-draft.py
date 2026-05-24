#!/usr/bin/env python3
"""Upload slide PNGs to Postiz CDN + POST TikTok @anicca.jpx draft.
Usage: postiz-draft.py <run_dir>
Reads run_dir/slides/*.png + run_dir/picks.json
Writes run_dir/caption.txt + run_dir/postiz-receipt.json + Slack message
Final stdout: ✅ slideshow drafted: <slug> | postiz=<id> | slides=<n> | slack ts=<ts>
"""
import os, sys, json, urllib.request, urllib.error, datetime, subprocess, re
from pathlib import Path

if len(sys.argv) < 2:
    print("usage: postiz-draft.py <run_dir>", file=sys.stderr); sys.exit(1)
RUN_DIR = Path(sys.argv[1])
SKILL_DIR = Path(__file__).resolve().parent.parent
SLUG = SKILL_DIR.name
LANG = "en" if "-en" in SLUG else "ja"

POSTIZ_KEY = os.environ["POSTIZ_API_KEY"]
# === Fixed TikTok account (Dais 2026-05-14 — anicca.jpx 制限超過のため固定振り分け) ===
TIKTOK_INT = 'cmp9sdev5012voh0y58qs45xc'  # mantra JA slideshow TikTok (canonical 2026-05-19)
# === Fixed Instagram account (canonical 2026-05-20 — Dais final) ===
IG_INT = 'cmn8ycvtn02djqx0ytuisn9mw'  # iam/mantra/4.7 JA slideshow Instagram (canonical)
SLACK_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CH = os.environ["SLACK_CHANNEL_ID"]

HASHTAGS_EN = "#affirmations #lawofattraction #positiveaffirmations #manifestation #manifest #positivity #dailyaffirmations #manifesting #affirmation #mindfulness #loa #positivevibes #meditation #spirituality #abundance #inspiration #selfcare #selflove #spiritual #affirmationsoftheday #affirmationoftheday #loveyourself #positivethinking #positivemindset #life #inspirational #goodvibes #positivethoughts"
HASHTAGS_JA = "#アファメーション #引き寄せ #潜在意識 #マインドフルネス #自己肯定感 #ポジティブ #affirmations #lawofattraction #positiveaffirmations #manifestation #positivity #dailyaffirmations #manifesting #mindfulness #loa #positivevibes #meditation #spirituality #abundance #selfcare #selflove #affirmationsoftheday #loveyourself #positivethinking #life"
HEADER_EN = "Repeat with me:"
HEADER_JA = "繰り返してね。"
EMOJI = "🌷" if LANG == "en" else "🌸"

def upload(p: Path):
    out = subprocess.run(["postiz","upload",str(p)], capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(f"postiz upload failed: {out.stderr}")
    m = re.search(r"\{[\s\S]+?\}", out.stdout)
    if not m: raise RuntimeError(f"no JSON: {out.stdout[:300]}")
    j = json.loads(m.group(0))
    return {"id": j["id"], "path": j["path"]}

def slack_post(text, blocks):
    payload = {"channel": SLACK_CH, "text": text, "blocks": blocks}
    req = urllib.request.Request("https://slack.com/api/chat.postMessage", method="POST",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type":"application/json; charset=utf-8"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def main():
    slides = sorted((RUN_DIR / "slides").glob("slide_*.png"))
    if not slides:
        raise RuntimeError("no slides found")

    print(f"[1/2] uploading {len(slides)} slide(s)...")
    images = []
    for s in slides:
        u = upload(s)
        images.append(u)
        print(f"  ✓ {s.name} → {u['path']}")

    # Caption
    picks = json.loads((RUN_DIR / "picks.json").read_text())
    if isinstance(picks, dict) and "picks" in picks:
        picks_list = picks["picks"]
    else:
        picks_list = picks
    first = picks_list[0]["text"]
    header = HEADER_EN if LANG == "en" else HEADER_JA
    hashtags = HASHTAGS_EN if LANG == "en" else HASHTAGS_JA
    # Template A: caption = header + emoji + hashtags
    # Template B/C: caption = first line + emoji + hashtags
    if SLUG.endswith("-photo-en") or SLUG.endswith("-photo-ja"):
        caption = f"{header} {EMOJI} {hashtags}"
    else:
        caption = f"{first} {EMOJI} {hashtags}"
    (RUN_DIR / "caption.txt").write_text(caption, encoding="utf-8")

    print(f"[2/2] POST /public/v1/posts (TikTok + IG draft, SELF_ONLY + UPLOAD)...")
    posts_list = [{
        "integration": {"id": TIKTOK_INT},
        "value": [{"content": caption, "image": images}],
        "settings": {"__type":"tiktok","title":"","privacy_level":"SELF_ONLY","content_posting_method":"UPLOAD","duet":False,"stitch":False,"comment":True,"autoAddMusic":"no","brand_content_toggle":False,"brand_organic_toggle":False,"video_made_with_ai":True}
    }]
    if IG_INT:
        posts_list.append({
            "integration": {"id": IG_INT},
            "value": [{"content": caption, "image": [{"id": img["id"], "path": img["path"]} for img in images]}],
            "settings": {"__type": "instagram-standalone", "post_type": "post", "collaborators": [], "thumbnail": None},
        })
    payload = {
        "type": "now",
        "date": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "shortLink": False, "tags": [],
        "posts": posts_list,
    }
    req = urllib.request.Request("https://api.postiz.com/public/v1/posts", method="POST",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": POSTIZ_KEY, "Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            resp = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"Postiz HTTP {e.code}: {body[:500]}")
    post_id = resp[0]["postId"] if isinstance(resp, list) and resp else (resp or {}).get("postId","?")

    receipt = {
        "skill_slug": SLUG, "postiz_post_id": post_id, "integration_id": TIKTOK_INT,
        "mode":"drafts","privacy_level":"SELF_ONLY","content_posting_method":"UPLOAD",
        "caption": caption, "slide_count": len(slides), "images": images,
        "first_line": first,
        "published_at_utc": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "next_step":"Open TikTok app → Inbox/Drafts → review → tap Post",
    }
    (RUN_DIR / "postiz-receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2))

    blocks = [
        {"type":"header","text":{"type":"plain_text","text":f"📌 {SLUG} — daily draft"}},
        {"type":"section","text":{"type":"mrkdwn","text":f"*Postiz:* `{post_id}`\n*Slides:* {len(slides)}\n*Account:* @anicca.jpx TikTok DRAFT\n*First line:* {first}"}},
        {"type":"section","text":{"type":"mrkdwn","text":f"*Slide URL:* {images[0]['path']}"}},
    ]
    s = slack_post(f"{SLUG}: postiz={post_id}", blocks)
    ts = s.get("ts","")
    print(f"✅ slideshow drafted: {SLUG} | postiz={post_id} | slides={len(slides)} | slack ts={ts}")

if __name__ == "__main__":
    main()
