#!/usr/bin/env python3
"""Rebuild the CTA slide to feature the REAL product (book cover) — affiliate best practice.
Clean cream bg + book cover (with soft shadow) + CTA text + product name + #PR + up-arrow.
Usage: compose_cta_book.py <work_dir> <book_cover.jpg> <out.png> <product_name>
"""
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
CREAM = (250, 243, 227)
INK = (38, 50, 56)
AMBER = (224, 152, 50)
FONT = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
FONT_M = "/System/Library/Fonts/ヒラギノ角ゴシック W5.ttc"

work, book_path, out, product = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

img = Image.new("RGB", (W, H), CREAM)
d = ImageDraw.Draw(img)

# --- top CTA text ---
f_big = ImageFont.truetype(FONT, 92)
lines = ["プロフィールの", "リンクから", "チェック"]
y = 130
for ln in lines:
    w = d.textlength(ln, font=f_big)
    d.text(((W - w) / 2, y), ln, font=f_big, fill=INK)
    y += int(92 * 1.3)

# --- book cover, centered, with soft shadow ---
book = Image.open(book_path).convert("RGB")
bw = 560
bh = int(book.height * bw / book.width)
book = book.resize((bw, bh), Image.LANCZOS)
bx, by = (W - bw) // 2, 760
# shadow
shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sd = ImageDraw.Draw(shadow)
sd.rounded_rectangle([bx - 8, by - 8, bx + bw + 8, by + bh + 8], radius=14, fill=(0, 0, 0, 90))
shadow = shadow.filter(ImageFilter.GaussianBlur(22))
img.paste(Image.new("RGB", (W, H), CREAM), (0, 0), Image.new("L", (W, H), 0))  # noop keep
img = Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB")
d = ImageDraw.Draw(img)
img.paste(book, (bx, by))
# thin border
d.rectangle([bx, by, bx + bw, by + bh], outline=(225, 215, 195), width=3)

# --- product name caption under the book ---
f_cap = ImageFont.truetype(FONT_M, 40)
cap = product
cy = by + bh + 34
# wrap if long
import textwrap
for cl in textwrap.wrap(cap, width=18):
    w = d.textlength(cl, font=f_cap)
    d.text(((W - w) / 2, cy), cl, font=f_cap, fill=INK)
    cy += 52

# --- #PR bottom-right ---
f_pr = ImageFont.truetype(FONT, 50)
d.text((W - d.textlength("#PR", font=f_pr) - 56, H - 104), "#PR", font=f_pr, fill=AMBER)

# --- small "↑ リンクはプロフィール" hint near top under text ---
f_hint = ImageFont.truetype(FONT_M, 34)
hint = "▲ リンクはプロフィールに"
w = d.textlength(hint, font=f_hint)
d.text(((W - w) / 2, y + 12), hint, font=f_hint, fill=AMBER)

img.save(out, "PNG")
print("CTA rebuilt with real book cover →", out)
