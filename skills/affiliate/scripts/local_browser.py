#!/usr/bin/env python3
"""Run the isolated Affiliate EN CloakBrowser owned by launchd."""

import os
import time
from pathlib import Path

from cloakbrowser import launch_persistent_context


profile = Path(os.environ.get("AFFILIATE_BROWSER_PROFILE", "~/.cloak/profiles/affiliate/en")).expanduser()
port = int(os.environ.get("AFFILIATE_CDP_PORT", "9324"))
start_url = os.environ.get("AFFILIATE_START_URL", "https://elevenlabs.io/app/home")
profile.mkdir(mode=0o700, parents=True, exist_ok=True)
context = launch_persistent_context(
    str(profile), headless=False,
    args=[f"--remote-debugging-port={port}", "--remote-allow-origins=*"],
)
pages = context.pages
page = pages[0] if pages else context.new_page()
if page.url == "about:blank":
    page.goto(start_url, wait_until="domcontentloaded", timeout=30_000)
while True:
    time.sleep(60)
