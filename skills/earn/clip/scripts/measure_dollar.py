#!/usr/bin/env python3
"""measure_dollar.py — MEASURE-$ standalone step: read Digistore24 affiliate sales for the
clip-loop offer (~/clips/offer.json, sid1-attributed) and append ONE dollar-metric line to
~/clips/clip-metrics.jsonl, alongside the view/like lines the MEASURE step in clip_pass.sh
already writes there (same file, disambiguated by "type":"dollar").

API reference (fetched via crwl/curl 2026-07-16, no WebFetch/WebSearch used per policy):
  https://dev.digistore24.com/hc/en-us/sections/32544342993169-API (API basics + reference)
  https://digistore24.com/api/docs/openapi.yaml (machine-readable spec)
  https://digistore24.com/api/docs/paths/listPurchases.yaml
Auth: header "X-DS-API-KEY: <key>" (openapi.yaml components.securitySchemes.ApiKeyAuth,
type=apiKey, in=header, name=X-DS-API-KEY). Base URL: https://www.digistore24.com/api/call.
listPurchases (GET /listPurchases) is the only documented endpoint whose response items carry
sub_ids.sid1-5 (per-affiliate-link attribution, matching offer.json's own sub_id_scheme note);
listTransactions has a cleanly-typed `amount` field but NO sid fields. load_transactions=true
on listPurchases embeds each purchase's transaction_list (payment/refund/chargeback rows with
amount+currency), which is the only way to get BOTH sid1 and $ amount in one call. The doc site
does not fully spell out the embedded transaction_list item shape, so parsing below is
defensive: it tries several plausible amount/currency key names rather than assuming one.

stdout: ONE compact JSON line (loop child-script contract, matches bio_step.py). stderr: detail.
Exit code is ALWAYS 0 (missing key / API error / etc. all report via outcome, never crash the
caller) — this script's whole job is to be safe to run even before a key exists.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

C = os.path.expanduser
ENV_PATH = C("~/.local/state/life-manager/.env")
OFFER_PATH = C("~/clips/offer.json")
METRICS_PATH = C("~/clips/clip-metrics.jsonl")
API_BASE = "https://www.digistore24.com/api/call"
KEY_ENV_NAMES = ("DIGISTORE24_API_KEY", "DS24_API_KEY", "DIGISTORE_API_KEY")


def find_api_key():
    """Env var first (already-sourced shell/loop context), else parse ~/.local/state/life-manager/.env
    directly so this script also works standalone (not yet wired into clip_pass.sh)."""
    for name in KEY_ENV_NAMES:
        v = os.environ.get(name)
        if v:
            return v.strip()
    try:
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                if line.startswith("export "):
                    line = line[len("export "):]
                k, _, v = line.partition("=")
                if k.strip() in KEY_ENV_NAMES:
                    v = v.strip().strip('"').strip("'")
                    if v:
                        return v
    except FileNotFoundError:
        pass
    return None


def load_offer():
    with open(OFFER_PATH) as f:
        return json.load(f)


def api_get(path, key, params):
    url = f"{API_BASE}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"X-DS-API-KEY": key, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def first_amount(d, keys):
    for k in keys:
        v = d.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def extract_purchase_list(payload):
    # response envelope isn't consistently documented (some DS24 endpoints wrap in "data",
    # some don't) -- try both so a shape change doesn't silently zero out results.
    if isinstance(payload, dict):
        if isinstance(payload.get("purchase_list"), list):
            return payload["purchase_list"]
        data = payload.get("data")
        if isinstance(data, dict) and isinstance(data.get("purchase_list"), list):
            return data["purchase_list"]
    return []


def sum_sales_for_sid1(purchase_list, sid1_wanted):
    sales = 0
    revenue_usd = 0.0
    non_usd_skipped = 0
    for p in purchase_list:
        sub_ids = p.get("sub_ids") or {}
        if sub_ids.get("sid1") != sid1_wanted:
            continue
        txns = p.get("transaction_list") or p.get("transactions") or []
        if txns:
            for t in txns:
                if t.get("transaction_type") not in (None, "payment"):
                    continue  # skip refund/chargeback rows from the revenue sum
                amt = first_amount(t, ("amount", "earning", "net_amount", "commission_amount"))
                currency = t.get("currency") or "USD"
                if amt is None:
                    continue
                if currency != "USD":
                    non_usd_skipped += 1
                    continue
                sales += 1
                revenue_usd += amt
        else:
            # no embedded transactions -- fall back to whatever amount-like field the
            # purchase object itself carries.
            amt = first_amount(p, ("earning", "amount", "net_amount", "commission_amount"))
            currency = p.get("currency") or "USD"
            if amt is None:
                continue
            if currency != "USD":
                non_usd_skipped += 1
                continue
            sales += 1
            revenue_usd += amt
    return sales, round(revenue_usd, 2), non_usd_skipped


def today_dollar_line_exists(handle):
    today = time.strftime("%Y-%m-%d", time.gmtime())
    try:
        with open(METRICS_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("type") != "dollar" or d.get("handle") != handle:
                    continue
                ts = d.get("ts")
                if isinstance(ts, (int, float)) and time.strftime("%Y-%m-%d", time.gmtime(ts)) == today:
                    return True
    except FileNotFoundError:
        pass
    return False


def append_dollar_line(handle, sales, revenue_usd):
    line = {"ts": int(time.time()), "type": "dollar", "handle": handle, "sales": sales, "revenue_usd": revenue_usd}
    with open(METRICS_PATH, "a") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", default="aiclipsvault", help="sid1 value to attribute sales to")
    a = ap.parse_args()
    handle = a.handle

    key = find_api_key()
    if not key:
        res = {
            "outcome": "skip",
            "reason": (
                "no api key: set one of DIGISTORE24_API_KEY / DS24_API_KEY / DIGISTORE_API_KEY "
                "in ~/.local/state/life-manager/.env (generate via Digistore24 account -> Settings -> API, "
                "see https://dev.digistore24.com/hc/en-us/articles/32479630493585-API-basics), "
                "then re-run this script"
            ),
        }
        print(json.dumps(res, ensure_ascii=False))
        return

    try:
        offer = load_offer()
    except Exception as e:
        print(json.dumps({"outcome": "skip", "reason": f"offer.json unreadable: {type(e).__name__}"}, ensure_ascii=False))
        return

    product_id = offer.get("product_id")
    params = {
        "from": "-30d",
        "to": "now",
        "load_transactions": "true",
        "page_size": "1000",
        "page_no": "1",
    }
    if product_id:
        params["search"] = json.dumps({"product_id": str(product_id), "role": "affiliate"})
    else:
        params["search"] = json.dumps({"role": "affiliate"})

    try:
        payload = api_get("/listPurchases", key, params)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass
        print(json.dumps({"outcome": "error", "reason": f"HTTP {e.code}: {body}"}, ensure_ascii=False))
        print(f"measure_dollar: HTTPError {e.code} {body}", file=sys.stderr)
        return
    except Exception as e:
        print(json.dumps({"outcome": "error", "reason": f"{type(e).__name__}: {str(e)[:200]}"}, ensure_ascii=False))
        print(f"measure_dollar: request failed: {type(e).__name__}: {e}", file=sys.stderr)
        return

    purchase_list = extract_purchase_list(payload)
    sales, revenue_usd, non_usd_skipped = sum_sales_for_sid1(purchase_list, handle)
    if non_usd_skipped:
        print(f"measure_dollar: skipped {non_usd_skipped} non-USD transaction(s) from revenue_usd sum", file=sys.stderr)

    if today_dollar_line_exists(handle):
        res = {
            "outcome": "noop",
            "reason": "dollar entry already exists for today",
            "handle": handle,
            "sales": sales,
            "revenue_usd": revenue_usd,
        }
        print(json.dumps(res, ensure_ascii=False))
        return

    written = append_dollar_line(handle, sales, revenue_usd)
    res = {
        "outcome": "ok",
        "handle": handle,
        "sales": sales,
        "revenue_usd": revenue_usd,
        "epc_note": "revenue_usd = affiliate commission (USD-only txns) over trailing 30d, sid1-attributed; EPC needs bio-link click count, not tracked yet",
        "written": written,
    }
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
