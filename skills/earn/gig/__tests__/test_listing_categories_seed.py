"""test_listing_categories_seed.py — RED (Phase 2a, feature gig-feasibility-volume).
PROP-005 / REQ-GFV-004 — `strategy.default.json.listing_categories` has >=8 entries; every entry's
`price_jpy_initial` falls in [0.5, 0.7] x `price_jpy_target` (design doc's "初期は相場の50〜70%").
PROP-004 companion check (占い reclassification, REQ-GFV-003) is included here too since it reads
the SAME seed file this test already loads — zero `占い`/`霊感`/`スピリチュアル` entries remain in
`skip_categories`, and exactly one `listing_categories` entry matches that text-reading content.

`strategy.default.json` does not have `listing_categories` yet -> KeyError -> RED.
"""
import json
import os
import re
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_STRATEGY = os.path.join(SKILL_DIR, "strategy.default.json")

P = 0
F = 0


def chk(name, got, want):
    global P, F
    if got == want:
        print(f"  ok {name} ({got})")
        P += 1
    else:
        print(f"  FAIL {name} want={want} got={got}")
        F += 1


with open(DEFAULT_STRATEGY, encoding="utf-8") as f:
    seed = json.load(f)

listing_categories = seed["listing_categories"]  # RED: KeyError, key does not exist yet

chk("PROP-005: listing_categories has >=8 entries", len(listing_categories) >= 8, True)

price_ratio_ok = True
for entry in listing_categories:
    initial = entry.get("price_jpy_initial")
    target = entry.get("price_jpy_target")
    if not (initial and target and 0.5 * target <= initial <= 0.7 * target):
        price_ratio_ok = False
        print(f"    bad ratio: {entry.get('category')} initial={initial} target={target}")
chk("PROP-005: every entry's price_jpy_initial is 50-70% of price_jpy_target", price_ratio_ok, True)

fortune_pattern = re.compile("占い|霊感|スピリチュアル")
skip_categories = seed.get("skip_categories", [])
skip_fortune_hits = [c for c in skip_categories if fortune_pattern.search(c)]
chk("PROP-004: skip_categories contains ZERO 占い/霊感/スピリチュアル entries", len(skip_fortune_hits), 0)

listing_fortune_hits = [e for e in listing_categories if fortune_pattern.search(str(e.get("category", "")))]
chk("PROP-004: listing_categories contains EXACTLY ONE 占い-style entry", len(listing_fortune_hits), 1)

required_categories = [
    "SEO記事/LP文章", "ネーミング/キャッチコピー", "Excel/VBA自動化", "EC商品説明文",
    "プレゼン/パワポ", "文字起こし×要約", "翻訳", "FAQ生成",
]
listed_names = " ".join(str(e.get("category", "")) for e in listing_categories)
missing = [c for c in required_categories if c not in listed_names]
chk("PROP-005: covers the design doc's named categories (SEO記事/LP文章 etc, none missing)",
    missing, [])

print(f"=== test_listing_categories_seed: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
