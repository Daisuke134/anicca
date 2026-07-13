#!/usr/bin/env python3
"""Close the surplus tabs the apply loop leaves behind on the daily-driver.

Each 応募 opens a Coconala tab and nothing closes it. Fifteen-plus live tabs starved the machine
(free pages ~62MB, load average past 21) and Chromium died, which blinds the whole gig loop.
Keeping one Coconala tab alive preserves the session cookies the loop drives; everything past that
is garbage.

Deterministic bookkeeping only — which page to visit stays the agent's call.

    python3 cdp_tab_gc.py            # keep 1 coconala tab + 1 other, close the rest
    python3 cdp_tab_gc.py --keep 2   # keep 2 coconala tabs
"""
import json
import sys
import urllib.request

CDP = "http://127.0.0.1:9222"
KEEP_COCONALA = 2 if "--keep" in sys.argv and sys.argv[-1] == "2" else 1


def _get(path):
    return json.loads(urllib.request.urlopen(f"{CDP}{path}", timeout=8).read())


def main():
    try:
        tabs = _get("/json/list")
    except Exception as e:
        print(json.dumps({"ok": False, "reason": f"cdp_unreachable: {e}"}))
        return 0  # never crash the pass — the browser guard handles a dead browser

    pages = [t for t in tabs if t.get("type") == "page"]
    coconala = [t for t in pages if "coconala.com" in (t.get("url") or "")]
    blanks = [t for t in pages if (t.get("url") or "").startswith(("chrome://newtab", "about:blank"))]

    doomed = coconala[KEEP_COCONALA:] + blanks
    # keep at least one page alive so the browser never ends up with zero tabs
    if len(doomed) >= len(pages):
        doomed = doomed[1:]

    closed = 0
    for t in doomed:
        try:
            urllib.request.urlopen(f"{CDP}/json/close/{t['id']}", timeout=8).read()
            closed += 1
        except Exception:
            pass

    print(json.dumps({
        "ok": True, "pages_before": len(pages), "closed": closed,
        "pages_after": len(pages) - closed, "coconala_kept": min(len(coconala), KEEP_COCONALA),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
