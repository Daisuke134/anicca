#!/usr/bin/env python3
"""verify_positions.py — REQ-LV-017 daily verification evidence for pm-earner. A NEW, purely
additive, read-only script — does NOT touch fetch_positions()/redeem_positions() or any part of
the trading/redeem pipeline in redeem.py (that logic is unchanged, "維持"). Does the same
unauthenticated GET https://data-api.polymarket.com/positions?user=<wallet> redeem.py's own
fetch_positions() already does, but feeds the raw response text through the new, frozen
parse_positions_response(json_text) pure function to normalize it into {market, size, redeemable}
rows for the daily mail-evidence report — a lighter, verification-only view, separate from
fetch_positions()'s richer trading-shaped rows.

CLI: `python3 verify_positions.py [wallet]` -> one JSON line
  {"wallet": "...", "positions_count": N, "redeemable_count": M, "positions": [...]}
Fail-closed like every other network call in this codebase: any request/parse error -> positions=[]
(never fabricates a count), reported via "error" key rather than crashing.
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from positions import parse_positions_response  # noqa: E402 (REQ-LV-017, frozen)

DATA_API = "https://data-api.polymarket.com"
DEFAULT_WALLET = os.environ.get("PM_EARNER_WALLET", "0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74")


def build_url(wallet: str) -> str:
    """Same endpoint/params shape as redeem.py's own fetch_positions(), kept intentionally separate
    here so this verification-only path never depends on (or risks breaking) the trading
    pipeline's request logic."""
    import urllib.parse
    query = urllib.parse.urlencode({"user": wallet, "sizeThreshold": 0.001, "limit": 100})
    return f"{DATA_API}/positions?{query}"


def _default_fetch(url: str, timeout: int) -> str:
    req = urllib.request.Request(url, headers={"user-agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def verify_positions(wallet: str = DEFAULT_WALLET, timeout: int = 20, fetch=None) -> dict:
    """`fetch` is an injectable (url, timeout) -> response_text callable (mirrors this codebase's
    onchain_check/sigStatus injection-seam convention) so tests never hit the real network."""
    fetch = fetch or _default_fetch
    try:
        body = fetch(build_url(wallet), timeout)
    except Exception as e:
        return {"wallet": wallet, "positions_count": 0, "redeemable_count": 0, "positions": [], "error": str(e)}

    positions = parse_positions_response(body)
    redeemable_count = sum(1 for p in positions if p.get("redeemable") is True)
    return {
        "wallet": wallet,
        "positions_count": len(positions),
        "redeemable_count": redeemable_count,
        "positions": positions,
    }


if __name__ == "__main__":
    w = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_WALLET
    print(json.dumps(verify_positions(w), ensure_ascii=False))
