#!/usr/bin/env python3
"""collect_metrics.py — pull the money truth into one daily row.

The loop cannot improve what it cannot read. Three sources, one line per run:

  RevenueCat v2  → mrr, active_subscriptions, active_trials, revenue_28d,
                   new_customers_28d, active_users_28d   (subscription truth)
  Stripe         → balance + payments in the window        (one-off product truth)
  App Store      → an analytics report request per app; Apple generates the data
                   asynchronously, so the request id is recorded and the reader
                   picks the report up on a later run     (install truth)

Nothing here converts an unavailable number into zero: a source that fails is
written as null with its error, because a fake zero would teach the loop a lie.

  collect_metrics.py [--state <path>] [--apps 6755129214,6759667221]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

STATE = pathlib.Path(os.path.expanduser(os.environ.get(
    "MKT_METRICS_STATE", "~/.openclaw/state/content-library/daily-metrics.jsonl")))
ENV_FILE = pathlib.Path(os.path.expanduser("~/.openclaw/.env"))


def load_env() -> dict[str, str]:
    env = dict(os.environ)
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(errors="replace").splitlines():
            if line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env.setdefault(k.strip(), v.strip())
    return env


def http_json(url: str, headers: dict, data: bytes | None = None, method: str = "GET"):
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def revenuecat(env) -> dict:
    key, project = env.get("RC_API_KEY"), env.get("REVENUECAT_PROJECT_ID")
    if not key or not project:
        return {"error": "RC_API_KEY or REVENUECAT_PROJECT_ID missing"}
    try:
        body = http_json(
            f"https://api.revenuecat.com/v2/projects/{project}/metrics/overview",
            {"Authorization": f"Bearer {key}"})
        return {m["id"]: m.get("value") for m in body.get("metrics", [])}
    except (urllib.error.URLError, KeyError, ValueError) as e:
        return {"error": str(e)[:200]}


def stripe(env, since_hours: int = 24) -> dict:
    key = env.get("STRIPE_SECRET_KEY")
    if not key:
        return {"error": "STRIPE_SECRET_KEY missing"}
    import base64
    auth = base64.b64encode(f"{key}:".encode()).decode()
    headers = {"Authorization": f"Basic {auth}"}
    since = int(time.time()) - since_hours * 3600
    out = {}
    try:
        bal = http_json("https://api.stripe.com/v1/balance", headers)
        out["balance"] = [{"currency": b["currency"], "amount": b["amount"]}
                          for b in bal.get("available", [])]
        pay = http_json(
            "https://api.stripe.com/v1/payment_intents?"
            + urllib.parse.urlencode({"created[gte]": since, "limit": 100}), headers)
        paid = [p for p in pay.get("data", []) if p.get("status") == "succeeded"]
        out["succeeded_payments_24h"] = len(paid)
        out["gross_24h"] = {}
        for p in paid:
            cur = p.get("currency", "?")
            out["gross_24h"][cur] = out["gross_24h"].get(cur, 0) + p.get("amount", 0)
    except (urllib.error.URLError, ValueError) as e:
        out["error"] = str(e)[:200]
    return out


def asc_token(env) -> str:
    import jwt  # PyJWT is present on this machine; a missing import is a real failure
    now = int(time.time())
    return jwt.encode(
        {"iss": env["ASC_ISSUER_ID"], "iat": now, "exp": now + 900,
         "aud": "appstoreconnect-v1"},
        pathlib.Path(env["ASC_KEY_PATH"]).read_text(),
        algorithm="ES256", headers={"kid": env["ASC_KEY_ID"], "typ": "JWT"})


def app_store(env, app_ids: list[str]) -> dict:
    """Ask Apple for an analytics snapshot per app and record what came back.

    Apple builds these reports asynchronously, so a fresh request yields an id and
    the numbers land on a later run. Existing requests are reused rather than
    piling up one request per day.
    """
    try:
        headers = {"Authorization": f"Bearer {asc_token(env)}",
                   "Content-Type": "application/json"}
    except (KeyError, ImportError, OSError) as e:
        return {"error": f"asc auth unavailable: {str(e)[:120]}"}

    out = {}
    for app_id in app_ids:
        entry = {}
        try:
            existing = http_json(
                f"https://api.appstoreconnect.apple.com/v1/apps/{app_id}"
                f"/analyticsReportRequests?limit=10", headers)
            reqs = existing.get("data", [])
            if reqs:
                entry["request_id"] = reqs[0]["id"]
                entry["stopped_due_to_inactivity"] = \
                    reqs[0]["attributes"].get("stoppedDueToInactivity")
            else:
                created = http_json(
                    "https://api.appstoreconnect.apple.com/v1/analyticsReportRequests",
                    headers,
                    data=json.dumps({"data": {
                        "type": "analyticsReportRequests",
                        "attributes": {"accessType": "ONE_TIME_SNAPSHOT"},
                        "relationships": {"app": {"data": {"type": "apps", "id": app_id}}}}}
                    ).encode(),
                    method="POST")
                entry["request_id"] = created["data"]["id"]
                entry["created_now"] = True

            reports = http_json(
                "https://api.appstoreconnect.apple.com/v1/analyticsReportRequests/"
                f"{entry['request_id']}/reports?limit=50", headers)
            entry["reports_available"] = len(reports.get("data", []))
        except (urllib.error.HTTPError, urllib.error.URLError, KeyError, ValueError) as e:
            entry["error"] = str(e)[:160]
        out[app_id] = entry
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--state", default=str(STATE))
    ap.add_argument("--apps", default="6755129214,6759667221",
                    help="App Store ids: Anicca iOS, Honne")
    a = ap.parse_args()

    env = load_env()
    row = {
        "ts": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "revenuecat": revenuecat(env),
        "stripe": stripe(env),
        "app_store": app_store(env, [x for x in a.apps.split(",") if x]),
    }

    path = pathlib.Path(os.path.expanduser(a.state))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

    rc = row["revenuecat"]
    print(f"METRICS mrr={rc.get('mrr')} subs={rc.get('active_subscriptions')} "
          f"trials={rc.get('active_trials')} new_customers_28d={rc.get('new_customers')} "
          f"stripe_payments_24h={row['stripe'].get('succeeded_payments_24h')} -> {path}")

    # A run that reached no source at all is a failure, not a quiet success.
    failed = [k for k in ("revenuecat", "stripe") if row[k].get("error")]
    if len(failed) == 2:
        print(f"FATAL: every money source failed: {failed}", file=sys.stderr)
        return 1
    if failed:
        print(f"WARN: source failed: {failed}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
