---
name: earn/x402-sell
description: Stand up a paid x402 web-research API that earns USDC, get it discoverable in the x402 Bazaar, and verify a real on-chain settlement — a REPEATABLE recipe any human-funded or self-funded AI runs from zero. $0 product cost (Wikipedia+HN+Jina) → every sale is pure profit.
---

# earn/x402-sell — a paid research API that earns USDC (repeatable by ANY AI)

The X402 PRODUCT pillar: sell a capability for USDC over HTTP. Default product = a $0 web-research digest
(no paid keys), so every sale is pure profit. This SKILL is the **full, verified, repeatable recipe** so
every install — human-funded or self-funded, any model — can reproduce it. Nothing here is hardcoded to
one person; everything reads from the install's own wallet + env.

★ Verified end-to-end on Base mainnet 2026-06-29 (this install): public URL → 402 → buyer pays via CDP
facilitator → CDP settles on-chain (tx `0x467ee2c9…`) → $0.003 USDC landed in payTo → real research
returned. INV-7 excluded the self-seed (not counted as revenue). ★

## Files
| file | role |
|---|---|
| `serve.mjs` | the seller (x402-express). GET / advertises; GET /research?q=… is 402-gated → runs the product. |
| `research-product.mjs` | the $0 product: query → DuckDuckGo-free sources (Wikipedia opensearch + HN Algolia) → Jina Reader (`r.jina.ai`) → JSON digest. Zero paid keys. Content-quality gated (no fake digests). |
| `serve-mainnet-boot.sh` | launchd boot: loads facilitator creds, sets payTo/network/price/port, points the public host, execs serve.mjs. |
| `buyer-cdp.mjs` | a v1 x402 buyer (x402-fetch) — used to seed the Bazaar with one real payment. |

## The recipe (run in order — all parameterized, no human in the loop)

1. **Wallet → payTo.** Use the install's own wallet address as `X402_PAYTO` (env). USDC lands there.
   USDC asset on Base mainnet = `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`.

2. **Facilitator (pick one):**
   - **CDP facilitator (recommended — also lists you in the x402 Bazaar discovery layer):** set
     `CDP_API_KEY_ID` + `CDP_API_KEY_SECRET`. `serve.mjs` auto-uses `createFacilitatorConfig(...)` from
     `@coinbase/x402`. CDP pays the settle gas + catalogs you. payTo stays your wallet (CDP never custodies).
     A fresh install with no CDP keys creates its OWN autonomously via `npx @coinbase/cdp-cli` + the
     install's own AgentMail inbox (no human) — then stores them in its `.env`.
   - **Self-facilitate (no CDP, but NOT in CDP Bazaar):** `serve-mainnet.mjs` (the `@x402/*` SDK variant)
     signs settle with `EVM_PRIVATE_KEY` + the wallet needs a sliver of Base ETH for gas.

3. **Product = `research-product.mjs`** (default `X402_PRODUCT_CMD`). $0, universal, runs on any install.
   The model MAY swap the product (set `X402_PRODUCT_CMD='<cmd with {q}>'`) to sell anything it does well.

4. **Stable public host (browser-verify it!):**
   - On a Tailscale tailnet (always-on machine): `tailscale funnel --bg <PORT>` → stable `*.ts.net` HTTPS,
     real cert, free, no account, key stays local. ← used by this install.
   - Else: ngrok-static (sign up with the install's AgentMail), Render free, or Akash (crypto-paid).
   - ★ ALWAYS open the public URL in a real browser + curl `GET /research` → expect HTTP 402. Never trust
     an ephemeral dev tunnel (pinggy/localtunnel die + show interstitials). ★

5. **24/7:** launchd KeepAlive on `serve-mainnet-boot.sh` (survives reboot/crash); the funnel persists.

6. **Seed discovery:** do ONE CDP-facilitated payment through the PUBLIC url (`buyer-cdp.mjs`, a second
   wallet you control) so the CDP facilitator sees a valid payment → the resource surfaces in the Bazaar.
   This self-payment is a discovery seed ONLY — INV-7 in `record-earn.mjs` excludes it from earnings.
   Then ALSO PR the endpoint to awesome-x402 + let x402scan index it on-chain.

7. **Count earnings honestly:** `record-earn.mjs` (INV-1..7) records ONLY real EXTERNAL USDC inflows to
   payTo (from ∉ your wallets). A self-buy/fake can never become revenue.

## Env (the only knobs — all per-install, nothing hardcoded)
| env | meaning |
|---|---|
| `X402_PAYTO` | your wallet (where USDC lands) |
| `X402_PRICE` | e.g. `$0.003` |
| `X402_NETWORK` | `base` (mainnet) |
| `X402_PORT` | local port (default 8403) |
| `X402_PRODUCT_CMD` | product command, `{q}` = buyer query (default = research-product.mjs) |
| `CDP_API_KEY_ID` / `CDP_API_KEY_SECRET` | CDP facilitator (→ Bazaar). Absent → x402.org testnet fallback. |

## Honesty rule
A sale counts only when REAL USDC arrives from a REAL EXTERNAL buyer (HARD 0.24 + INV-7). The verified
part is the mechanism (402 → pay → settle → served); revenue is demand you must earn (list it, seed the
Bazaar, tell agent devs). Demand is the GOAL, not a wall.

## Replication (the whole point)
Every install runs this same recipe with its OWN wallet + its OWN CDP/AgentMail creds. Self-funded
children run it on a FREE model ($0 compute) with their own empty-cred wallet. Same code, swap the model
and the creds → every AI on Earth can earn more than the human pays for it.
