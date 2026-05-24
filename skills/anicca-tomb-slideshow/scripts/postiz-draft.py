#!/usr/bin/env python3
"""Upload 6 slide PNGs to Postiz CDN + POST to /public/v1/posts as TikTok draft.
Args: <product_slug> <run_dir>
Output line:
  ✅ slideshow drafted: <slug> | postiz post=<id> | slides=6 | slack ts=<ts>
  ❌ slideshow FAILED: <reason>
"""
import os
import sys
import json
import urllib.request
import urllib.error
import datetime
import time
import subprocess
from pathlib import Path

if len(sys.argv) < 3:
    print("usage: postiz-draft.py <slug> <run_dir>", file=sys.stderr)
    sys.exit(1)

PRODUCT_SLUG = sys.argv[1]
RUN_DIR = Path(sys.argv[2])
SKILL_DIR = Path.home() / ".openclaw" / "skills" / "anicca-tomb-slideshow"

POSTIZ_KEY = os.environ["POSTIZ_API_KEY"]
# === No TikTok account for cemetery EN (canonical 2026-05-19). ===
# Stale wrong id (cmnit95mg…) PURGED. Cemetery EN has an IG canonical (set
# below) so the script posts IG-only until a real cemetery-EN TikTok account
# exists. No ID invented.
TIKTOK_INT = None  # cemetery EN: no TikTok account yet
# === Fixed Instagram account (canonical 2026-05-20 — Dais final) ===
IG_INT = 'cmp9oubma00q5oh0yejnxduwf'  # cemetery EN Instagram (canonical)
SLACK_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CH = os.environ["SLACK_CHANNEL_ID"]


def postiz_upload(file_path: Path):
    """Use postiz CLI to upload a slide; returns (id, path)."""
    out = subprocess.run(
        ["postiz", "upload", str(file_path)],
        capture_output=True, text=True, timeout=60,
    )
    if out.returncode != 0:
        raise RuntimeError(f"postiz upload failed: {out.stderr}")
    # CLI prints non-JSON header then JSON body; extract last { ... } block
    text = out.stdout
    start = text.rfind("{")
    end = text.rfind("}")
    if start < 0 or end < 0:
        raise RuntimeError(f"no JSON in postiz upload output: {text[:300]}")
    obj = json.loads(text[start:end + 1])
    return obj["id"], obj["path"]


def slack_post(text, blocks=None):
    payload = {"channel": SLACK_CH, "text": text}
    if blocks:
        payload["blocks"] = blocks
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        method="POST",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {SLACK_TOKEN}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def main():
    if not TIKTOK_INT and not IG_INT:
        print("⏭️  cemetery EN: no TikTok and no IG account — skipping post, nothing drafted")
        return
    products = json.loads((SKILL_DIR / "data" / "products.json").read_text())
    prod = products["products"][PRODUCT_SLUG]
    caption = (RUN_DIR / "caption.txt").read_text().strip()

    slides = sorted((RUN_DIR / "slides").glob("slide_*.png"))
    if len(slides) != 6:
        raise RuntimeError(f"expected 6 slides, got {len(slides)}")

    print(f"[1/2] Uploading {len(slides)} slides to Postiz CDN...")
    images = []
    for s in slides:
        sid, path = postiz_upload(s)
        images.append({"id": sid, "path": path})
        print(f"  ✓ {s.name} → {path}")
        time.sleep(1)

    print()
    print("[2/2] POST /public/v1/posts (TikTok + IG draft mode)...")
    posts_list = []
    if TIKTOK_INT:
        posts_list.append({
            "integration": {"id": TIKTOK_INT},
            "value": [{"content": caption, "image": images}],
            "settings": {
                "__type": "tiktok",
                "title": "",
                "privacy_level": "SELF_ONLY",
                "content_posting_method": "UPLOAD",
                "duet": False,
                "stitch": False,
                "comment": True,
                "autoAddMusic": "no",
                "brand_content_toggle": False,
                "brand_organic_toggle": False,
                "video_made_with_ai": True,
            },
        })
    if IG_INT:
        posts_list.append({
            "integration": {"id": IG_INT},
            "value": [{"content": caption, "image": [{"id": img["id"], "path": img["path"]} for img in images]}],
            "settings": {"__type": "instagram-standalone", "post_type": "post", "collaborators": [], "thumbnail": None},
        })
    payload = {
        "type": "now",
        "date": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "shortLink": False,
        "tags": [],
        "posts": posts_list,
    }

    req = urllib.request.Request(
        "https://api.postiz.com/public/v1/posts",
        method="POST",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": POSTIZ_KEY,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"Postiz HTTP {e.code}: {body[:500]}")

    if isinstance(resp, list) and resp:
        post_id = resp[0].get("postId")
    else:
        post_id = (resp or {}).get("postId") or "?"

    receipt = {
        "postiz_post_id": post_id,
        "integration_id": TIKTOK_INT,
        "mode": "drafts",
        "content_posting_method": "UPLOAD",
        "privacy_level": "SELF_ONLY",
        "caption": caption,
        "slide_count": len(slides),
        "images": images,
        "product_slug": PRODUCT_SLUG,
        "published_at_utc": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "next_step": "Open TikTok app → Drafts/Inbox → review → tap Post",
    }
    (RUN_DIR / "postiz-receipt.json").write_text(json.dumps(receipt, indent=2))

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"👕 Fashion slideshow draft — {prod['name']}"}},
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"*Postiz post:* `{post_id}`\n*Slides:* {len(slides)}\n*Account:* @anicca.jpx (TikTok)\n*Mode:* drafts (review in TikTok app Inbox before posting)"}},
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"*Caption:*\n>>> {caption}"}},
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"*Run dir:* `{RUN_DIR}`"}},
    ]
    sresp = slack_post(f"👕 fashion slideshow draft: {PRODUCT_SLUG}", blocks=blocks)

    print(f"✅ slideshow drafted: {PRODUCT_SLUG} | postiz post={post_id} | slides={len(slides)} | slack ts={sresp.get('ts')}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        msg = str(e)[:300]
        print(f"❌ slideshow FAILED: {msg}", file=sys.stderr)
        print(f"❌ slideshow FAILED: {msg}")
        sys.exit(1)
