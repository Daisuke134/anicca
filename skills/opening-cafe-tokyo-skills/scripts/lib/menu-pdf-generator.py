#!/usr/bin/env python3
"""Entity-agnostic menu PDF generator.

Generates an A4 portrait menu PDF from data/config.json + data/cafe/menu.json.
Used by phase4-uber-merchant-signup.sh for Uber Eats Merchant menu upload
(PDF mode) and by Phase 5 (live menu publish).

Usage:
  python3 lib/menu-pdf-generator.py <config.json> <menu.json> <output.pdf>

Output: A4 portrait PDF (1240×1754 px @ 150 DPI) with brand header,
        single-product spotlight, allergens, hours, footer.

Idempotent: overwrites output if newer content. Caller checks mtime if needed.
"""
import os
import sys
import json
import pathlib
from PIL import Image, ImageDraw, ImageFont


W, H = 1240, 1754
INK    = (20, 16, 14)
DIM    = (130, 130, 130)
CREAM  = (251, 247, 239)

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Futura.ttc",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
]


def font(size: int):
    for f in FONT_CANDIDATES:
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                continue
    return ImageFont.load_default()


def main() -> int:
    if len(sys.argv) < 4:
        print("usage: menu-pdf-generator.py <config.json> <menu.json> <output.pdf>",
              file=sys.stderr)
        return 1

    config_path = pathlib.Path(sys.argv[1])
    menu_path   = pathlib.Path(sys.argv[2])
    out_path    = pathlib.Path(sys.argv[3])

    config = json.loads(config_path.read_text()) if config_path.exists() else {}
    menu   = json.loads(menu_path.read_text()) if menu_path.exists() else {}

    brand    = (config.get("brand") or {}).get("name") or config.get("brand_name") or "Anicca Cafe"
    tagline  = (config.get("brand") or {}).get("tagline") or "Tokyo · Uber Eats only"
    accent_rgb = tuple((config.get("brand") or {}).get("accent_rgb") or [232, 154, 60])

    # menu.json shape:
    #   {"items":[{"name","price_jpy","description","allergens":[..]}],
    #    "hours":"...", "footer_url":"..."}
    items     = menu.get("items") or []
    if not items:
        # fallback to config.product
        prod = config.get("product") or {}
        if prod.get("name"):
            items = [{
                "name":        prod.get("name"),
                "price_jpy":   prod.get("price_jpy", 0),
                "description": prod.get("description", ""),
                "allergens":   prod.get("allergens", []),
            }]
    hours      = menu.get("hours") or "Saturday — Sunday: 11:00 — 15:00 JST"
    footer_url = menu.get("footer_url") or config.get("brand", {}).get("url") or "aniccaai.com/cafe"

    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)

    # Header
    d.text((100, 120), brand, font=font(72), fill=INK)
    d.text((100, 220), tagline, font=font(32), fill=DIM)
    d.line([(100, 290), (W - 100, 290)], fill=INK, width=2)

    # Single-product (or multi)
    d.text((100, 340), "MENU", font=font(28), fill=DIM)
    cy = 420
    for i, item in enumerate(items[:3]):  # limit 3 to keep clean
        name  = item.get("name", "")
        price = item.get("price_jpy", 0)
        desc  = item.get("description", "")
        d.text((100, cy), name, font=font(64), fill=INK)
        d.text((100, cy + 90), desc[:70], font=font(28), fill=DIM)
        d.text((W - 320, cy + 50), f"¥{price:,}", font=font(60), fill=accent_rgb)
        cy += 280

    # Allergens
    d.line([(100, 1100), (W - 100, 1100)], fill=DIM, width=1)
    d.text((100, 1140), "Allergens", font=font(28), fill=DIM)
    allergens = []
    for it in items:
        for a in it.get("allergens", []):
            if a not in allergens:
                allergens.append(a)
    if not allergens:
        allergens = ["Mango (fruit allergy). 28-major-allergens: none."]
    d.text((100, 1200), ", ".join(allergens)[:80], font=font(24), fill=INK)

    # Hours
    d.text((100, 1290), "Hours", font=font(28), fill=DIM)
    d.text((100, 1350), hours[:80], font=font(28), fill=INK)

    # Footer (anicca brand seal)
    d.text((100, 1500), "anicca", font=font(40), fill=accent_rgb)
    d.text((100, 1560), "impermanence", font=font(24), fill=DIM)
    d.text((100, 1620), footer_url, font=font(20), fill=INK)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out_path, "PDF", resolution=150.0)

    print(f"✅ menu-pdf: {len(items)} items → {out_path} ({out_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
