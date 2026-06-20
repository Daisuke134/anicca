---
name: earn/x402-sell
description: Sell a capability for USDC over HTTP (x402) — a TOOL. YOU decide what to sell, the price, and how to create demand.
---

# earn/x402-sell — get paid in USDC for doing something people want

This is the X402 PRODUCT pillar — the only one that creates NEW value instead of moving capital. It is
a TOOL, not a product. **You are an intelligence; you decide WHAT to sell, for HOW MUCH, and HOW to get
buyers.** `serve.mjs` only makes "receive USDC over HTTP for doing X" a one-command primitive.

Why this is the trillion-dollar lever: at $0 compute (free model), every sale is PURE PROFIT. Demand is
the GOAL, not a wall — the whole job of an intelligence is to build what people want. Do not treat "no
buyers yet" as a wall; treat it as the work: find a real need, serve it, price it, tell people.

## The tool
```
X402_PRICE='$0.05' X402_PAYTO=<your wallet> node serve.mjs   # stands up a paid HTTP endpoint
# default product = web research via Agent-Reach (Twitter/Reddit/YouTube/GitHub, $0 API fees)
# the model can sell ANYTHING by setting X402_PRODUCT_CMD='<cmd with {q}>'
```
- `GET /` (free) advertises what's for sale + the price, so buyers/agents can discover it.
- `GET /research?q=...` returns 402 Payment Required until the caller pays `X402_PRICE` USDC on Base,
  then runs the product and returns the result. Receiving needs NO key — only your wallet address.

## Your job (the decisions the tool does NOT make)
1. DECIDE the product. What do people actually want that you can deliver? Web research is the default,
   but you might sell: a curated digest, a monitoring feed, a data extract, an analysis, a generated
   asset — whatever you can do well and others will pay for. Use Agent-Reach to find what's in demand.
2. DECIDE the price. Cheap enough to sell, high enough to matter. You can A/B it.
3. CREATE demand. List the endpoint where buyers (humans or other agents) look: post it on the GitHub
   Issues social, Dais's socials, agent marketplaces (MoltX Social, x402 directories). Make it easy to
   find and obviously useful. This is the real work; the code is done.
4. HOST it so buyers can reach it. Cloud anicca = a public URL; locally use a tunnel for a real buyer.
5. RECORD each sale (real USDC received) and share what sold + at what price so other Anicca copy/adapt.

## Honesty rule
A sale counts only when REAL USDC arrives from a REAL buyer. Paying yourself to fake a sale is banned
(HARD RULE 0.24). The verified part is the mechanism (402 → pay → served); the revenue is demand you
must earn.

## Why no fixed product/price here
Each Anicca picks a different product, price, and audience → diversified revenue across the colony
(HARD RULE #0). Tool + onboarding, never the decision.
