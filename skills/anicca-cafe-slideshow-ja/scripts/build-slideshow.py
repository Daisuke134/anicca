#!/usr/bin/env python3
"""Build 6-slide deck — v2 design (less marketing, fits within bounds).

Slides:
  1. Hook on cream — auto-fit headline
  2. Male model fullbleed — tiny "anicca" wordmark top-left only (NO PRICE)
  3. Female model fullbleed — tiny "anicca" wordmark top-left only (NO PRICE)
  4. Philosophy on ink — multi-line message, word-wrapped to fit
  5. "anicca = impermanence" (ink, restrained)
  6. CTA on cream — product name + tiny price subtitle + URL

Rules:
  - SAFE_MARGIN = 90px each side. max_width = W - 180 = 900px
  - All text auto-shrinks if too wide.
  - Multi-line messages split on '\n' (use \n in JSON, not '/').
  - No glyph that may be missing (no ↓). Use polygon arrow.
"""
import os
import sys
import json
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

if len(sys.argv) < 3:
    print("usage: build-slideshow.py <product_slug> <run_dir>", file=sys.stderr)
    sys.exit(1)

PRODUCT_SLUG = sys.argv[1]
RUN_DIR = Path(sys.argv[2])
SKILL_DIR = Path(__file__).resolve().parent.parent

products = json.loads((SKILL_DIR / "data" / "products.json").read_text())
prod = products["products"][PRODUCT_SLUG]
narrative = products["narrative"]

# Skill-specific accent (set via products.json["accent_rgb"] or default)
ACCENT_RGB = tuple(products.get("accent_rgb", [232, 154, 60]))

# ── Step 1: Generate AI model images ────────────────────────────────────────
FAL_KEY = os.environ.get("FAL_API_KEY") or os.environ.get("FAL_KEY")
if not FAL_KEY:
    print("ERR: FAL_API_KEY not set", file=sys.stderr)
    sys.exit(2)


def fal_generate(prompt: str, out_path: Path) -> None:
    req = urllib.request.Request(
        "https://fal.run/fal-ai/flux/dev",
        method="POST",
        data=json.dumps({
            "prompt": prompt,
            "image_size": {"width": 1080, "height": 1920},
            "num_inference_steps": 28,
            "guidance_scale": 3.5,
            "num_images": 1,
        }).encode(),
        headers={
            "Authorization": f"Key {FAL_KEY}",
            "Content-Type": "application/json",
        },
    )
    print(f"  fal.ai generating: {out_path.name} ...", flush=True)
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode())
    img_url = data["images"][0]["url"]
    urllib.request.urlretrieve(img_url, out_path)
    print(f"  ✓ saved {out_path}", flush=True)


images_dir = RUN_DIR / "images"
img_male = images_dir / "model-male.jpg"
img_female = images_dir / "model-female.jpg"
fal_generate(prod["model_prompt_male"], img_male)
fal_generate(prod["model_prompt_female"], img_female)

# ── Step 2: Compose 6 slides with Pillow ────────────────────────────────────
W, H = 1080, 1920
INK = (20, 16, 14)
CREAM = (251, 247, 239)
WHITE = (255, 255, 255)
DIM = (130, 130, 130)
ACCENT = ACCENT_RGB
SAFE_MARGIN = 90
MAX_TEXT_WIDTH = W - 2 * SAFE_MARGIN  # 900

FONT_CANDIDATES = [
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc",
    "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Futura.ttc",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
]


def font(size):
    for f in FONT_CANDIDATES:
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                continue
    return ImageFont.load_default()


def text_width(draw, text, f):
    bb = draw.textbbox((0, 0), text, font=f)
    return bb[2] - bb[0]


def fit_one_line(draw, text, max_size, min_size=32, max_width=None):
    """Return font size that fits within max_width."""
    if max_width is None:
        max_width = MAX_TEXT_WIDTH
    for size in range(max_size, min_size - 1, -2):
        f = font(size)
        if text_width(draw, text, f) <= max_width:
            return size, f
    f = font(min_size)
    return min_size, f


def wrap_words(draw, text, size, max_width=None):
    """Word-wrap to fit max_width at given font size."""
    if max_width is None:
        max_width = MAX_TEXT_WIDTH
    f = font(size)
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if text_width(draw, test, f) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_centered(draw, text, y, size, color, line_height=1.18):
    """Draw possibly multi-line text centered at y. Auto-fits each line via wrap."""
    f = font(size)
    raw_lines = text.split("\n")
    final_lines = []
    for ln in raw_lines:
        if text_width(draw, ln, f) <= MAX_TEXT_WIDTH:
            final_lines.append(ln)
        else:
            final_lines.extend(wrap_words(draw, ln, size))
    cy = y
    for ln in final_lines:
        tw = text_width(draw, ln, f)
        cx = (W - tw) / 2
        draw.text((cx, cy), ln, font=f, fill=color)
        cy += int(size * line_height)
    return cy


def draw_centered_autofit(draw, text, y, max_size, min_size, color, line_height=1.18):
    """For headlines that should NEVER wrap — auto-shrink until single line fits."""
    size, f = fit_one_line(draw, text, max_size, min_size)
    tw = text_width(draw, text, f)
    cx = (W - tw) / 2
    draw.text((cx, y), text, font=f, fill=color)
    return size


def make_slide_image_bg(image_path: Path, dim_top=False, dim_bottom=False):
    img = Image.open(image_path).convert("RGB")
    img = img.resize((W, H), Image.LANCZOS)
    base = img.copy()
    draw = ImageDraw.Draw(base, "RGBA")
    if dim_top:
        for i in range(0, 360):
            alpha = int(140 * (1 - i / 360))
            draw.rectangle([(0, i), (W, i + 1)], fill=(0, 0, 0, alpha))
    if dim_bottom:
        for i in range(0, 360):
            alpha = int(140 * (i / 360))
            draw.rectangle([(0, H - 360 + i), (W, H - 359 + i)], fill=(0, 0, 0, alpha))
    return base


def make_solid_slide(bg_color):
    return Image.new("RGB", (W, H), bg_color)


slides_dir = RUN_DIR / "slides"

# ── Slide 1: Hook on cream — auto-fit ───────────────────────────────────────
s1 = make_solid_slide(CREAM)
d = ImageDraw.Draw(s1)
hook_lines = narrative["slide_1_hook"].split("\n")
# multi-line: each line auto-fits independently
total_h = 0
sizes = []
for ln in hook_lines:
    sz, _ = fit_one_line(d, ln, 160, 60)
    sizes.append(sz)
    total_h += int(sz * 1.18)
y0 = (H - total_h) // 2
cy = y0
for ln, sz in zip(hook_lines, sizes):
    f = font(sz)
    tw = text_width(d, ln, f)
    d.text(((W - tw) / 2, cy), ln, font=f, fill=INK)
    cy += int(sz * 1.18)
s1.save(slides_dir / "slide_01.png")

# ── Slide 2: Male model — minimal overlay ───────────────────────────────────
s2 = make_slide_image_bg(img_male, dim_top=True)
d = ImageDraw.Draw(s2)
# tiny "anicca" wordmark top-left
f_brand = font(40)
d.text((SAFE_MARGIN, 90), "{{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}", font=f_brand, fill=WHITE)
s2.save(slides_dir / "slide_02.png")

# ── Slide 3: Female model — minimal overlay ─────────────────────────────────
s3 = make_slide_image_bg(img_female, dim_top=True)
d = ImageDraw.Draw(s3)
d.text((SAFE_MARGIN, 90), "{{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}", font=f_brand, fill=WHITE)
s3.save(slides_dir / "slide_03.png")

# ── Slide 4: Philosophy on ink — wrapped ────────────────────────────────────
s4 = make_solid_slide(INK)
d = ImageDraw.Draw(s4)
msg = narrative["slide_4_message"]
# pick a size such that the longest wrapped line fits
target_size = 96
# pre-compute all lines at target_size, then shrink if total height > 1100
lines = []
for raw_ln in msg.split("\n"):
    f = font(target_size)
    if text_width(d, raw_ln, f) <= MAX_TEXT_WIDTH:
        lines.append(raw_ln)
    else:
        lines.extend(wrap_words(d, raw_ln, target_size))
while target_size > 50 and len(lines) * int(target_size * 1.25) > 1100:
    target_size -= 6
    lines = []
    for raw_ln in msg.split("\n"):
        f = font(target_size)
        if text_width(d, raw_ln, f) <= MAX_TEXT_WIDTH:
            lines.append(raw_ln)
        else:
            lines.extend(wrap_words(d, raw_ln, target_size))
total_h = len(lines) * int(target_size * 1.25)
y0 = (H - total_h) // 2
f = font(target_size)
cy = y0
for ln in lines:
    tw = text_width(d, ln, f)
    d.text(((W - tw) / 2, cy), ln, font=f, fill=CREAM)
    cy += int(target_size * 1.25)
s4.save(slides_dir / "slide_04.png")

# ── Slide 5: "anicca = 諸行無常" on ink (JA) ────────────────────────────────
s5 = make_solid_slide(INK)
d = ImageDraw.Draw(s5)
draw_centered_autofit(d, "{{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}", 760, 200, 100, ACCENT)
# Use JA equivalent from narrative.slide_5_message, fallback to "諸行無常"
_sub = narrative.get("slide_5_message", "諸行無常")
# Strip "anicca = " prefix if present (we already drew anicca above)
if _sub.startswith("anicca = "):
    _sub = _sub[len("anicca = "):]
draw_centered_autofit(d, _sub, 1060, 120, 48, CREAM)
s5.save(slides_dir / "slide_05.png")

# ── Slide 6: Product CTA on cream — clean, restrained ───────────────────────
s6 = make_solid_slide(CREAM)
d = ImageDraw.Draw(s6)
# product name auto-fit
draw_centered_autofit(d, prod["name"], 780, 92, 48, INK)
# tiny subtitle: garment + price (price fine but small)
price_str = ""
if "price_jpy" in prod:
    price_str = f"¥{prod['price_jpy']:,}"
elif "price_usd" in prod:
    price_str = f"${prod['price_usd']}"
subtitle = f"{prod.get('garment', '')}  ·  {price_str}".strip(" ·")
draw_centered_autofit(d, subtitle, 900, 42, 28, DIM)
# URL
draw_centered_autofit(d, narrative["slide_6_cta_jp"], 1180, 72, 36, INK)
draw_centered_autofit(d, "(プロフィールから)", 1280, 38, 24, DIM)
s6.save(slides_dir / "slide_06.png")

# ── Step 3: Caption ─────────────────────────────────────────────────────────
import random
if "price_jpy" in prod:
    _price = prod["price_jpy"]
else:
    _price = int(prod.get("price_usd", 0) * 150)
caption = random.choice(narrative["captions"]).replace("{price}", f"{_price:,}")
(RUN_DIR / "caption.txt").write_text(caption)

print(f"✓ 6 slides built in {slides_dir}")
print(f"✓ caption written to {RUN_DIR}/caption.txt")
