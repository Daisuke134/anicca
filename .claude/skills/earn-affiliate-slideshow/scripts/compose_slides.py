#!/usr/bin/env python3
"""Compose JP slide text onto generated background images → final 1080x1920 slides.

Reads a deck JSON (slides[].text + n) and the bg images slide_<n>.png in WORK,
writes composed_<n>.png. Clean typographic overlay in the top negative space.

Usage: compose_slides.py <deck.json> <work_dir>
"""
import sys, json, os
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FONT = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
INK = (38, 50, 56)        # charcoal navy, matches the illustration figure
ACCENT = (224, 152, 50)   # warm amber accent (matches the bubble glow)

deck = json.load(open(sys.argv[1]))
work = sys.argv[2]

def fit(img):
    img = img.convert("RGB")
    # scale to cover 1080x1920 then center-crop
    r = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * r), round(img.height * r)), Image.LANCZOS)
    x = (img.width - W) // 2; y = (img.height - H) // 2
    return img.crop((x, y, x + W, y + H))

def draw_text(d, lines, font, top, color, lh=1.28):
    # measure
    sizes = [d.textbbox((0, 0), ln, font=font) for ln in lines]
    line_h = max(s[3] - s[1] for s in sizes)
    y = top
    for ln, s in zip(lines, sizes):
        w = s[2] - s[0]
        x = (W - w) // 2
        # soft readability halo
        for dx, dy in ((-2,-2),(2,-2),(-2,2),(2,2),(0,3)):
            d.text((x+dx, y+dy), ln, font=font, fill=(255, 251, 240))
        d.text((x, y), ln, font=font, fill=color)
        y += int(line_h * lh)
    return y

for s in deck["slides"]:
    n = s["n"]
    bg_path = os.path.join(work, f"slide_{n}.png")
    if not os.path.exists(bg_path):
        print(f"missing {bg_path}"); continue
    img = fit(Image.open(bg_path))
    d = ImageDraw.Draw(img)
    is_cta = s.get("role") == "cta"
    lines = [l for l in s["text"].split("\n") if l.strip()]
    # CTA: keep #PR on its own smaller line
    pr = None
    if is_cta and lines and lines[-1].strip() == "#PR":
        pr = lines.pop()
    fsize = 104 if max(len(l) for l in lines) <= 6 else 86
    font = ImageFont.truetype(FONT, fsize)
    end_y = draw_text(d, lines, font, top=150, color=INK)
    if pr:
        prf = ImageFont.truetype(FONT, 52)
        d.text((W - d.textlength(pr, font=prf) - 60, H - 110), pr, font=prf, fill=ACCENT)
    out = os.path.join(work, f"composed_{n}.png")
    img.save(out, "PNG")
    print(f"composed_{n}.png  ({fsize}px, {len(lines)} lines)")
print("DONE")
