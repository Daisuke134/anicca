# Audit evidence — live `userFills` query, wallet `0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21`

- **Fetched**: 2026-07-09 (this session), via `curl -s https://api.hyperliquid.xyz/info -d
  '{"type":"userFills","user":"0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21"}'` — public, read-only
  Hyperliquid Info API endpoint. No signing key used. No order was placed. Raw response saved
  verbatim at `evidence/audit-userfills-0xa3cdd4-raw.json` (46,424 bytes).
- **Fill count**: 146 fills total (matches behavioral-spec.md §2 item 1's claim exactly).
- **Non-zero `closedPnl` fills**: 71 of 146 (the other 75 are opening/increasing fills with
  `closedPnl == "0"`, correctly excluded by REQ-B2's `closedPnl != 0` filter).
- **Sum of `closedPnl`** across all 146 fills: `0.27274`
- **Sum of `fee`** across all 146 fills: `0.396474`
- **Net** (`sum(closedPnl) - sum(fee)`): `-0.123734` — matches behavioral-spec.md §2 item 2's
  cited "actual realized net ≈ −$0.1237" to 4 decimal places. No correction to that figure was
  needed; §2 now cites this file instead of standing unsubstantiated.
- **Raw field presence (first fill, verbatim from the live response)**:
  ```json
  {
    "coin": "ETH", "px": "1793.9", "sz": "0.0027", "side": "A",
    "time": 1783370643509, "startPosition": "0.0027", "dir": "Close Long",
    "closedPnl": "0.01458", "hash": "0xd74c8801392f5d6dd8c6043f5c910b01c3009fe6d4227c3f7b153353f8233758",
    "oid": 489132799604, "crossed": true, "fee": "0.002179",
    "tid": 568915744567876, "feeToken": "USDC", "twapId": null
  }
  ```
  Confirms `fee` and `tid` ARE present on real fill objects (the installed
  `hyperliquid-python-sdk` v0.24.0 docstring cited in F-5 is stale/incomplete — it omits several
  fields, including `fee`, `tid`, and `feeToken`, that the live API actually returns). All 146
  fills carry a `fee` field (numeric string) and a `tid` field (Python `int`, never a string,
  never missing) — confirmed by iterating the full response, not just the first element.
- **Tied-timestamp confirmation**: iterating all 146 `time` values found exactly 1 duplicate
  timestamp pair (two distinct `tid`s sharing the same millisecond `time`) — live confirmation
  that EDGE-9's "same-close multiple partial fills at an identical timestamp" scenario is a real,
  observed case on this wallet's own history, not merely a theoretical one. This is the exact
  condition F-1's fix (inclusive re-query boundary) exists to make safe.
- **No pagination limit observed**: the full 146-fill lifetime history for this address was
  returned in a single `user_fills_by_time`-equivalent call with no truncation marker — consistent
  with NFR-1 not yet requiring pagination/chunking at this wallet's current scale (still deferred
  to Phase 5 hardening if a future wallet's history exceeds whatever limit the live API enforces).
