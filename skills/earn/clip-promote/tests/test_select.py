"""Unit tests for the PURE SELECT parse+rank (REQ-1). Fixtures are the REAL anchors captured live
2026-06-29 from the logged-in promote.fun campaigns page (aniccaclips)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from select_campaigns import parse_link, rank_campaigns  # noqa: E402

# real subset captured live
LIVE = [
    {"href": "/campaigns", "t": "Campaigns"},                       # nav, not a campaign
    {"href": "/campaigns/bia-audio-3", "t": "$3,750.00 $1.50"},
    {"href": "/campaigns/crocs", "t": "$17,500.00 $2.50"},
    {"href": "/campaigns/copa90", "t": "$4,000.00 $1.50"},
    {"href": "/campaigns/madden-content-2", "t": "$8,000.00 $1.75"},
    {"href": "/campaigns/fenix-flexin", "t": "$8,000.00 $0.90"},
]


def test_parse_link_extracts_slug_budget_cpm():
    c = parse_link("/campaigns/crocs", "$17,500.00 $2.50")
    assert c == {"slug": "crocs", "budget": 17500.0, "cpm": 2.5}


def test_parse_link_rejects_nav_and_malformed():
    assert parse_link("/campaigns", "Campaigns") is None
    assert parse_link("/campaigns/x", "$10.00") is None  # only one money value
    assert parse_link("/other/crocs", "$1 $2") is None


def test_rank_by_cpm_times_budget_desc():
    r = rank_campaigns(LIVE)
    slugs = [c["slug"] for c in r]
    assert slugs[0] == "crocs"          # 2.5*17500 = 43750 (highest)
    assert slugs[1] == "madden-content-2"  # 1.75*8000 = 14000
    assert "Campaigns" not in slugs     # nav excluded
    assert r[0]["score"] == 43750.0


def test_clipped_are_excluded():
    r = rank_campaigns(LIVE, clipped={"crocs"})
    assert all(c["slug"] != "crocs" for c in r)
    assert r[0]["slug"] == "madden-content-2"


def test_dedup_slugs():
    dupe = LIVE + [{"href": "/campaigns/crocs", "t": "$17,500.00 $2.50"}]
    r = rank_campaigns(dupe)
    assert [c["slug"] for c in r].count("crocs") == 1


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"  ok  {fn.__name__}")
        except Exception:
            failed += 1; print(f"  FAIL {fn.__name__}"); traceback.print_exc()
    print(f"\n{len(fns)-failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
