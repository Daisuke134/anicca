import os, sys, json, time

# Launch a CloakBrowser instance whose ENTIRE traffic egresses through the account's assigned
# residential proxy (the clean, non-datacenter exit IP is the #1 anti-ban lever). Unlike
# launch_clip_browser.py (which uses the burned daily-driver IP), this routes signup + all browser
# work through geo.iproyal.com so a fresh IG account is BORN on a clean residential IP.
#
#   CDP_PORT=9230 CLOAK_PROFILE_PATH=~/.cloak/profiles/clip-proxy-1 \
#   PROXY_FILE=~/.cloak/proxy-clip-1.json python3 launch_proxy_browser.py
#
# The proxy password is read from PROXY_FILE and handed to CloakBrowser's native proxy support;
# it is never printed.

sys.path.insert(0, os.environ.get(
    "VENV_CLOAK_SITE_PACKAGES",
    "/Users/operator/.openclaw/skills/_shared/venv-cloak/lib/python3.14/site-packages",
))
from cloakbrowser import launch_persistent_context

profile_path = os.environ.get("CLOAK_PROFILE_PATH", "/Users/operator/.cloak/profiles/clip-proxy-1")
cdp_port = os.environ.get("CDP_PORT", "9230")
proxy_file = os.path.expanduser(os.environ.get("PROXY_FILE", "~/.cloak/proxy-clip-1.json"))

d = json.load(open(proxy_file))
proxy = {
    "server": f"http://{d['host']}:{d['port']}",
    "username": d["username"],
    "password": d["password"],
}

ctx = launch_persistent_context(
    profile_path,
    headless=False,
    proxy=proxy,
    args=[f"--remote-debugging-port={cdp_port}", "--remote-allow-origins=*"],
)
pg = ctx.new_page()
# prove the exit IP before anything else touches Instagram
pg.goto("https://api.ipify.org?format=json", wait_until="domcontentloaded", timeout=60000)
print(f"PROXY BROWSER UP on :{cdp_port} — exit check: {pg.content()[:200]}", flush=True)
pg.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=60000)
print(f"instagram.com loaded through residential proxy", flush=True)
while True:
    time.sleep(60)
