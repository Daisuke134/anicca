#!/usr/bin/env python3
"""Template B EN (solid color + bold uppercase) — anicca-iam-color-en."""
import os, sys, json, datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

if len(sys.argv) < 2:
    print("usage: build-slideshow.py <run_dir>", file=sys.stderr); sys.exit(1)
RUN_DIR = Path(sys.argv[1])
SKILL_DIR = Path(__file__).resolve().parent.parent
LANG = "en"
W, H = 1080, 1350

PALETTE = [
    ("#F3D9E5","#9B3656"), ("#F5EDE0","#7E6243"), ("#E5DEEF","#5A3D7A"), ("#DCE7D4","#3B5043"),
    ("#D4E3EE","#244C6E"), ("#FBDDCB","#7A3219"), ("#D6E8DE","#2E5B45"), ("#E8DCC4","#6B4F23"),
]

# Verified iam.affirmations Template B published posts (verbatim from IG profile grid + DG37kbmtxdW)
IAM_TEMPLATE_B = [
    {"id":"iam-b-001","text":"I SHOW UP FOR MYSELF EVERY SINGLE DAY.","lines":["I SHOW UP","FOR MYSELF","EVERY SINGLE","DAY."],"source":"@iam.affirmations","source_url":"https://www.instagram.com/iam.affirmations/"},
    {"id":"iam-b-002","text":"I AM AT PEACE WITH WHERE I AM AND EXCITED ABOUT WHERE I'M GOING.","lines":["I AM AT PEACE","WITH WHERE I AM","AND EXCITED","ABOUT WHERE","I'M GOING."],"source":"@iam.affirmations","source_url":"https://www.instagram.com/iam.affirmations/"},
    {"id":"iam-b-003","text":"I AM TOO WHOLE TO SETTLE FOR ANYTHING HALF-HEARTED.","lines":["I AM TOO WHOLE","TO SETTLE FOR","ANYTHING","HALF-HEARTED."],"source":"@iam.affirmations","source_url":"https://www.instagram.com/iam.affirmations/"},
    {"id":"iam-b-004","text":"I SEE IT. I LIKE IT. I WANT IT. I GOT IT.","lines":["I SEE IT.","I LIKE IT.","I WANT IT.","I GOT IT."],"source":"@iam.affirmations DG37kbmtxdW","source_url":"https://www.instagram.com/p/DG37kbmtxdW/"},
    {"id":"iam-b-005","text":"MY STORY IS NOT OVER. THE BEST CHAPTERS ARE STILL BEING WRITTEN.","lines":["MY STORY","IS NOT OVER.","THE BEST","CHAPTERS","ARE STILL","BEING WRITTEN."],"source":"@iam.affirmations","source_url":"https://www.instagram.com/iam.affirmations/"},
    {"id":"iam-b-006","text":"I AM READY TO START A NEW CHAPTER IN MY LIFE.","lines":["I AM READY","TO START A","NEW CHAPTER","IN MY LIFE."],"source":"@iam.affirmations","source_url":"https://www.instagram.com/iam.affirmations/"},
    {"id":"iam-b-007","text":"I ATTRACT WHAT IS MEANT FOR ME.","lines":["I ATTRACT","WHAT IS","MEANT FOR","ME."],"source":"@iam.affirmations","source_url":"https://www.instagram.com/iam.affirmations/"},
]

def h2r(h):
    h = h.lstrip("#"); return tuple(int(h[i:i+2],16) for i in (0,2,4))

def pick(run_dir):
    doy = int(datetime.datetime.now().strftime("%j"))
    p = IAM_TEMPLATE_B[(doy - 1) % len(IAM_TEMPLATE_B)]
    (run_dir / "picks.json").write_text(json.dumps([p], ensure_ascii=False, indent=2))
    return p

def compose(run_dir, p):
    doy = int(datetime.datetime.now().strftime("%j"))
    bg_hex, text_hex = PALETTE[(doy - 1) % len(PALETTE)]
    canvas = Image.new("RGB", (W, H), h2r(bg_hex))
    draw = ImageDraw.Draw(canvas)

    body_font = ImageFont.truetype(str(SKILL_DIR / "fonts" / "TikTokSansDisplayBlack.ttf"), 96)
    wmark_font = ImageFont.truetype(str(SKILL_DIR / "fonts" / "TikTokSansDisplayBold.ttf"), 18)

    lines = p["lines"]
    LH = 110
    total_h = LH * len(lines)
    y = (H - total_h) // 2 - 50
    for ln in lines:
        draw.text((72, y), ln, font=body_font, fill=h2r(text_hex))
        y += LH

    wm = "ANICCAAI.COM"
    bb = draw.textbbox((0,0), wm, font=wmark_font); ww = bb[2]-bb[0]
    draw.text(((W-ww)//2, 1290), wm, font=wmark_font, fill=h2r(text_hex))

    out = run_dir / "slides" / "slide_01.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, "PNG", optimize=True)
    return out

def main():
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    p = pick(RUN_DIR)
    compose(RUN_DIR, p)
    (RUN_DIR / "first_line.txt").write_text(p["text"], encoding="utf-8")
    print(f"build OK: 1 slide '{p['text']}'")

if __name__ == "__main__":
    main()
