#!/usr/bin/env python3
"""search_buses.py — scrape バス比較なび (bushikaku.net) for overnight-bus candidates.

VERIFIED 2026-06-25 against osaka_tokyo / kyoto_tokyo for date 20260625.
Returns RAW structured candidates for the AGENT to judge "best" — this script makes NO best-pick
decision (per ~/.claude/rules/building-effective-ai-agents.md: judgment belongs to the model).

Usage: search_buses.py <from_slug> <to_slug> <YYYYMMDD>
  e.g. search_buses.py osaka tokyo 20260625
Slugs are bushikaku route slugs (osaka, kyoto, nara, tokyo, ...). Uses the live CloakBrowser (CDP 9222)
because the result list is JS-rendered. Prints JSON: {candidates:[...], note}.

CAVEAT (verified): bushikaku availability is CACHED/laggy — a plan shown as "わずか" may be 満席 on the
booking site. Treat availability as a hint; confirm on the booking site before relying on it.
"""
import sys, json, re, fcntl
from playwright.sync_api import sync_playwright

CDP = "http://localhost:9222"
# lines to skip when back-scanning for the plan name (seat-type chips, ratings, prices, times)
SKIP = {"夜行便","昼行便","充電","Wi-Fi","女性安心","女性専用席","トイレ付","仕切りカーテン",
        "3列独立","4列標準","4列足元広め","座席指定","2列","2列独立","3列シート","4列"}
PREF_MARK = re.compile(r"^[（(].+[）)]$")     # full- OR half-width "（大阪）"/"(大阪)" marker on its own line
NOISE = re.compile(r"^(¥?[\d,]+円?|\d{1,2}:\d{2}|★+|[\d.]+)$")  # price / time / rating noise
LABELISH = re.compile(r"(着$|発$|^\d{1,2}:\d{2}|乗車|降車|予約サイト|バス会社|時間)")  # not a place name

def parse(txt):
    lines = [l.strip() for l in txt.split("\n")]
    idx = [i for i, l in enumerate(lines) if l.startswith("予約サイト")]
    out = []
    for n, i in enumerate(idx):
        end = idx[n+1] if n+1 < len(idx) else len(lines)
        name = ""
        for j in range(i-1, max(i-9, -1), -1):
            l = lines[j]
            if l and l not in SKIP and not NOISE.match(l) and not PREF_MARK.match(l):
                name = l; break
        blk_lines = lines[i:end]
        blk = "\n".join(blk_lines)
        price = re.search(r"¥([\d,]+)", blk)
        price = int(price.group(1).replace(",", "")) if price else None
        # GENERAL stop extraction: the place name is the line right AFTER a （都道府県） marker.
        stops = []
        for k, l in enumerate(blk_lines[:-1]):
            if PREF_MARK.match(l):
                place = blk_lines[k+1].strip()
                if (place and place not in stops and place not in SKIP
                        and not NOISE.match(place) and not LABELISH.search(place)):
                    stops.append(place[:40])
        st = "満席" if "満席" in blk else ("わずか" if "わずか" in blk else "空席")
        times = re.findall(r"\d{1,2}:\d{2}", blk)
        out.append({"name": name[:60], "price": price, "stops": stops,
                    "availability": st, "times": times[:8]})
    return out

def main():
    frm, to, ymd = sys.argv[1], sys.argv[2], sys.argv[3]
    url = f"https://www.bushikaku.net/search/{frm}_{to}/{ymd}/"
    _lf = open("/tmp/yakobus-cdp.lock", "w")   # ONE CDP client at a time (shared with cloak.py)
    try:
        fcntl.flock(_lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(json.dumps({"error": "another yakobus CDP client holds the lock — run sequentially"})); sys.exit(1)
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP); ctx = b.contexts[0]
        pg = ctx.new_page(); pg.on("dialog", lambda d: d.accept())
        pg.goto(url, wait_until="domcontentloaded", timeout=90000); pg.wait_for_timeout(3500)
        txt = pg.evaluate("()=>{const t=document.body.innerText;const i=t.indexOf('並び替え');return t.slice(i>0?i:0,(i>0?i:0)+16000);}")
        links = pg.evaluate("""()=>[...document.querySelectorAll('a[href]')].filter(a=>/external_link|booking\\/select/.test(a.href)).map(a=>({t:(a.textContent||'').replace(/\\s+/g,' ').trim().slice(0,40),h:a.href})).slice(0,60)""")
        try: pg.close()  # close our own tab (no browser.close()) to avoid tab leak on daily-driver
        except Exception: pass
    cands = parse(txt)
    if not cands:
        print(json.dumps({"error": "no candidates parsed", "route": f"{frm}->{to}", "date": ymd,
                          "url": url, "hint": "route slug/date wrong, or page layout changed"}, ensure_ascii=False))
        sys.exit(1)
    cands.sort(key=lambda c: (c["price"] if c["price"] else 10**9))
    # attach a parsed price to each booking link so the agent can map chosen candidate -> its link by price
    for lk in links:
        m = re.search(r"¥([\d,]+)", lk.get("t", ""))
        lk["price"] = int(m.group(1).replace(",", "")) if m else None
    print(json.dumps({
        "route": f"{frm}->{to}", "date": ymd, "url": url,
        "candidates": cands, "bookingLinks": links,
        "note": "Agent picks best: cheapest that is AVAILABLE and whose stops include the requested destination. Availability is a laggy hint — confirm on the booking site."
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
