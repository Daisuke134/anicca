#!/usr/bin/env python3
"""defi-yield/lib.py — PURE pool selection + supply sizing for the DeFi yield earn slot (no I/O, no keys).

CLOUD-portable earner: supply USDC to a battle-tested lending pool and accrue yield, wallet-signature only,
no KYC/browser. The effectful shell (yield.py) fetches live DefiLlama pools + calls the pool's supply(); this
module is the testable judgment: which pool, how much. Verified live 2026-07-04: Base USDC = aave-v3 3.14%
$29M / fluid-lending 5.29% $9M.
"""

# Only battle-tested lending protocols (no exotic/farm risk) qualify for a self-funded AI's capital.
ALLOWED = ("aave-v3", "spark", "compound-v3", "morpho-blue", "fluid-lending", "moonwell")


def pick_pool(pools, allowed=ALLOWED, min_tvl_usd=5_000_000, min_apy=0.5, prefer_safest=True):
    """Choose one USDC pool. Filters to allowed protocols + min TVL + min APY. Returns the chosen pool dict
    or None. `prefer_safest`=True ranks by (protocol-rank, then APY) so a huge-TVL blue-chip wins over a
    marginally-higher exotic; False ranks purely by APY. Pure (no network)."""
    cand = []
    for p in pools:
        if p.get("project") not in allowed:
            continue
        if (p.get("symbol") or "").upper() != "USDC":
            continue
        if (p.get("tvlUsd") or 0) < min_tvl_usd:
            continue
        if (p.get("apy") or 0) < min_apy:
            continue
        cand.append(p)
    if not cand:
        return None
    if prefer_safest:
        rank = {name: i for i, name in enumerate(allowed)}
        cand.sort(key=lambda p: (rank.get(p.get("project"), 99), -(p.get("apy") or 0)))
    else:
        cand.sort(key=lambda p: -(p.get("apy") or 0))
    return cand[0]


def size_supply(balance_usdc, gas_reserve=0.5, max_pct=0.9, min_supply=1.0):
    """USDC to supply: up to max_pct of the balance above the gas reserve, never below min_supply (else 0).
    Keeps a reserve so the wallet can always pay gas to withdraw. Pure."""
    if balance_usdc <= gas_reserve:
        return 0.0
    usable = balance_usdc - gas_reserve
    amt = usable * max_pct
    return amt if amt >= min_supply else 0.0
