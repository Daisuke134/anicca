#!/usr/bin/env python3
"""sales_selector.py (A5 / #9) — rank OUR OWN Capafy listings by real sales signal so the build
loop doubles down on what actually sells, instead of picking the next skill by blind judgment.

Data reality (measured 2026-07-19): the seller endpoint GET /agent/agents returns ONLY our own
listings (26), each with fields: sales, recentSales, rating, ratingCount, reviewCount, agentStatus.
There is NO reliable marketplace-wide ranking endpoint (POST /agent/agents/search is server-broken).
So this ranks OUR listings. When we have zero sales signal it says so honestly (no fabrication) and
tells the build loop to fall back to BEST_PRACTICES marketplace-winner research.

Output: ~/.local/state/life-manager/state/capafy-sales-ranking.json + a human summary printed to stdout.
The build loop reads the JSON in STEP2 to prioritize the winning category for the next listing.
"""
import json, os, subprocess, sys
from pathlib import Path

REPO_ROOT = Path(os.environ.get("LIFE_MANAGER_REPO", Path(__file__).resolve().parents[3]))
CAPAFY_HTTP = str(REPO_ROOT / "skills/capafy-autopublish/vendor/capafy-user/scripts/capafy_http.py")
OUT = os.path.expanduser("~/.local/state/life-manager/state/capafy-sales-ranking.json")


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _fetch():
    r = subprocess.run(
        ["/opt/homebrew/bin/python3", CAPAFY_HTTP, "GET", "/agent/agents"],
        capture_output=True, text=True, timeout=60,
    )
    d = json.loads(r.stdout)
    lst = (((d or {}).get("data") or {}).get("list")) or []
    return lst if isinstance(lst, list) else []


def _score(a):
    # sales weighted highest, then recent momentum, then social proof (rating * reviews).
    return _num(a.get("sales")) * 10 + _num(a.get("recentSales")) * 5 + _num(a.get("rating")) * _num(a.get("reviewCount"))


def main():
    try:
        agents = _fetch()
    except Exception as e:  # network / server-broken — do not crash the loop
        out = {"ok": False, "error": f"fetch failed: {e}", "signal": "none", "advice": "use BEST_PRACTICES marketplace research"}
        json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=2)
        print(json.dumps(out)); return 0

    ranked = sorted(agents, key=_score, reverse=True)
    total_sales = sum(_num(a.get("sales")) + _num(a.get("recentSales")) for a in agents)
    top = [
        {"name": a.get("name"), "agentId": a.get("agentId"), "status": a.get("agentStatus"),
         "sales": a.get("sales"), "recentSales": a.get("recentSales"),
         "rating": a.get("rating"), "reviewCount": a.get("reviewCount"), "score": _score(a)}
        for a in ranked[:5]
    ]

    if total_sales <= 0:
        out = {
            "ok": True, "signal": "none", "listings": len(agents),
            "advice": "NO sales signal yet across our listings — do NOT fabricate a winner. "
                      "For this pass, pick the next skill via BEST_PRACTICES.md marketplace-winner "
                      "research (research a live top seller, copy its pricing/category/structure).",
            "top_by_proxy": top,
        }
    else:
        winner = ranked[0]
        out = {
            "ok": True, "signal": "sales", "listings": len(agents),
            "winner": {"name": winner.get("name"), "agentId": winner.get("agentId")},
            "advice": f"Our best-selling listing is '{winner.get('name')}'. Build the NEXT skill in the "
                      f"same category/style as our proven winners below (double down on what sells).",
            "top": top,
        }
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
