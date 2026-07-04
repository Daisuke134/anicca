import sys, time
sys.path.insert(0, "/Users/anicca/.openclaw/skills/_shared/venv-cloak/lib/python3.14/site-packages")
from cloakbrowser import launch_persistent_context
ctx = launch_persistent_context(
    "/Users/anicca/.cloak/profiles/promote-fun",
    headless=False,
    args=["--remote-debugging-port=9224", "--remote-allow-origins=*"],
)
pg = ctx.new_page()
pg.goto("https://www.promote.fun/")
print("PROMOTE BROWSER UP on :9224")
while True:
    time.sleep(60)
