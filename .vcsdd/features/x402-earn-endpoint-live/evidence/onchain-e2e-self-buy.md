# On-chain E2E evidence — x402 self-facilitation settle (no-mock, Base mainnet)

Date: 2026-06-28 · Feature: x402-earn-endpoint-live (continuation of founder-x402-self-facilitate §Done c+d)

## What was proven (REAL money, no mock, no CDP, no human)
The founder x402 self-facilitating server (`apps/x402-agents/src/server.js`, POST /social/x, $0.003 USDC,
payTo founder 0x810f) settles a real x402 payment on Base mainnet using an in-process facilitator signed
by the founder key — no Coinbase/CDP account, the founder wallet pays its own settle gas.

## Mechanism verification (throwaway key boot)
- GET /health → 200 {status:ok, gas_ready:false}
- GET /metadata → POST /social/x, $0.003, eip155:8453, payTo 0x810f, USDC asset, discoverable:true
- POST /social/x (no payment) → 402 Payment Required with valid PAYMENT-REQUIRED (amount 3000 = $0.003,
  asset USDC 0x8335..2913, payTo 0x810f, maxTimeoutSeconds 60) + Bazaar discovery extension schema.

## Real on-chain settle (founder key boot + real buyer)
- Buyer = automaton 0xa3CDd4 (~/.automaton/wallet.json), signed EIP-3009 transferWithAuthorization.
- Server = founder 0x810f key (~/.anicca-founder/wallet.json), in-process x402Facilitator.
- Buyer POST /social/x → HTTP 200, paymentStatus: "settled".
- tx: 0x71d4ca087d909a8ac79a22ada491250c4c392ee42e2b5d6309bed7d72b1d2a98
  - https://basescan.org/tx/0x71d4ca087d909a8ac79a22ada491250c4c392ee42e2b5d6309bed7d72b1d2a98
  - receipt status: success | block 47928100 | gasUsed 102820 | from (settler) = 0x810f (self-facilitation)
- USDC balances: founder 0x810f 0 → 0.003 (received) ; buyer 0xa3CDd4 0.003129 → 0.000129 (paid).
- founder ETH gas: 0.0000469 → 0.0000463 (spent ~0.0000006 ETH — plenty for many settles).

## Honesty gate (§Done d) — INV-7 self-payment exclusion
- `record-earn.mjs --source x402` (prod) → "no EXTERNAL income ... self-transfers ignored — nothing recorded".
- founder STATE realised_earn_usdc = 0 (the self-buy is NOT counted as revenue — payer 0xa3CDd4 ∈ MY_WALLETS/SHARED).
- ⇒ the mechanism is proven; the $0.003 is explicitly NOT earnings. Real revenue requires a real EXTERNAL buyer.

## Remaining for REAL external revenue (NOT done yet — honest)
- F2 host: cloudflared public tunnel so external buyers can reach the endpoint.
- F4 discovery: register on x402scan + Bazaar so buyer agents find it.
- Product: POST /social/x handler is a STUB (returns example data) — wire real X/Twitter scraping
  (TWITTERAPI_KEY present) so a paying buyer gets real value.
- F5: 24/7 launchd heartbeat keeping it alive.
- Demand: a real external buyer agent calling + paying (the genuine hard part, demand-constrained).
