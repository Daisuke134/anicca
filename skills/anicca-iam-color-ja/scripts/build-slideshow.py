#!/usr/bin/env python3
"""Template B JA (solid color + bold) — anicca-iam-color-ja."""
import os, sys, json, datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

if len(sys.argv) < 2:
    print("usage: build-slideshow.py <run_dir>", file=sys.stderr); sys.exit(1)
RUN_DIR = Path(sys.argv[1])
SKILL_DIR = Path(__file__).resolve().parent.parent
LANG = "ja"
W, H = 1080, 1350

PALETTE = [
    ("#F3D9E5","#9B3656"), ("#F5EDE0","#7E6243"), ("#E5DEEF","#5A3D7A"), ("#DCE7D4","#3B5043"),
    ("#D4E3EE","#244C6E"), ("#FBDDCB","#7A3219"), ("#D6E8DE","#2E5B45"), ("#E8DCC4","#6B4F23"),
]

IAM_TEMPLATE_B_JA = [
    {"id":"iam-b-ja-001","text":"私は今のままで充分です。","lines":["私は","今のままで","充分です。"],"source":"i.am app screenshot 6.5-2","source_url":"https://apps.apple.com/jp/app/i-am-positive-affirmations/id874656917"},
    {"id":"iam-b-ja-002","text":"私には美しい心と魂があります。","lines":["私には","美しい心と","魂があります。"],"source":"i.am app screenshot 6.5-2","source_url":"https://apps.apple.com/jp/app/i-am-positive-affirmations/id874656917"},
    {"id":"iam-b-ja-003","text":"物事は必要な形でうまくいく。","lines":["物事は","必要な形で","うまくいく。"],"source":"i.am app screenshot 6.5-6","source_url":"https://apps.apple.com/jp/app/i-am-positive-affirmations/id874656917"},
    {"id":"iam-b-ja-004","text":"私は愛と尊重を受けるに値する。","lines":["私は","愛と尊重を","受けるに","値する。"],"source":"i.am app screenshot 6.5-8","source_url":"https://apps.apple.com/jp/app/i-am-positive-affirmations/id874656917"},
    {"id":"iam-b-ja-005","text":"私は毎日ワクワク過ごしている。","lines":["私は毎日","ワクワク","過ごしている。"],"source":"玉野湖太","source_url":"https://note.com/tamano_tora/n/nbba06689facf"},
    {"id":"iam-b-ja-006","text":"私はチャンスに恵まれている。","lines":["私は","チャンスに","恵まれている。"],"source":"玉野湖太","source_url":"https://note.com/tamano_tora/n/nbba06689facf"},
    {"id":"iam-b-ja-007","text":"私は、なりつつある自分にわくわくしている。","lines":["私は、","なりつつある","自分に","わくわく","している。"],"source":"i.am app screenshot 6.5-7","source_url":"https://apps.apple.com/jp/app/i-am-positive-affirmations/id874656917"},
]

def h2r(h):
    h = h.lstrip("#"); return tuple(int(h[i:i+2],16) for i in (0,2,4))

def pick(run_dir):
    doy = int(datetime.datetime.now().strftime("%j"))
    p = IAM_TEMPLATE_B_JA[(doy - 1) % len(IAM_TEMPLATE_B_JA)]
    (run_dir / "picks.json").write_text(json.dumps([p], ensure_ascii=False, indent=2))
    return p

def compose(run_dir, p):
    doy = int(datetime.datetime.now().strftime("%j"))
    bg_hex, text_hex = PALETTE[((doy + 1) - 1) % len(PALETTE)]  # 1-step offset vs EN
    canvas = Image.new("RGB", (W, H), h2r(bg_hex))
    draw = ImageDraw.Draw(canvas)

    body_font = ImageFont.truetype(str(SKILL_DIR / "fonts" / "NotoSansJP-Bold.ttf"), 130)
    wmark_font = ImageFont.truetype(str(SKILL_DIR / "fonts" / "NotoSansJP-Bold.ttf"), 22)

    lines = p["lines"]
    LH = 150
    total_h = LH * len(lines)
    y = (H - total_h) // 2 - 30
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
