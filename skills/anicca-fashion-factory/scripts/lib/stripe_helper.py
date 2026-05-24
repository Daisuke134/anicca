"""Stripe API wrapper using urllib (no external deps)."""
import os
import json
import urllib.request
import urllib.parse
from pathlib import Path


def _load_env():
    env_path = Path.home() / ".openclaw" / ".env"
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            if k.startswith("export "):
                k = k[7:]
            os.environ.setdefault(k.strip(), v.strip())


def _post(path: str, params: dict) -> dict:
    _load_env()
    key = os.environ["STRIPE_SECRET_KEY"]
    pairs = []
    for k, v in params.items():
        if isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    for sk, sv in item.items():
                        pairs.append((f"{k}[{i}][{sk}]", str(sv)))
                else:
                    pairs.append((f"{k}[]", str(item)))
        elif isinstance(v, dict):
            for sk, sv in v.items():
                pairs.append((f"{k}[{sk}]", str(sv)))
        else:
            pairs.append((k, str(v)))
    data = urllib.parse.urlencode(pairs).encode()
    req = urllib.request.Request(
        f"https://api.stripe.com/v1/{path}",
        data=data,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _get(path: str, params: dict = None) -> dict:
    _load_env()
    key = os.environ["STRIPE_SECRET_KEY"]
    qs = ("?" + urllib.parse.urlencode(params)) if params else ""
    req = urllib.request.Request(
        f"https://api.stripe.com/v1/{path}{qs}",
        headers={"Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def create_product(name: str, description: str, image_url: str, metadata: dict) -> str:
    params = {
        "name": name,
        "description": description,
        "images[]": image_url,
    }
    for k, v in metadata.items():
        params[f"metadata[{k}]"] = v
    res = _post("products", params)
    return res["id"]


def create_price(product_id: str, unit_amount_cents: int, currency: str = "usd") -> str:
    res = _post("prices", {
        "product": product_id,
        "unit_amount": unit_amount_cents,
        "currency": currency,
        "tax_behavior": "exclusive",
    })
    return res["id"]


def create_payment_link(price_id: str, shipping_countries: list, metadata: dict) -> str:
    params = {
        "line_items": [{
            "price": price_id,
            "quantity": 1,
            "adjustable_quantity[enabled]": "true",
            "adjustable_quantity[minimum]": 1,
            "adjustable_quantity[maximum]": 10,
        }],
        "shipping_address_collection[allowed_countries][]": shipping_countries,
    }
    for k, v in metadata.items():
        params[f"metadata[{k}]"] = v
    res = _post("payment_links", params)
    return res["url"]


def list_charges(created_gte: int = None, limit: int = 100) -> list:
    params = {"limit": limit}
    if created_gte:
        params["created[gte]"] = created_gte
    res = _get("charges", params)
    return res.get("data", [])


def list_payment_intents(created_gte: int = None, limit: int = 100) -> list:
    params = {"limit": limit}
    if created_gte:
        params["created[gte]"] = created_gte
    res = _get("payment_intents", params)
    return res.get("data", [])
