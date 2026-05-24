"""Printful API wrapper using urllib (no external deps)."""
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


def _request(path, method="GET", body=None, params=None):
    _load_env()
    api_key = os.environ["PRINTFUL_API_KEY"]
    store_id = os.environ.get("PRINTFUL_STORE_ID", "18142516")

    if params:
        path = path + "?" + urllib.parse.urlencode(params)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-PF-Store-Id": store_id,
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"https://api.printful.com{path}",
        method=method, data=data, headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        raise RuntimeError(f"HTTP {e.code}: {body_text[:500]}")


def list_sync_products():
    return _request("/store/products").get("result", [])


def get_sync_product(sync_product_id):
    return _request(f"/store/products/{sync_product_id}").get("result", {})


def list_orders(status=None, limit=20):
    params = {"limit": limit}
    if status:
        params["status"] = status
    return _request("/orders", params=params).get("result", [])


def get_order(order_id):
    return _request(f"/orders/{order_id}").get("result", {})


def create_order(recipient, items, external_id=None, confirm=False, shipping="STANDARD"):
    body = {
        "recipient": recipient,
        "items": items,
        "shipping": shipping,
    }
    if external_id:
        body["external_id"] = external_id
    path = "/orders"
    if confirm:
        path += "?confirm=true"
    return _request(path, method="POST", body=body).get("result", {})


def estimate_order_costs(recipient, items, shipping="STANDARD"):
    body = {
        "recipient": recipient,
        "items": items,
        "shipping": shipping,
    }
    return _request("/orders/estimate-costs", method="POST", body=body).get("result", {})


def upload_design_file(url):
    """Upload design via URL. Returns file_id."""
    return _request("/files", method="POST", body={"url": url}).get("result", {})


def order_tracking(order_id):
    """Get shipment tracking info for an order."""
    order = get_order(order_id)
    shipments = order.get("shipments", [])
    return [
        {
            "shipment_id": s.get("id"),
            "carrier": s.get("carrier"),
            "service": s.get("service"),
            "tracking_number": s.get("tracking_number"),
            "tracking_url": s.get("tracking_url"),
            "shipped_at": s.get("ship_date"),
        }
        for s in shipments
    ]
