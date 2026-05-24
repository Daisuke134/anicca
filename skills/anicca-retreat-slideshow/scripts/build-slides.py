#!/usr/bin/env python3
"""Build 6 typography-only slides (1080x1920) for retreat slideshow.
Args: <theme_slug> <run_dir>
"""
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

if len(sys.argv) < 3:
    print("usage: build-slides.py <theme_slug> <run_dir>", file=sys.stderr)
    sys.exit(1)

THEME_SLUG = sys.argv[1]
RUN_DIR = Path(sys.argv[2])
SKILL_DIR = Path.home() / ".openclaw" / "skills" / "anicca-retreat-slideshow"

W, H = 1080, 1920
PAD = 100

# Font fallback chain (system fonts available on macOS)
DISPLAY_FONTS = [
    "/Library/Fonts/Cormorant Garamond.ttc",
    "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "/System/Library/Fonts/Times.ttc",
]
BODY_FONTS = [
    "/Library/Fonts/IBM Plex Sans.ttc",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
]
MONO_FONTS = [
    "/Library/Fonts/IBM Plex Mono.ttc",
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Monaco.ttf",
    "/System/Library/Fonts/Courier New.ttf",
]


def font(family, size):
    for path in family:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def hex_or_rgb(c):
    if isinstance(c, list) and len(c) >= 3:
        return tuple(c[:3])
    return tuple(c)


def wrap_lines(draw, text, font_obj, max_width):
    words = text.split(" ")
    lines = []
    current = ""
    for w in words:
        test = (current + " " + w).strip()
        bb = draw.textbbox((0, 0), test, font=font_obj)
        if bb[2] - bb[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


def draw_centered_block(img, draw, text, font_obj, color, top_y, line_spacing=1.2):
    """Draw multi-line text centered horizontally, starting at top_y. Returns next y."""
    lines = text.split("\n")
    y = top_y
    for line in lines:
        bb = draw.textbbox((0, 0), line, font=font_obj)
        w = bb[2] - bb[0]
        h = bb[3] - bb[1]
        x = (img.width - w) // 2
        draw.text((x, y), line, font=font_obj, fill=color)
        y += int(h * line_spacing)
    return y


def draw_left_block(img, draw, text, font_obj, color, top_y, x=PAD, line_spacing=1.25):
    lines = text.split("\n")
    y = top_y
    for line in lines:
        bb = draw.textbbox((0, 0), line, font=font_obj)
        h = bb[3] - bb[1]
        draw.text((x, y), line, font=font_obj, fill=color)
        y += int(h * line_spacing)
    return y


def draw_eyebrow(draw, text, color, y=140):
    f = font(MONO_FONTS, 26)
    spaced = "  ".join(text.upper())
    bb = draw.textbbox((0, 0), spaced, font=f)
    x = (W - (bb[2] - bb[0])) // 2
    draw.text((x, y), spaced, font=f, fill=color)


def draw_thin_rule(draw, y, color, x1=PAD, x2=W - PAD, weight=1):
    for i in range(weight):
        draw.line([(x1, y + i), (x2, y + i)], fill=color)


def draw_footer_url(draw, color, y=H - 130):
    f = font(MONO_FONTS, 28)
    text = "aniccaai.com/retreat"
    bb = draw.textbbox((0, 0), text, font=f)
    x = (W - (bb[2] - bb[0])) // 2
    draw.text((x, y), text, font=f, fill=color)


def draw_pagination(draw, idx, total, color, y=H - 70):
    f = font(MONO_FONTS, 22)
    text = f"{idx:02d} / {total:02d}"
    bb = draw.textbbox((0, 0), text, font=f)
    x = (W - (bb[2] - bb[0])) // 2
    draw.text((x, y), text, font=f, fill=color)


def new_canvas(palette):
    return Image.new("RGB", (W, H), hex_or_rgb(palette["paper"]))


def main():
    cfg = json.loads((SKILL_DIR / "data" / "themes.json").read_text())
    palette = cfg["palette"]
    theme = cfg["themes"][THEME_SLUG]
    cta_url = cfg["cta_url"]

    paper = hex_or_rgb(palette["paper"])
    ink = hex_or_rgb(palette["ink"])
    terra = hex_or_rgb(palette["terra"])
    dim = hex_or_rgb(palette["dim"])
    rule = (ink[0], ink[1], ink[2])

    slides_dir = RUN_DIR / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)

    label = theme["label"]
    total = 6

    # --- Slide 1: Hook ---
    img = new_canvas(palette)
    draw = ImageDraw.Draw(img)
    draw_eyebrow(draw, f"§ {label}", dim)
    draw_thin_rule(draw, 220, rule + (60,) if isinstance(rule, tuple) else rule, x1=W // 2 - 60, x2=W // 2 + 60)
    f_hook = font(DISPLAY_FONTS, 130)
    draw_centered_block(img, draw, theme["hook"], f_hook, ink, 460, line_spacing=1.05)
    draw_pagination(draw, 1, total, dim)
    img.save(slides_dir / "slide_01.png")

    # --- Slide 2: Diagnosis ---
    img = new_canvas(palette)
    draw = ImageDraw.Draw(img)
    draw_eyebrow(draw, "Why this happens", dim)
    f_d = font(DISPLAY_FONTS, 64)
    draw_left_block(img, draw, theme["diagnosis"], f_d, ink, 320, x=PAD, line_spacing=1.35)
    draw_thin_rule(draw, H - 220, terra, x1=PAD, x2=PAD + 120, weight=2)
    draw_pagination(draw, 2, total, dim)
    img.save(slides_dir / "slide_02.png")

    # --- Slide 3: Remedy ---
    img = new_canvas(palette)
    draw = ImageDraw.Draw(img)
    draw_eyebrow(draw, "The remedy", terra)
    f_r = font(DISPLAY_FONTS, 84)
    draw_centered_block(img, draw, theme["remedy"], f_r, ink, 380, line_spacing=1.25)
    draw_pagination(draw, 3, total, dim)
    img.save(slides_dir / "slide_03.png")

    # --- Slide 4: Steps (numbered) ---
    img = new_canvas(palette)
    draw = ImageDraw.Draw(img)
    draw_eyebrow(draw, "Practice", dim)
    y = 360
    for i, step in enumerate(theme["steps"], start=1):
        roman = ["I", "II", "III", "IV", "V"][i - 1]
        f_num = font(DISPLAY_FONTS, 64)
        f_step = font(BODY_FONTS, 42)
        # Number
        draw.text((PAD, y), roman, font=f_num, fill=terra)
        # Step text wrapped
        max_w = W - 2 * PAD - 140
        lines = wrap_lines(draw, step, f_step, max_w)
        sy = y + 8
        for line in lines:
            draw.text((PAD + 140, sy), line, font=f_step, fill=ink)
            bb = draw.textbbox((0, 0), line, font=f_step)
            sy += int((bb[3] - bb[1]) * 1.4)
        y = sy + 60
    draw_pagination(draw, 4, total, dim)
    img.save(slides_dir / "slide_04.png")

    # --- Slide 5: Bridge ---
    img = new_canvas(palette)
    draw = ImageDraw.Draw(img)
    draw_eyebrow(draw, "Anicca Retreats", terra)
    f_b = font(DISPLAY_FONTS, 76)
    draw_centered_block(img, draw, theme["bridge"], f_b, ink, 380, line_spacing=1.25)
    draw_pagination(draw, 5, total, dim)
    img.save(slides_dir / "slide_05.png")

    # --- Slide 6: CTA ---
    img = new_canvas(palette)
    draw = ImageDraw.Draw(img)
    draw_eyebrow(draw, "Apply", dim)
    f_cta = font(DISPLAY_FONTS, 96)
    draw_centered_block(img, draw, "Twelve seats.\nNo fee.\nTokyo, 2026 →", f_cta, ink, 540, line_spacing=1.2)
    draw_thin_rule(draw, H - 320, terra, x1=W // 2 - 80, x2=W // 2 + 80, weight=2)
    f_url = font(MONO_FONTS, 36)
    bb = draw.textbbox((0, 0), cta_url, font=f_url)
    x = (W - (bb[2] - bb[0])) // 2
    draw.text((x, H - 240), cta_url, font=f_url, fill=terra)
    draw_pagination(draw, 6, total, dim)
    img.save(slides_dir / "slide_06.png")

    # --- Caption ---
    (RUN_DIR / "caption.txt").write_text(theme["caption"])

    print(f"  ✓ 6 slides built in {slides_dir}")


if __name__ == "__main__":
    main()
