import sys, time
sys.path.insert(0, "/Users/anicca/.openclaw/skills/_shared/venv-cloak/lib/python3.14/site-packages")
from cloakbrowser import launch_persistent_context
ctx = launch_persistent_context(
    "/Users/anicca/.cloak/profiles/clip-en",
    headless=False,
    args=["--remote-debugging-port=9223", "--remote-allow-origins=*"],
)
# open a first tab so the instance has a page
pg = ctx.new_page()
pg.goto("https://www.instagram.com/")
print("CLIP BROWSER UP on :9223")
# keep alive
while True:
    time.sleep(60)
