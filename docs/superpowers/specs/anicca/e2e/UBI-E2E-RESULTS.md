# UBI E2E results (fresh evidence, no-mock) — append-only

## UBI-E1 — wallet payout (anicca → recipient, real USDC on Base) — ✅ PASS (2026-06-18)
FOUNDATION GATE. Proves anicca can send real USDC autonomously (its own key), recipient verifiably receives.

- Mechanism: `~/anicca/skills/earn/execute-ubi.py` (web3.py ERC-20 `transfer`), signed with `BLOCKRUN_WALLET_KEY` (anicca's own wallet, NOT a human key). UBI_PLAN = `{"transfers":[{"to":<addr>,"amount_base":200000}]}`.
- Sender (anicca): `0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21`
- Recipient (test, key saved /tmp/ubi-selftest-recipient.json, recoverable): `0xF4776B523D4b8e76CEE5040974AA874D8A579bE7`
- Amount: $0.20 USDC (200000 base units)
- **tx: `0x3d6be65183088eb4a9d2dfa77cad3d6c43cda8e6bddb19fe42b9ea82a33d7b97` — status 0x1, block 47488085**
- Verify (Base RPC `balanceOf`): recipient USDC = **0.20** ✓ ; receipt status = 0x1 ✓
- Sender balance: 8.63 → 7.59 (NOTE: dropped ~$1.04, more than the $0.20 sent — likely other wallet activity / x402 compute outflow; flagged for follow-up, not fabricated).

Conclusion: the SEND rail is real and verified on-chain. Demo's "sign up → real money arrives" is feasible via this path. No fake.

## UBI-E1b — /income signup path (live prod) — ✅ PASS (2026-06-18)
- /income rebuilt LIVE: apply above fold, email/wallet/bank/card, full UBI copy + roadmap, iOS logo removed. Home hero top CTA "Receive basic income" → /income (verified curl).
- `POST https://aniccaai.com/.netlify/functions/income-signup {"email":...,"method":"email"}` → `{"ok":true,"recorded":true}` (real Supabase insert, status=queued, wallet+method in notes).
- Demo path: signup recorded in prod → payout sent locally via execute-ubi (UBI-E1, proven). Full auto form→send watcher = STAGE 2.

## UBI-E2 — email (Crossmint) — pending
## UBI-E3/E4 — bank/card (Stripe+Bridge) — pending
## UBI-E5 — creator daily payout — pending
## UBI-E6 — mobile (Kotani sandbox) — pending
## UBI-E7 — FIFO queue / batch unlock — pending
## UBI-E8 — sybil gate (idkit) — pending
