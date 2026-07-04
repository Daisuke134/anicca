import os, sys, time
sys.path.insert(0, os.environ.get(
    "VENV_CLOAK_SITE_PACKAGES",
    "/Users/anicca/.openclaw/skills/_shared/venv-cloak/lib/python3.14/site-packages",
))
from cloakbrowser import launch_persistent_context
profile_path = os.environ.get("CLOAK_PROFILE_PATH", "/Users/anicca/.cloak/profiles/clip-en")
cdp_port = os.environ.get("CDP_PORT", "9223")
ctx = launch_persistent_context(
    profile_path,
    headless=False,
    args=[f"--remote-debugging-port={cdp_port}", "--remote-allow-origins=*"],
)
# open a first tab so the instance has a page
pg = ctx.new_page()
pg.goto("https://www.instagram.com/")
print(f"CLIP BROWSER UP on :{cdp_port}")
# keep alive
while True:
    time.sleep(60)
