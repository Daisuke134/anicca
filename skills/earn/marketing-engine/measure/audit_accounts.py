#!/usr/bin/env python3
"""audit_accounts.py — prove every posting target still exists.

Discovered 2026-07-31: the TikTok account behind the "Anicca" Postiz integration
(@aniccaen2) no longer exists, yet a launchd job kept posting to it for at least ten
days — Postiz reported half the attempts as ERROR and the other half as PUBLISHED with
only a profile URL, so every English larry post went nowhere and nothing said so.

This walks the configured integrations and asks the platform whether each handle is
real, then writes the verdict and alerts on any dead target.

  audit_accounts.py [--platform tiktok] [--dry-run] [--no-alert]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import urllib.request

STATE = pathlib.Path(os.path.expanduser(os.environ.get(
    "MKT_ACCOUNT_AUDIT_STATE",
    "~/.openclaw/state/content-library/account-audit.jsonl")))
ENV_FILE = pathlib.Path(os.path.expanduser("~/.openclaw/.env"))
TELEGRAM_TARGET = os.environ.get("MKT_TELEGRAM_TARGET", "8547730585")


def load_env() -> dict:
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
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read().decode(errors="replace"), strict=False)


def integrations(env) -> list[dict]:
    key = env.get("POSTIZ_API_KEY")
    if not key:
        raise SystemExit("FATAL: POSTIZ_API_KEY missing")
    return http_json("https://api.postiz.com/public/v1/integrations",
                     {"Authorization": key})


def check_tiktok(env, handles: list[str]) -> dict[str, dict]:
    """One Apify run for every handle; a handle that returns an error object is dead."""
    token = env.get("APIFY_API_TOKEN")
    if not token:
        raise SystemExit("FATAL: APIFY_API_TOKEN missing")
    items = http_json(
        "https://api.apify.com/v2/acts/clockworks~tiktok-scraper/"
        f"run-sync-get-dataset-items?token={token}&timeout=900",
        {"Content-Type": "application/json"},
        data=json.dumps({"profiles": handles, "resultsPerPage": 1,
                         "shouldDownloadVideos": False,
                         "shouldDownloadCovers": False}).encode(),
        method="POST")

    verdict = {h: {"alive": False, "reason": "no data returned"} for h in handles}
    for item in items:
        if item.get("error"):
            handle = (item.get("input") or item.get("url", "").split("@")[-1]).strip()
            verdict[handle] = {"alive": False, "reason": item["error"]}
            continue
        author = item.get("authorMeta") or {}
        handle = author.get("name") or author.get("nickName")
        if handle in verdict:
            verdict[handle] = {"alive": True, "reason": "profile returned videos",
                               "latest_views": item.get("playCount")}
    return verdict


def send(message: str) -> bool:
    r = subprocess.run(
        ["openclaw", "message", "send", "--channel", "telegram",
         "--target", TELEGRAM_TARGET, "--message", message, "--json"],
        capture_output=True, text=True, timeout=120)
    return r.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--platform", default="tiktok", choices=["tiktok"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-alert", action="store_true")
    a = ap.parse_args()

    env = load_env()
    rows = [i for i in integrations(env)
            if i.get("identifier") == a.platform and not i.get("disabled")]
    handles = sorted({i["profile"] for i in rows if i.get("profile")})
    print(f"{a.platform} integrations enabled: {len(rows)} handles: {len(handles)}")

    verdict = check_tiktok(env, handles)
    dead = [h for h, v in verdict.items() if not v["alive"]]
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for h in handles:
        v = verdict[h]
        mark = "alive" if v["alive"] else "DEAD"
        extra = f" views={v.get('latest_views')}" if v["alive"] else f" — {v['reason']}"
        print(f"  @{h}: {mark}{extra}")

    if not a.dry_run:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE, "a") as f:
            for h in handles:
                f.write(json.dumps({"ts": now, "platform": a.platform, "handle": h,
                                    **verdict[h]}, ensure_ascii=False) + "\n")

    if dead:
        names = {i["profile"]: i.get("name") for i in rows}
        lines = [f"⚠️ posting targets that no longer exist ({a.platform})"]
        lines += [f"@{h} (integration \"{names.get(h)}\")" for h in sorted(dead)]
        lines.append("Every post scheduled to these is lost. Repoint or re-provision.")
        msg = "\n".join(lines)
        print(msg)
        if not a.dry_run and not a.no_alert:
            send(msg)
        return 1
    print("all posting targets exist")
    return 0


if __name__ == "__main__":
    sys.exit(main())
