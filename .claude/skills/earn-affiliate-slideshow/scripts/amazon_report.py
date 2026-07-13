#!/usr/bin/env python3
"""amazon_report.py — read the REAL Amazon Associates earnings report (verification engine).

This is the "actually earned money" gate of the affiliate skill. It reads the LIVE Amazon
Associates dashboard via the CloakBrowser daily-driver (CDP) and extracts the real numbers:
clicks, ordered items, shipped items, commission (紹介料). NO faking — only what Amazon shows.
The earn loop feeds these into the un-fakeable ledger (record-affiliate-earn.mjs); a row is
recorded ONLY when commission > 0 (a real sale). Until then the honest number is ¥0.

Per memory: past earn skills earned ¥0 because verification was missing — this closes that gap.

Usage: amazon_report.py            # prints JSON {clicks, ordered, shipped, commission_jpy, asof}
Reads the daily-driver (must be logged into affiliate.amazon.co.jp). Uses cdp.py from
ig-account-create. Run with /opt/homebrew/bin/python3.
"""
import sys, os, json, time
sys.path.insert(0, os.path.expanduser("~/.agents/skills/ig-account-create/scripts"))
import cdp


def main():
    tid = cdp.new_tab("https://affiliate.amazon.co.jp/home")
    time.sleep(8)
    # the home dashboard "今月のレポート" card shows: 発送済み商品/紹介料合計/注文済み商品/クリック数/コンバージョン率
    data = cdp.evaluate(tid, r"""(()=>{
      const T = document.body.innerText;
      const grab = (label) => {
        // find a number that follows the label within the report card text
        const re = new RegExp(label + "[^0-9¥%\\-]{0,12}([¥]?[0-9,\\.]+%?)");
        const m = T.match(re); return m ? m[1] : null;
      };
      return {
        commission_raw: grab("紹介料合計") || grab("紹介料"),
        ordered:        grab("注文済み商品の合計") || grab("注文済み商品"),
        shipped:        grab("発送済み商品の合計") || grab("発送済み商品"),
        clicks:         grab("クリック数"),
        conv:           grab("コンバージョン率"),
        loggedOut:      /アソシエイト・セントラル.*サインイン|ログイン/.test(T) && !/StoreID/.test(T),
        storeId:        (T.match(/StoreID:\s*([a-z0-9\-]+)/i)||[])[1] || null
      };
    })()""")
    cdp.close_tab(tid)
    if not isinstance(data, dict):
        print(json.dumps({"error": "could not read report", "raw": str(data)[:200]})); return
    if data.get("loggedOut"):
        print(json.dumps({"error": "not logged into affiliate.amazon.co.jp"})); return

    def yen(x):
        if not x: return 0
        return int(x.replace("¥", "").replace(",", "").split(".")[0] or 0)
    def num(x):
        if not x: return 0
        try: return int(x.replace(",", "").split(".")[0])
        except Exception: return 0

    out = {
        "store_id": data.get("storeId"),
        "clicks": num(data.get("clicks")),
        "ordered_items": num(data.get("ordered")),
        "shipped_items": num(data.get("shipped")),
        "commission_jpy": yen(data.get("commission_raw")),
        "conversion": data.get("conv"),
        "asof": time.strftime("%Y-%m-%d %H:%M JST"),
        "real_sale": yen(data.get("commission_raw")) > 0,   # the "actually earned" gate
    }
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
