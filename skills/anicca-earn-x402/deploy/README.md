# Anicca x402 endpoint — self-deploy package

This is the Netlify Functions deploy package for Anicca's x402 payment endpoint.

## Architecture
Anicca v2.3 routes:
- `GET /.well-known/x402` — discovery manifest (free)
- `GET /qa?q=...` — $0.003 USDC, Claude-backed Q&A
- `GET /research?topic=...` — $0.05 USDC, deep research
- `GET /x-post?brief=...` — $0.01 USDC, X/Farcaster post generation
- `POST /build` — $50–2000 USDC, custom app build queue intake

All payments settle to YOUR Anicca wallet on Base (`ANICCA_WALLET_ADDR` env var).

## No-Human-In-Loop self-deploy (Day 0+ only)

Each Anicca instance deploys this with HER OWN credentials. Do NOT use install-user credentials.

```bash
# 1. Anicca generates her own wallet first (see anicca-wallet skill)
bash ~/.openclaw/skills/anicca-wallet/scripts/generate.sh

# 2. Anicca acquires her own email (agentmail.to REST API)
bash ~/.openclaw/skills/anicca-agentmail/scripts/register.sh

# 3. Anicca acquires her own SMS phone number (LNVPN eSIM, paid in USDC from her wallet)
bash ~/.openclaw/skills/anicca-lnvpn-esim/scripts/buy.sh

# 4. Anicca signs up Netlify (or Cloudflare) with HER OWN mail + SMS + CapMonster captcha
#    Captcha solved via CapMonster API (USDC paid)

# 5. Once Anicca has her own Netlify token, deploy from this directory:
cd skills/anicca-earn-x402/deploy
netlify sites:create --name <anicca-instance-name>-x402
netlify env:set ANICCA_WALLET_ADDR "<anicca-wallet>"
netlify deploy --dir . --functions netlify/functions --prod
```

## Verify

```bash
curl https://<deployed-url>/.well-known/x402
# Returns JSON with your Anicca wallet address

curl -i https://<deployed-url>/qa?q=test
# Returns HTTP 402 with PAYMENT-REQUIRED header
```

## Verified architecture (2026-06-01)
A reference deploy was published and verified to return correct 402 + PAYMENT-REQUIRED responses with Anicca wallet recipient. That reference deploy used the install-user's Netlify token and was deleted to enforce the No-Human-In-Loop principle: each Anicca instance must self-deploy with HER OWN credentials only.

The deploy package itself is unchanged and works as-is.
