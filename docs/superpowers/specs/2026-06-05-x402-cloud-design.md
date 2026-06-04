# x402-cloud (#324-W2-in-cloud) — Cloudflare Worker + agentic.market listing

## Goal
Real x402 earn endpoint on Cloudflare edge. Unlike Wave 1 (LOCAL :8403 self-signed
receipt prototype where signer == pay_to), Wave 2 verifies a **BUYER-signed** EIP-3009
`transferWithAuthorization` where `recovered_signer == from (BUYER) != pay_to (us)`.
List the route on agentic.market so real agentic buyers can pay 0.001 USDC on Base.

## Constants (mirror anicca-wallet/wallet_lib.py)
| key | value |
|---|---|
| pay_to (us) | `0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21` |
| Base chain_id | `8453` |
| USDC (Base) | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| price atomic | `1000` (0.001 USDC, 6 decimals) |

## Protocol (EIP-3009 transferWithAuthorization, the x402 standard)
The buyer signs an EIP-712 typed message authorizing a USDC transfer to us. This is the
real x402 facilitator-compatible shape (Coinbase x402 spec), NOT the Wave 1 custom receipt.

EIP-712 domain (USDC on Base — name/version/chainId/verifyingContract):
```
{ name: "USD Coin", version: "2", chainId: 8453, verifyingContract: <USDC> }
```
Primary type `TransferWithAuthorization`:
```
from address, to address, value uint256, validAfter uint256, validBefore uint256, nonce bytes32
```

## Receipt header shape (base64 JSON in `x-payment`)
```json
{ "protocol":"x402-exact-evm", "chain_id":8453, "verifying_contract":"<USDC>",
  "from":"<BUYER>", "to":"<PAY_TO>", "value_atomic":1000,
  "valid_after":0, "valid_before":<ts+3600>, "nonce":"0x<32 bytes>", "signature":"0x..." }
```

## Worker (services/x402-worker/index.ts) — endpoints
| route | behavior |
|---|---|
| GET /health | 200 `{ok:true}` |
| GET /paid (no x-payment) | 402 + WWW-Authenticate: x402 + x402-network/asset/amount/pay-to headers |
| GET /paid (x-payment) | verify → 200 `{ok,service,buyer,served_at}` or 402 `{error:"invalid_receipt", reason}` |

### Verification (all MUST pass)
1. base64-decodable JSON with all required fields
2. `to` == pay_to (us)
3. `chain_id` == 8453
4. `value_atomic` >= 1000
5. `valid_after <= now <= valid_before`
6. nonce unseen → write to NONCE_KV (TTL 24h); replay → 402
7. **recover EIP-712 signer == `from` (BUYER)** — the Wave-2 differentiator. A self-signed
   Wave-1 receipt (signer == pay_to == to, from absent/mismatch) is REJECTED.
8. (Wave 2.5 optional, env-gated) facilitator settle call — out of scope for E2E gate.

Signature recovery in the Worker uses `viem` (`recoverTypedDataAddress`), bundled by wrangler.

## Files
| file | purpose |
|---|---|
| `services/x402-worker/index.ts` | Worker fetch handler |
| `services/x402-worker/wrangler.toml` | name=anicca-x402, KV binding NONCE_KV |
| `services/x402-worker/package.json` | viem dep |
| `services/x402-worker/deploy.sh` | reads CLOUDFLARE_API_TOKEN, creates KV, `wrangler deploy`, writes deploy json |
| `services/x402-worker/list-on-agentic-market.sh` | validate + confirm Bazaar discovery (NO POST/api/listings — does not exist) |
| `services/x402-worker/tests/test_x402_cloud_e2e.sh` | 3-scenario E2E against deployed URL |
| `services/x402-worker/tests/sign_buyer_auth.py` | eth_account mock buyer signs EIP-3009 auth |

## E2E gate (3 scenarios)
1. GET /paid no header → **402** with all x402 headers.
2. GET /paid with Wave-1 self-signed receipt (signer==to) → **402 invalid_receipt**.
3. GET /paid with mock-buyer-signed EIP-3009 auth (signer==from!=to) → **200 ok**.

## agentic.market listing — CORRECTED (researched 2026-06-05)
- The spec's `POST /api/listings` does NOT exist. agentic.market is Coinbase's x402 **Bazaar**,
  a DISCOVERY layer ("Zero API keys"). A resource is listed automatically once it serves the
  correct x402 v2 PaymentRequirements body (`accepts[]` + `extensions.bazaar.info`) and the
  facilitator crawls/settles it. Sources: agentic.market/validate (Seller Tools),
  agentic.market/SKILL.md, x402-foundation/x402 docs/extensions/bazaar.mdx.
- So the Worker's 402 body was upgraded to the x402 v2 schema; `list-on-agentic-market.sh`
  validates via the validator API + confirms via the public search API. No API key needed.

## Credentials / HARD RULE #-1
- CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID absent from `~/.openclaw/.env` and `~/.hermes/.env`.
  → camofox autonomous signup at cloudflare.com (GOOGLE_LOGIN_EMAIL/PASSWORD) to create account +
  mint an API token, write to `~/.hermes/.env`. Do NOT ask Dais.
- Never echo token values.

## Secrets / /tmp
- tmp work → `~/.hermes/state/.tmp-*.$$`. Never /tmp.
- deploy json → `~/.hermes/state/x402-cloud-deploy.json`.
