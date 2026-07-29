# earn/video money rail — ChangeNOW crypto affiliate + on-chain USDC detector (②③)

**Date**: 2026-06-30 · **Status**: built + live-tested (honest $0, no commissions yet) · **Slot**: earn/video

## Problem
The earn/video machine could warm + post, but had NO monetization: `MONEY_AFFILIATE_URL` was empty and `record_earn`
was fail-closed (recorded nothing). Deeper mismatch: the loop counts **on-chain USDC**, but typical faceless-IG
monetization (affiliate/CPM) pays **fiat**. Resolution: pick an affiliate that pays **crypto** so it settles as USDC
to the founder wallet → the loop's on-chain detector counts it. No self-made ebook.

## Decision (BP-cited)
**ChangeNOW Partner Program** (changenow.io/for-partners + best-financial-affiliate-programs, 2026-06-30):
no-KYC email+password signup, API key, **crypto payouts**, lifetime recurring 0.4%/swap. Referral link format
`https://changenow.io/?link_id=<API_KEY>` (changenow.io/referral-links). Fits the USDC loop; realistic for a
money/crypto IG. Rejected fiat-only programs (Wise/Robinhood/Credit Karma).

## What was built
| Piece | File | Contract |
|---|---|---|
| Affiliate account | `~/.cloak/changenow-partner.json` (chmod 600) | email person@example.com, api_key, referral_link, payout_wallet=0x810f |
| Bio link wiring | `~/.openclaw/.env` `MONEY_AFFILIATE_URL` | slot reads it → S2 installs in IG bio post-warmup (verified S2 DRY) |
| On-chain detector | `skills/earn/video/onchain.py` | read-only Base RPC; `confirm_usdc_inflow(entry,recipient,rpc)` + `scan_inflows` + `detect()` |
| record gate | `record_earn.py` | pure schema gate; default `verify_onchain`=False (fail-closed); `onchain_check` injectable |
| S4 wiring | `run.sh` S4_record | detect() → record_earn(…, onchain_check=confirm_usdc_inflow) over inflows; records ONLY confirmed USDC |

## Invariants (CANNOT-FABRICATE)
- A recorded earning MUST correspond to a **real, successful Base tx** containing a **USDC** (0x833589…2913)
  Transfer whose `to`== the DEDICATED earn/video receive address (0x61bB7105…2d78, ChangeNOW-payout-only, NOT the shared 0x810f) AND from != recipient (self-transfers rejected), and whose raw amount matches to within 1 micro-USDC. Else rejected.
- Idempotent on `tx_hash` (detect dedup + record_earn `_seen_tx`). RPC error / mismatch / failed tx → False (no fabrication).
- With no real inflow → recorded total == 0 (verified live: detect scanned Base, found 0, recorded 0).

## Money flow (end to end)
```
faceless reel CTA "swap crypto via link in bio"
  → viewer swaps on ChangeNOW via referral link (link_id = our api key)
  → ChangeNOW accrues commission (crypto)
  → withdraw as USDC (Base) to founder 0x810f       ← gated on real balance (future, no revenue yet)
  → onchain.detect() sees the Transfer to 0x810f
  → record_earn confirms it on-chain → ledger += real USDC
```

## Live verification (2026-06-30, no-mock)
- `test_onchain.py` confirms a REAL Base tx (0xce52f06f… → 0xe903… 0.01333 USDC) and rejects wrong-recipient /
  wrong-amount / bad-tx / missing-tx. RPC needs a browser-like User-Agent (public RPC 403s default python UA).
- S4 via run.sh: scans Base live → 0 new inflows → records $0 (honest), single-line JSON.

## Remaining (gated on real revenue, NOT code)
1. First withdrawal: set ChangeNOW payout to USDC/Base→0x810f (dashboard form appears once a balance exists).
2. Content CTA must actually drive swaps (conversion) — the real bottleneck after warmup completes (~day 7).
3. Optional: automate the withdrawal step (ChangeNOW dashboard) once a minimum balance accrues.

## Adversary fix (2026-06-30): dedicated receive address
The shared earn wallet 0x810f also receives x402/gig/funding USDC → would misattribute as video revenue. FIX: a DEDICATED fresh wallet `0x61bB710582bcAE3f62008BCBfa0fc2E5DFC92d78` (`~/.cloak/earn-video-wallet.json`, key local-only) receives ONLY ChangeNOW affiliate withdrawals → every inflow is genuinely affiliate revenue. `confirm_usdc_inflow`+`scan_inflows` also reject self-transfers (from==to). Dedup keyed on (tx_hash, log_index). Live no-mock test added: a real Base self-transfer tx is rejected.
