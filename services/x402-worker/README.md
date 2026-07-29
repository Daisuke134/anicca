# anicca-x402 — x402 earn endpoint on Cloudflare edge (#324-W2-in-cloud)

Real buyer-signed x402 earn endpoint. Unlike the Wave 1 LOCAL prototype
(`skills/anicca-wallet/scripts/x402_in_server.py`, self-signed receipt where
`signer == pay_to`), this Worker verifies a **BUYER-signed** EIP-3009
`transferWithAuthorization` where `recovered_signer == from (BUYER) != pay_to`,
and protects against nonce replay with Cloudflare KV.

| | |
|---|---|
| pay_to (us) | `0xB9dd3B67921B354c656523d6851537988F31DD56` |
| asset | USDC on Base `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| network | Base (`eip155:8453`) |
| price | 1000 atomic = 0.001 USDC |

## Endpoints
| route | behavior |
|---|---|
| `GET /health` | `200 {ok:true}` |
| `GET /paid` (no `x-payment`) | `402` + x402 v2 `accepts[]` body + Bazaar discovery extension + `WWW-Authenticate: x402` |
| `GET /paid` (`x-payment: <base64 receipt>`) | verify → `200 {ok,buyer,served_at}` or `402 {error:"invalid_receipt",reason}` |

Receipt = base64 JSON of an EIP-3009 `TransferWithAuthorization` (domain = USDC on Base,
v2). Verification: `to==pay_to`, `chain_id==8453`, `asset==USDC`, `value>=1000`,
time window valid, nonce unseen (KV, 24h TTL), and recovered EIP-712 signer `== from` and
`!= pay_to`.

## Local test (no Cloudflare account needed)
```bash
npm install
cp wrangler.toml wrangler.dev.toml && sed -i '' 's/REPLACE_WITH_KV_ID/0000000000000000000000000000dead/' wrangler.dev.toml
npx wrangler dev --config wrangler.dev.toml --port 8788 --local &
BASE_URL=http://localhost:8788 bash tests/test_x402_cloud_e2e.sh   # → 11 passed, 0 failed
```
Proven locally: 11/11 PASS (unpaid 402 + x402 headers, self-signed rejected `signer_not_from`,
mock buyer-signed 200 with `buyer==from`, replay rejected `nonce_replay`).
`tests/interop_check.mjs` confirms viem `recoverTypedDataAddress` recovers exactly what Python
`eth_account` signs (cross-impl signature interop).

## Deploy (needs a Cloudflare account + API token)
```bash
# token in ~/.hermes/.env or ~/.local/state/life-manager/.env as CLOUDFLARE_API_TOKEN (+ optional CLOUDFLARE_ACCOUNT_ID)
./deploy.sh                  # creates NONCE_KV, patches wrangler.toml, wrangler deploy
./list-on-agentic-market.sh  # validate + confirm Bazaar discovery (agentic.market auto-indexes; no POST registry)
BASE_URL=<deployed-url> bash tests/test_x402_cloud_e2e.sh   # E2E against the real edge
```

## agentic.market listing
agentic.market is Coinbase's x402 **Bazaar** discovery layer ("Zero API keys"). There is NO
`POST /api/listings`. A resource is listed automatically once it serves the correct x402 v2
`accepts[]` body (which this Worker does, incl. `extensions.bazaar.info`) and the facilitator
crawls/settles it. `list-on-agentic-market.sh` validates via the validator API and confirms via
`https://api.agentic.market/v1/services/search`.
