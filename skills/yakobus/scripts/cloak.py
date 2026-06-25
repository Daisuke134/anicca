#!/usr/bin/env python3
"""cloak.py — single-client CDP driver for the live daily-driver CloakBrowser (port 9222).

VERIFIED 2026-06-25 driving a real kosokubus booking end-to-end.

CRITICAL rules (learned the hard way — see spec 2026-06-25-best-overnight-bus-booking-skill.md §5):
  * EXACTLY ONE playwright client may attach at a time. A second concurrent client + a JS dialog
    => both auto-dismiss => ProtocolError => the browser process dies. So: do NOT also run a
    launch_persistent_context keepalive while using this; keep the Cloak Chromium alive as a
    standalone process (binary + --remote-debugging-port=9222).
  * ALWAYS register page.on("dialog", accept) so a confirm()/alert() never blocks/crashes the driver.
  * NEVER call browser.close() on a CDP-attached daily-driver (it can take the whole browser down).
  * The daily-driver has MANY tabs from other sessions — target the working page by URL substring
    via CLOAK_TARGET env (or the kosokubus default), never "the last tab".

Usage: cloak.py <cmd> [arg]   (JS for `eval` is read from stdin)
  goto <url> | goto-wait <url> | url | pages | newtab
  eval            (stdin = JS, prints JSON)
  shot <name> | shotfull <name>
  clicktext <text> | clicksel <css> | clickxy "x,y"
  typeat "x,y||text"  | fill "css||value"
Env: CLOAK_TARGET = URL substring of the page to drive (e.g. "kosokubus.com").
"""
import sys, json, os, re, fcntl
from playwright.sync_api import sync_playwright

SHOT_DIR = os.environ.get("CLOAK_SHOT_DIR", "/tmp")
CDP = os.environ.get("CLOAK_CDP", "http://localhost:9222")
NAVCMDS = ("goto", "goto-wait", "newtab")

def pick_page(ctx, cmd):
    target = os.environ.get("CLOAK_TARGET", "")
    if target:
        for pg in ctx.pages:
            if target in (pg.url or ""):
                return pg
        # target set but not open: only OK to open a fresh tab for nav cmds; otherwise REFUSE
        # (never silently drive an arbitrary tab — risk of typing card data into the wrong site).
        if cmd in NAVCMDS:
            return ctx.new_page()
        raise SystemExit(f"CLOAK_TARGET '{target}' not open and cmd '{cmd}' won't navigate — refusing to drive an arbitrary tab")
    page = None
    for pg in ctx.pages:
        if pg.url and pg.url != "about:blank":
            page = pg
    if cmd == "newtab" or page is None:
        page = ctx.new_page()
    return page

def acquire_cdp_lock():
    # ONE CDP client at a time (2nd client + a JS dialog = browser crash). Shared with search_buses.py.
    lf = open("/tmp/yakobus-cdp.lock", "w")
    try:
        fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("another yakobus CDP client holds /tmp/yakobus-cdp.lock — run search/cloak strictly sequentially")
    return lf  # keep open for process lifetime; released on exit

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "url"
    arg = sys.argv[2] if len(sys.argv) > 2 else ""
    _lock = acquire_cdp_lock()
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0]
        # accept dialogs on EVERY tab (a dialog on any page crashes a 2nd client) — register
        # context-wide BEFORE navigating; do not silently swallow the registration itself.
        def _accept(d):
            try: d.accept()
            except Exception: pass
        ctx.on("page", lambda pg: pg.on("dialog", _accept))
        for pg in ctx.pages:
            pg.on("dialog", _accept)
        page = pick_page(ctx, cmd)

        if cmd in ("goto", "goto-wait"):
            wait = "networkidle" if cmd == "goto-wait" else "domcontentloaded"
            page.goto(arg, wait_until=wait, timeout=90000)
            page.wait_for_timeout(3000)
            print("URL:", page.url)
        elif cmd == "eval":
            out = json.dumps(page.evaluate(sys.stdin.read()), ensure_ascii=False, default=str)[:60000]
            # redact card PANs only (card-shaped runs) — avoid over-redacting "1 2 3 .." numeric lists:
            out = re.sub(r"\b(?:\d{4}[ \-]){3}\d{1,4}\b", "<redacted-card>", out)  # 4-4-4-4 grouped
            out = re.sub(r"\b\d{13,19}\b", "<redacted-card>", out)                 # bare 13-19 digit PAN
            print(out)
        elif cmd == "url":
            print("URL:", page.url, "| TITLE:", page.title())
        elif cmd == "pages":
            for i, pg in enumerate(ctx.pages):
                print(i, pg.url)
        elif cmd in ("shot", "shotfull"):
            path = f"{SHOT_DIR}/{arg or cmd}.png"
            page.screenshot(path=path, full_page=(cmd == "shotfull"))
            print("SHOT:", path, "| URL:", page.url)
        elif cmd == "clicktext":
            el = page.locator(f"text={arg}").first
            el.scroll_into_view_if_needed(timeout=8000); el.click(timeout=8000)
            page.wait_for_timeout(3500); print("CLICKED:", arg, "| URL:", page.url)
        elif cmd == "clicksel":
            el = page.locator(arg).first
            el.scroll_into_view_if_needed(timeout=8000); el.click(timeout=8000)
            page.wait_for_timeout(3500); print("CLICKED sel:", arg, "| URL:", page.url)
        elif cmd == "clickxy":
            x, y = arg.split(","); page.mouse.click(float(x), float(y))
            page.wait_for_timeout(2000); print("CLICKED xy:", arg, "| URL:", page.url)
        elif cmd == "typeat":
            xy, text = arg.split("||", 1); x, y = xy.split(",")
            if text.strip() == "@env":               # secret-safe path: value from env, never argv
                text = os.environ.get("CLOAK_FILL_VALUE", ""); shown = "<env-secret>"
            elif re.fullmatch(r"\d{3,}", text.replace(" ", "").replace("-", "")):
                # any pure-digit run (CVV 3-4, OTP, PAN 13-19) must NOT pass through argv → use fill/@env
                raise SystemExit("typeat refuses pure-digit strings (CVV/PAN/OTP) in argv — use `fill` or `@env` (CLOAK_FILL_VALUE)")
            else:
                shown = text
            page.mouse.click(float(x), float(y)); page.wait_for_timeout(400)
            page.keyboard.press("ControlOrMeta+a"); page.keyboard.press("Delete")
            page.keyboard.type(text, delay=60); page.wait_for_timeout(300)
            page.keyboard.press("Enter"); page.wait_for_timeout(2500); print("TYPED:", shown, "| URL:", page.url)
        elif cmd == "fill":
            # SECRET-SAFE: value comes from env CLOAK_FILL_VALUE, never argv (argv shows in `ps`/transcript).
            sel = arg
            val = os.environ.get("CLOAK_FILL_VALUE", "")
            if not val:   # never fake-success on an unset/empty env (would submit a blank card field)
                raise SystemExit("CLOAK_FILL_VALUE empty/unset — refusing to fill (no fake success)")
            page.locator(sel).first.fill(val, timeout=8000)
            print("FILLED:", sel, "(value via env, masked)")
        # NOTE: never browser.close() — CDP detach happens automatically on context exit.

if __name__ == "__main__":
    main()
