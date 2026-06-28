# Behavioral Spec — x402-earn-endpoint-live (lean)

Date: 2026-06-28 · Builder: main agent (= I, per VCSDD role) · Mode: lean

## Goal (provable)
Stand up a DIFFERENTIATED x402 paid HTTP endpoint that is LIVE, publicly reachable, and DISCOVERABLE,
with payout to the founder wallet, and verify the full mechanism end-to-end with NO mock and NO fake
self-payment. Built on the existing `~/anicca/skills/earn/x402-sell/serve.mjs` (verified to exist).

`done =` all of R1–R7 verified by fresh evidence (V-R1..V-R7) AND adversary PASS AND my own external
curl of the public URL returns 200.

## Product decision (the model's call, not hardcoded)
- WHAT to sell: multi-source web-research brief (default product = Agent-Reach over Twitter/Reddit/
  YouTube/GitHub, $0 API fees). This is judgment/synthesis output (differentiated), not a commodity
  lookup. (If Agent-Reach is unavailable at build time, substitute an equally-differentiated product
  the running model CAN deliver — the spec is product-agnostic; R7 just requires real, relevant output.)
- PRICE: $0.10 USDC per call (cheap enough to sell, high enough to matter; A/B later).
- PAYTO: founder wallet `0x810f6d61f7606deee2657d3083e150a222bc29c5` (Base). Receiving needs NO key.
- HOST: local `serve.mjs` + a public tunnel (cloudflared) → stable public URL.

## Requirements (EARS)
- **R1** WHEN the launch command runs with `X402_PAYTO`=founder wallet + `X402_PRICE`, the system SHALL
  serve a free advertisement at `GET /` describing the product and the price.
- **R2** WHEN the paid route is requested WITHOUT payment, the system SHALL respond `402 Payment
  Required` with valid x402 payment requirements: network=base, asset=USDC, payTo=founder wallet,
  amount=price.
- **R3** WHEN the paid route is requested WITH a valid x402 payment, the system SHALL execute the
  product command and return its real output (no stub/mock).
- **R4** The running endpoint SHALL be reachable from the public internet via a tunnel (a stable
  https URL that returns 200 on `GET /` from an external fetch).
- **R5** The endpoint SHALL be discoverable: (a) serve a `/.well-known/x402` manifest, (b) be
  registered on x402scan, AND (c) be listed on ≥1 agent marketplace (Clustly service and/or a gigs
  api-monetization platform).
- **R6 (invariant / honesty)** Revenue counts ONLY when real USDC arrives from a real EXTERNAL buyer.
  The system SHALL NOT self-pay to simulate a sale (HARD 0.24). The VERIFIED claim is "mechanism live +
  discoverable + serves real value," NOT "earned $X." This boundary is stated explicitly in any report.
- **R7** The underlying product command SHALL return real, non-empty, query-relevant output when
  invoked directly with a real query.

## Verification architecture (1b) — how each requirement is proven (no-mock)
| Req | Check | Pass condition |
|---|---|---|
| R1 | `curl localhost:$PORT/` | 200; body contains price + product description |
| R2 | `curl localhost:$PORT/research?q=test` (no pay) | 402; JSON payment reqs; payTo==founder wallet, network base, asset USDC, amount==price |
| R3 | inspect serve.mjs payment-gating path | paid path calls the real product command (no stubbed result) |
| R4 | external `firecrawl/curl <public-tunnel-url>/` | 200 from outside the host |
| R5 | `curl <url>/.well-known/x402`; x402scan registration resp; Clustly `GET /services` | manifest served; registration acknowledged; service listed |
| R6 | grep launch+serve for self-pay/mock-sale path | none found (adversary confirms) |
| R7 | run product command directly with a real query | non-empty, query-relevant output |

## Purity boundary (1b)
- I/O (impure): HTTP server, child-process exec of product cmd, tunnel, network registration calls.
- Pure (testable in isolation): payment-requirement object construction, `/.well-known/x402` manifest
  construction, price parsing.

## Out of scope (honest)
- Generating actual revenue today (demand-gated; no real external buyers guaranteed — verified
  2026-06-28 that x402 buyer demand is thin). This feature delivers earning-CAPABILITY + discovery, not
  guaranteed income. Real first sale is tracked separately once a buyer calls.
- Self-paying to fake a sale (banned).

## Definition of Done (4-D)
spec ✓ (this file) · verification ✓ (V-R1..R7 fresh evidence) · impl ✓ (endpoint live + listed) ·
adversary PASS ✓ · my external-URL 200 check ✓.
