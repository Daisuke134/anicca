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

## UBI-E2 — email (Crossmint) — ✅ PASS (2026-06-18)
Proves: a person with ONLY an email receives real USDC (no wallet/crypto knowledge). Dais accesses via email login.
- Crossmint server key in `~/.openclaw/.env::CROSSMINT_API_KEY` (gitignored, NOT in repo).
- Created email-owned smart wallet: `POST https://www.crossmint.com/api/2025-06-09/wallets` body `{"chainType":"evm","owner":"email:keiodaisuke@gmail.com","config":{"adminSigner":{"type":"email","email":"keiodaisuke@gmail.com"}}}` → address **0x9557737Cf1640fA71845af33dD7018adcd4c5aD9** (owner email:keiodaisuke@gmail.com).
- anicca sent real $0.50 USDC (execute-ubi, anicca key): **tx 0x421f0307d6e36f15e960f6e802cac65fe3122b8d06d4e4f955d907c76ebaa677, status 0x1**.
- Verify: Transfer log → to 0x9557…ad9, amount 0.5 ; balanceOf (lowercase) = **0.50** ✓. (NOTE: an earlier balanceOf read 0.0 due to a MIXED-CASE address in my eth_call calldata — node match needs lowercase; fixed + re-verified. Not a payment issue.)
- Dais verifies: sign in at crossmint.com with keiodaisuke@gmail.com → sees the $0.50 on Base; can hold or off-ramp.

## UBI-E3/E4 — bank/card (Stripe+Bridge) — BLOCKED today (honest)
Bridge.xyz requires business KYB onboarding (multi-day) before USDC→bank/card payouts. Stripe Connect onboarding is live (income-apply.js) but the USDC→fiat leg (Bridge) cannot be completed in hours. Not faked. Pending KYB.
## UBI-E3/E4 — bank/card (Stripe+Bridge) — pending
## UBI-E5 — creator daily payout — pending
## UBI-E6 — mobile (Kotani sandbox) — pending
## UBI-E7 — FIFO queue / batch unlock — pending
## UBI-E8 — sybil gate (idkit) — pending
