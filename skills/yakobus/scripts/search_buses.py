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
import sys, json, re
from playwright.sync_api import sync_playwright

CDP = "http://localhost:9222"
SKIP = {"夜行便","昼行便","充電","Wi-Fi","女性安心","女性専用席","トイレ付","仕切りカーテン",
        "3列独立","4列標準","4列足元広め","座席指定","2列","2列独立","3列シート","4列"}

def parse(txt):
    lines = [l.strip() for l in txt.split("\n")]
    idx = [i for i, l in enumerate(lines) if l.startswith("予約サイト")]
    out = []
    for n, i in enumerate(idx):
        end = idx[n+1] if n+1 < len(idx) else len(lines)
        name = ""
        for j in range(i-1, max(i-8, -1), -1):
            if lines[j] and lines[j] not in SKIP:
                name = lines[j]; break
        blk = "\n".join(lines[i:end])
        price = re.search(r"¥([\d,]+)", blk)
        price = int(price.group(1).replace(",", "")) if price else None
        dests = []
        for stop in ["バスタ新宿","新宿","池袋","八重洲","東京駅","横浜","町田","大手町","TDL","TDS"]:
            if stop in blk and stop not in dests:
                dests.append(stop)
        st = "満席" if "満席" in blk else ("わずか" if "わずか" in blk else "空席")
        times = re.findall(r"\d{1,2}:\d{2}", blk)
        out.append({"name": name[:60], "price": price, "stops": dests,
                    "availability": st, "times": times[:6]})
    return out

def main():
    frm, to, ymd = sys.argv[1], sys.argv[2], sys.argv[3]
    url = f"https://www.bushikaku.net/search/{frm}_{to}/{ymd}/"
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP); ctx = b.contexts[0]
        pg = ctx.new_page(); pg.on("dialog", lambda d: d.accept())
        pg.goto(url, wait_until="domcontentloaded", timeout=90000); pg.wait_for_timeout(3500)
        txt = pg.evaluate("()=>{const t=document.body.innerText;const i=t.indexOf('並び替え');return t.slice(i>0?i:0,(i>0?i:0)+16000);}")
        links = pg.evaluate("""()=>[...document.querySelectorAll('a[href]')].filter(a=>/external_link|booking\\/select/.test(a.href)).map(a=>({t:(a.textContent||'').replace(/\\s+/g,' ').trim().slice(0,40),h:a.href})).slice(0,60)""")
    cands = parse(txt)
    cands.sort(key=lambda c: (c["price"] if c["price"] else 10**9))
    print(json.dumps({
        "route": f"{frm}->{to}", "date": ymd, "url": url,
        "candidates": cands, "bookingLinks": links,
        "note": "Agent picks best: cheapest that is AVAILABLE and whose stops include the requested destination. Availability is a laggy hint — confirm on the booking site."
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
