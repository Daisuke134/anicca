# launch_affiliate_browser.py — dedicated CloakBrowser instance for the affiliate
# earn-core's Instagram account (@aishigoto.labo). Port 9225 is deliberately NEW:
# 9222 is Dais's daily-driver (never touch), 9223 is clip-en, 9224 is promote-fun.
# Root cause fix for the chronic tab-contention collision documented in
# state/lessons.jsonl (2026-07-08, 2026-07-10): run.sh was sharing :9222 with the
# affirmation-app loop, so whichever loop logged in last won the tab and the other
# fail-closed-skipped forever. Reuses the existing profile
# ~/.cloak/profiles/aishigoto-labo (already has this account's session history).
# Idempotent to re-run — if a process is already bound to 9225, this one will
# simply fail to bind; check with `curl localhost:9225/json/list` first.
import sys, time
sys.path.insert(0, "/Users/anicca/.openclaw/skills/_shared/venv-cloak/lib/python3.14/site-packages")
from cloakbrowser import launch_persistent_context
ctx = launch_persistent_context(
    "/Users/anicca/.cloak/profiles/aishigoto-labo",
    headless=False,
    args=["--remote-debugging-port=9225", "--remote-allow-origins=*"],
)
pg = ctx.new_page()
pg.goto("https://www.instagram.com/")
print("AFFILIATE BROWSER UP on :9225")
while True:
    time.sleep(60)
