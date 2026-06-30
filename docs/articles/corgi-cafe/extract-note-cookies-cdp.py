#!/usr/bin/env python3
"""Extract note.com cookies from the live CloakBrowser daily-driver via CDP
(instead of reading the locked sqlite file). Writes the same format as the
skill's extract-note-cookies.py so downstream scripts work unchanged."""
import json, pathlib
from playwright.sync_api import sync_playwright

OUT = pathlib.Path.home() / ".cloak/note-work/note-cookies.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    cookies = ctx.cookies("https://note.com")
    out = {c["name"]: c["value"] for c in cookies}
    OUT.write_text(json.dumps(out))
    print(f"extracted {len(out)} note.com cookies -> {OUT}")
    print("keys:", ",".join(sorted(out.keys()))[:200])
