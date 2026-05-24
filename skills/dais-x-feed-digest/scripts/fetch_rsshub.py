#!/usr/bin/env python3
"""dais-x-feed-digest : fetch watchlist X accounts via RSSHub, FULL text.

DETERMINISTIC. Pulls each handle's timeline (own posts + RT) from the local
RSSHub container and keeps the FULL tweet text (RSS <description>, NOT the
truncated <title>). HARD RULE #13: never lose source detail at fetch time.

Requires: RSSHub running on :1200 with TWITTER_AUTH_TOKEN set (see SKILL.md).
Usage: python3 fetch_rsshub.py [out.json]   (default: workspace/rsshub_full.json)
Prints per-handle item count + total chars. Exit 0 if >=8/12 handles ok.
"""
import json, os, sys, time, re, html, urllib.request
import xml.etree.ElementTree as ET

SKILL = os.path.expanduser("~/.openclaw/skills/dais-x-feed-digest")
WORK = os.path.expanduser("~/.openclaw/workspace/dais-x-feed-digest")
os.makedirs(WORK, exist_ok=True)
out_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(WORK, "rsshub_full.json")

handles = json.load(open(os.path.join(SKILL, "watchlist.json")))["x_handles"]
handles = [h.lstrip("@") for h in handles]

def clean(s):
    s = re.sub(r"<br\s*/?>", " ", s or "")
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s).strip()

out = {"fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%S+09:00"), "accounts": {}}
ok = 0
for h in handles:
    try:
        req = urllib.request.Request(f"http://localhost:1200/twitter/user/{h}",
                                     headers={"User-Agent": "anicca"})
        xml = urllib.request.urlopen(req, timeout=45).read()
        root = ET.fromstring(xml)
        items = []
        for it in root.findall(".//item")[:10]:
            desc = clean(it.findtext("description") or "")
            title = clean(it.findtext("title") or "")
            full = desc if len(desc) > len(title) else title
            items.append({"full": full,
                          "url": (it.findtext("link") or "").strip(),
                          "date": (it.findtext("pubDate") or "").strip()})
        out["accounts"][h] = {"n": len(items), "items": items}
        if items:
            ok += 1
        print(f"{h}: {len(items)}", flush=True)
    except Exception as e:  # noqa
        out["accounts"][h] = {"n": 0, "error": str(e)[:120]}
        print(f"{h}: ERR {e}", flush=True)
    time.sleep(1)

json.dump(out, open(out_path, "w"), ensure_ascii=False, indent=1)
total = sum(len(i["full"]) for v in out["accounts"].values() for i in v.get("items", []))
print(f"FETCH_DONE ok={ok}/{len(handles)} totalChars={total} out={out_path}")
sys.exit(0 if ok >= 8 else 1)
