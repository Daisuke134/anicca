---
name: anicca-wallet
description: Anicca's self-custody wallet on Base mainnet + minimal x402 protocol primitives (Wave 1 — signer + local IN prototype). Reads the canonical Anicca private key from ~/.automaton/wallet.json (address 0xa3CDd4Ec...), queries USDC + ETH balance via Base RPC, signs EIP-3009 transferWithAuthorization payloads (x402 OUT DRY-RUN ONLY — does NOT broadcast and does NOT call any x402 paid-service / facilitator), and serves a local x402 IN PROTOTYPE on port 8403 that issues 402 Payment Required challenges and accepts self-signed receipts (signer == pay_to). This is NOT a production earn endpoint — no buyer wallet, no facilitator verification, no EIP-3009 settlement, no on-chain transfer proof. Real x402 OUT pay-services + real buyer-signed IN flow + on-chain settlement are tracked as Wave 2 follow-on tasks (#324-W2-pay-dryrun, #324-W2-pay-live, #324-W2-in-buyer, #324-W2-in-cloud). Use this skill ONLY for read-only balance probes, signed-but-unbroadcast x402 OUT payloads, and the local x402 IN receipt prototype. The private key is loaded via wallet_lib at one chokepoint and never printed.
metadata:
  type: foundation-identity
  spec: anicca-oss/specs/00-MASTER.md § 1.0, anicca-oss/specs/16-RUNTIME-CODE-TRUTH.md § 17, anicca-oss/specs/09-EARN-X402-LIVE.md
  wave: 1
  parallel_safe: true
  requires:
    bins: [python3, jq, curl]
    python_packages: [eth_account>=0.13.0]
    files: [~/.automaton/wallet.json]
---

# anicca-wallet (Wave 1 — signer + local IN prototype)

## What it does
Foundation skill for Anicca's on-chain identity. Three primitives — sized honestly for Wave 1:

1. **balance probe** (`scripts/balance.sh`) — read-only USDC + ETH on Base for `0xa3CDd4Ec…`.
2. **x402 OUT (pay) — dry-run signer ONLY** (`scripts/x402_out_dry_run.py`) — sign an EIP-3009 USDC
   `transferWithAuthorization` payload off-chain. Dry-run only: prints the signature + recovered signer;
   does NOT broadcast and does NOT call any x402 paid-service / facilitator. A real x402 OUT pay-services
   flow is the Wave 2 follow-on `#324-W2-pay-dryrun` (sandbox facilitator) + `#324-W2-pay-live` (gated
   live $0.001 broadcast with on-chain verification).
3. **x402 IN (earn) — local single-wallet receipt PROTOTYPE** (`scripts/x402_in_server.py`) — minimal
   HTTP server on `127.0.0.1:8403` that returns `402 Payment Required` with proper x402 headers and `200`
   once a self-signed EIP-712 receipt verifies (signer == pay_to). **Not a production earn endpoint**:
   no buyer wallet, no facilitator verification, no EIP-3009 settlement, no on-chain transfer proof.
   The negative test `tests/test_x402_in_negative.sh` proves an ephemeral-key-signed receipt (hostile
   buyer who learns `pay_to` but does not own the key) is rejected with `402 invalid receipt`.
   Real buyer-signed flow + on-chain settlement = Wave 2 follow-on `#324-W2-in-buyer`. Cloudflare Worker
   port + agentic.market listing = `#324-W2-in-cloud`.

## How it's invoked
- `hermes cron` fires `scripts/balance_watch.sh` every 1 hour to append a JSONL row to
  `~/.hermes/state/wallet-balance.jsonl`.
- `scripts/x402_out_dry_run.py --to <addr> --amount-usdc <n>` is called on-demand by future earn /
  payout skills to produce a signed payload.
- `scripts/x402_in_server.py --port 8403` is started on-demand (Wave 1 is local-only; Wave 2 / #325
  replaces it with a Cloudflare Worker).

## Failure mode
If `~/.automaton/wallet.json` is missing or derives to the wrong address, every script aborts with
a clear error and writes nothing. The 1-hour cron has `--no-agent`, so a single failure is silent
(no LLM cost) and the next tick retries.

## Constitutional invariant
The private key from `~/.automaton/wallet.json` is loaded only inside `wallet_lib.load_signer()` and
released by the function returning a `LocalAccount` (not the key string). It is never printed,
logged, written to JSONL, passed via argv, or echoed into environment variables.
