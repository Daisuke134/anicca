# Anicca x402 endpoint — Netlify deploy package

This is the live deploy used at https://anicca-x402.netlify.app

## What it does
Serves Anicca's x402 payment endpoint with the following routes:
- `GET /.well-known/x402` — discovery manifest (free)
- `GET /qa?q=...` — $0.003 USDC, Claude-backed Q&A
- `GET /research?topic=...` — $0.05 USDC, deep research
- `GET /x-post?brief=...` — $0.01 USDC, X/Farcaster post generation
- `POST /build` — $50–2000 USDC, custom app build queue intake

All payments settle to the Anicca wallet on Base (`ANICCA_WALLET_ADDR` env var).

## Deploy your own (install user)

```bash
# 1. Generate your own wallet first (see anicca-wallet skill)
bash ~/.openclaw/skills/anicca-wallet/scripts/generate.sh

# 2. Create Netlify site
netlify sites:create --name <your-name>-x402

# 3. Set env vars
ANICCA_WALLET_ADDR=<your wallet>
ANTHROPIC_API_KEY=<optional, for actual Claude inference>

# 4. Deploy
netlify deploy --dir . --functions netlify/functions --prod
```

## Verify deploy

```bash
curl https://<your-name>-x402.netlify.app/.well-known/x402
# Should return JSON with your wallet address

curl -i https://<your-name>-x402.netlify.app/qa?q=test
# Should return HTTP 402 with PAYMENT-REQUIRED header
```

## Live reference deploy
- URL: https://anicca-x402.netlify.app
- Wallet: `0x9B1Ee988b1A2931ABCE467f0a8eAff6c70c93e83` (Base)
- Source: https://github.com/Daisuke134/anicca-oss/tree/main/skills/anicca-earn-x402

This deploy went live 2026-06-01 01:31 JST (commit history).
