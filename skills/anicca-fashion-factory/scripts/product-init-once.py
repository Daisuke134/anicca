#!/usr/bin/env python3
"""Install-once: 3 mockup → Stripe products → Payment Links → /fashion LP update → Slack.

Idempotent: if products.json already exists with payment_link, skip Stripe creation.

stdout last line:
  ✅ fashion init: 3 products live | slack ts=<ts>
  ❌ fashion init FAILED: <reason>
"""
import os
import sys
import json
import urllib.request
import subprocess
import datetime
from pathlib import Path

SKILL_DIR = Path.home() / ".openclaw" / "skills" / "anicca-fashion-factory"
sys.path.insert(0, str(SKILL_DIR / "scripts" / "lib"))

from stripe_helper import create_product, create_price, create_payment_link
from slack_helper import post_blocks, load_env


def fal_generate(prompt: str, out_path: Path) -> None:
    load_env()
    fal_key = os.environ["FAL_API_KEY"]
    req = urllib.request.Request(
        "https://fal.run/fal-ai/flux/schnell",
        data=json.dumps({
            "prompt": prompt,
            "image_size": "square_hd",
            "num_inference_steps": 4,
            "num_images": 1,
        }).encode(),
        headers={
            "Authorization": f"Key {fal_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode())
    img_url = data["images"][0]["url"]
    urllib.request.urlretrieve(img_url, out_path)


def main():
    load_env()
    config = json.loads((SKILL_DIR / "data" / "config.json").read_text())
    products_file = SKILL_DIR / "data" / "products.json"
    fashion_public = Path(config["landing_repo"]) / config["fashion_public_path"]
    fashion_public.mkdir(parents=True, exist_ok=True)

    # Load or init products
    if products_file.exists():
        store = json.loads(products_file.read_text())
    else:
        store = {"products": []}

    by_slug = {p["slug"]: p for p in store["products"]}
    initialized = []

    for prod in config["products"]:
        slug = prod["slug"]
        existing = by_slug.get(slug)
        if existing and existing.get("payment_link"):
            # Backfill display fields from config so older minimal records still render
            existing.setdefault("title", prod["title"])
            existing.setdefault("tagline", prod["tagline"])
            existing["price_usd"] = prod["price_usd"]
            by_slug[slug] = existing
            initialized.append(slug)
            continue

        # 1. Generate mockup
        img_path = fashion_public / f"{slug}.jpg"
        if not img_path.exists():
            mockup_prompt = (
                f"Premium product photography of {prod['garment']} on a transparent ghost mannequin, "
                f"studio lighting, soft cream gradient background, {prod['design_brief']}. "
                "Catalog photo. Ultra clean. No model."
            )
            print(f"  [{slug}] gen mockup...", flush=True)
            fal_generate(mockup_prompt, img_path)
        else:
            print(f"  [{slug}] mockup exists, skip gen", flush=True)

        # 2. Stripe product + price + payment link
        print(f"  [{slug}] Stripe product+price+link...", flush=True)
        prod_id = create_product(
            name=prod["title"],
            description=prod["tagline"] + " — " + prod["design_brief"],
            image_url=f"https://aniccaai.com/fashion/{slug}.jpg",
            metadata={"skill": "anicca-fashion-factory", "product": slug, "type": "apparel"},
        )
        price_id = create_price(prod_id, prod["price_usd"] * 100)
        link = create_payment_link(
            price_id,
            shipping_countries=config["shipping_countries"],
            metadata={"skill": "anicca-fashion-factory", "product": slug},
        )

        entry = {
            "slug": slug,
            "title": prod["title"],
            "tagline": prod["tagline"],
            "price_usd": prod["price_usd"],
            "stripe_product_id": prod_id,
            "stripe_price_id": price_id,
            "payment_link": link,
            "image": f"/fashion/{slug}.jpg",
            "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        }
        by_slug[slug] = entry
        initialized.append(slug)

    store["products"] = list(by_slug.values())
    products_file.write_text(json.dumps(store, indent=2, ensure_ascii=False))

    # 3. Slack notify
    lines = [f"• <{p['payment_link']}|{p['title']}> · *${p['price_usd']}*"
             for p in store["products"]]
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "👕 Fashion init complete"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}},
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"*LP:* https://{config['lp_url']}\n*Stripe:* live mode\n*Mockups:* fal.ai flux/schnell\n*TODO:* Printful API for auto-fulfillment"}},
    ]
    resp = post_blocks(
        channel=os.environ["SLACK_CHANNEL_ID"],
        text_fallback=f"👕 fashion init: {len(store['products'])} products live",
        blocks=blocks,
    )
    print(f"✅ fashion init: {len(store['products'])} products live | slack ts={resp['ts']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ fashion init FAILED: {e}", file=sys.stderr)
        print(f"❌ fashion init FAILED: {e}")
        sys.exit(1)
