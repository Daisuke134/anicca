# launch_promote_browser.py — dedicated CloakBrowser instance for the promote.fun
# clip-promote account. Port is read from CLIP_PROMOTE_CDP_PORT (default 9226) --
# was hardcoded to 9224, but 2026-07-11 found that port permanently squatted by an
# unrelated clip-en2 Instagram Chromium instance (a real port collision, not this
# script's own doing), so promote.fun's SELECT step could never find its tab.
# Moved to 9226 (verified free) rather than fight another loop's live browser for
# 9224. 9222 is Dais's daily-driver (never touch), 9223/9224 are IG accounts.
# Idempotent to re-run — if a process is already bound to the port, this one will
# simply fail to bind; check with `curl localhost:$CLIP_PROMOTE_CDP_PORT/json/list`
# before launching a second instance.
#
# headless=True (2026-07-12, was False): headed launches were crashing reproducibly
# on this machine (playwright's own launch_persistent_context self-killed the process
# right after DevTools bound, "TargetClosedError: Target page, context or browser has
# been closed") whenever many other Chromium windows were already open (daily-driver,
# warmup profiles, IG accounts). Isolated live: the identical launch with headless=True
# succeeded and navigated to promote.fun cleanly under the same load. This browser is
# 100% scripted CDP automation (join_campaign.py / select_campaigns.py) -- no human ever
# looks at the window, so headless carries no functional cost, only removes the crash.
import os, sys, time
sys.path.insert(0, "/Users/anicca/.openclaw/skills/_shared/venv-cloak/lib/python3.14/site-packages")
from cloakbrowser import launch_persistent_context
port = os.environ.get("CLIP_PROMOTE_CDP_PORT", "9226")
ctx = launch_persistent_context(
    "/Users/anicca/.cloak/profiles/promote-fun",
    headless=True,
    args=[f"--remote-debugging-port={port}", "--remote-allow-origins=*"],
)
pg = ctx.new_page()
pg.goto("https://www.promote.fun/")
print(f"PROMOTE BROWSER UP on :{port}")
while True:
    time.sleep(60)
