#!/usr/bin/env python3
"""Run the isolated Affiliate EN CloakBrowser owned by launchd."""

import os
import time
from pathlib import Path

from cloakbrowser import launch_persistent_context


profile = Path(os.environ.get("AFFILIATE_BROWSER_PROFILE", "~/.cloak/profiles/affiliate/en")).expanduser()
port = int(os.environ.get("AFFILIATE_CDP_PORT", "9324"))
profile.mkdir(mode=0o700, parents=True, exist_ok=True)
context = launch_persistent_context(
    str(profile), headless=False,
    args=[f"--remote-debugging-port={port}", "--remote-allow-origins=*"],
)
if not context.pages:
    context.new_page().goto("https://x.com/home")
while True:
    time.sleep(60)
