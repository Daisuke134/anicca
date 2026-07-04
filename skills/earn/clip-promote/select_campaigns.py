"""select_campaigns.py — SELECT (REQ-1): list ACTIVE promote.fun campaigns from the logged-in CDP tab
and rank them by (CPM x remaining budget), skipping any already-clipped this cycle. The PARSE+RANK core
is PURE (rank_campaigns) so it is unit-tested without a browser; fetch_live() does the CDP read.

promote.fun campaign anchors look like: href="/campaigns/<slug>", text "$17,500.00 $2.50" (budget, cpm).
Verified live 2026-06-29 (logged in as aniccaclips): crocs $17,500 @$2.50, jackass-clips-1 $8,000 @$1.50,
madden-content-2 $8,000 @$1.75, etc. The platform itself requires a WARMED account for new pages
(crocs Rules: "Warm the account up properly") — so POST is gated on a ready account (REQ-4), not here.
"""
import json
import re

_MONEY = re.compile(r"\$([0-9][0-9,]*(?:\.[0-9]+)?)")


def _money(s):
    return float(s.replace(",", ""))


def parse_link(href, text):
    """Parse one campaign anchor → {slug, budget, cpm} or None. PURE."""
    if not href or "/campaigns/" not in href:
        return None
    slug = href.rstrip("/").split("/campaigns/", 1)[1]
    if not slug or "/" in slug:
        return None
    nums = _MONEY.findall(text or "")
    if len(nums) < 2:
        return None
    budget, cpm = _money(nums[0]), _money(nums[1])
    return {"slug": slug, "budget": budget, "cpm": cpm}


def rank_campaigns(raw_links, clipped=None):
    """Given the raw [{href,t}] anchors, return ACTIVE campaigns ranked by cpm*budget desc,
    excluding any slug in `clipped`. PURE + deterministic."""
    clipped = set(clipped or [])
    out = []
    seen = set()
    for a in raw_links or []:
        c = parse_link(a.get("href"), a.get("t") or a.get("text"))
        if not c or c["slug"] in clipped or c["slug"] in seen:
            continue
        seen.add(c["slug"])
        c["score"] = round(c["cpm"] * c["budget"], 2)
        out.append(c)
    out.sort(key=lambda c: c["score"], reverse=True)
    return out


def fetch_live(tid, cdp):
    """Live read of the campaigns page via an injected cdp module (cdp.navigate / cdp.evaluate).

    REQ-4 fix (2026-07-04): filter to Instagram-only via the platform dropdown BEFORE
    scraping cards. Without this, fetch_live returned ALL campaigns regardless of accepted
    platform, and SELECT picked "crocs" — a TikTok-only campaign (confirmed live: its
    detail page's "Accepted Platforms" showed only a TikTok icon) that clip-promote cannot
    post to via IG. The dropdown selection is NOT reflected in the URL (client-side state
    only, verified: url stays https://www.promote.fun/campaigns after filtering) — must
    click through the UI every time, cannot deep-link."""
    import time
    cdp.navigate(tid, "https://www.promote.fun/campaigns")
    time.sleep(6)
    cdp.click_by_text(tid, "All Platforms")
    time.sleep(1)
    cdp.click_by_text(tid, "Instagram")
    time.sleep(2)
    js = (
        "JSON.stringify(Array.from(document.querySelectorAll('a[href*=\"/campaign\"]'))"
        ".slice(0,60).map(function(a){return {href:a.getAttribute('href'),"
        "t:(a.innerText||'').replace(/\\s+/g,' ').trim()}}))"
    )
    raw = cdp.evaluate(tid, js)
    try:
        return json.loads(raw)
    except Exception:
        return []


if __name__ == "__main__":  # CLI: prints the ranked active campaigns as JSON (needs a live CDP tab)
    import os
    import sys
    cdp_dir = os.environ.get("CDP_DIR", os.path.expanduser("~/.claude/skills/ig-account-create/scripts"))
    sys.path.insert(0, cdp_dir)
    import cdp  # noqa: E402
    tid = os.environ.get("PF_TID", "")
    ranked = rank_campaigns(fetch_live(tid, cdp))
    print(json.dumps(ranked, ensure_ascii=False))
