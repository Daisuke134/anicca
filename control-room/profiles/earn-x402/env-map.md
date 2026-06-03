# profiles/earn-x402/env-map.md

> See `shared/security.md` for storage policy. Values are NEVER in this file.

## § 1. Env vars (names only)

| Key NAME | Required | Source | Used for |
|---|---|---|---|
| `BWS_ACCESS_TOKEN` | yes | `~/.openclaw/.env` | unlock Bitwarden vault |
| `OPENROUTER_API_KEY` | yes | Bitwarden vault | LLM calls for paid `/inference` and `/research` |
| `CDP_API_KEY_ID` | yes | Bitwarden vault | CDP auth |
| `CDP_API_KEY_SECRET` | yes | Bitwarden vault | CDP auth |
| `CDP_WALLET_SECRET` | yes | Bitwarden vault | smart wallet identifier |
| `CLOUDFLARED_TUNNEL_ID` | yes | Bitwarden vault | tunnel config |
| `CLOUDFLARED_TUNNEL_CREDS_JSON` | yes | Bitwarden vault → mounted as file `/etc/cloudflared/<id>.json` | tunnel auth |
| `CLOUDFLARE_API_TOKEN` | yes | Bitwarden vault | DNS routing + tunnel management |
| `X402_LISTENER_PORT` | optional | env override (default `18402`) | local HTTP listener bind port |
| `X402_BASE_URL` | yes | env (set at boot) | public URL = `https://<instance>.aniccaai.com` |
| `X402_PRICING_PATH` | optional | env override | default `~/.hermes/profiles/<instance>-earn-x402/x402-pricing.json` |
| `USDC_CONTRACT_BASE` | optional | env override | default `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |

## § 2. Identity reference

`earn-x402` does NOT read any file from `~/.openclaw/identity/`. The
wallet address is in `~/.hermes/profiles/<instance>-orch/wallet.json`
(written by `orch` at boot via AgentKit `createSmartAccount()`). No
operator PII enters this profile's flow.

## § 3. Pricing config schema

`~/.hermes/profiles/<instance>-earn-x402/x402-pricing.json`:

```json
{
  "paths": {
    "/research": { "price_usdc": "0.30", "ttl_sec": 60 },
    "/inference": { "price_usdc": "0.05", "ttl_sec": 30 },
    "/health": { "free": true }
  },
  "rate_limit": { "per_minute_per_ip": 100 },
  "discovery": { "list_in_registry": true, "registry_url": "https://x402.coinbase.com/services" }
}
```

The schema lives in `anicca-oss/skills/anicca-wallet-x402/pricing.schema.json`.

## § 4. Self-pay loop (OpenRouter topup)

When OpenRouter credit drops below threshold (default $1), `earn-x402`
triggers `anicca-fuel-broker`:

```
inputs:
  ANICCA_INSTANCE_NAME, wallet address (from orch/wallet.json),
  OPENROUTER_API_KEY (Bitwarden vault),
  topup amount (config, default 5 USDC)

action:
  POST https://openrouter.ai/api/v1/credits/topup
  body: { amount_usdc: 5, payment: <EIP-3009 sig> }

post:
  log to wallet-audit.log + x402-audit.log (label: self-topup)
  verify OpenRouter dashboard credit increased
```

The point: anicca-oss is **100% NHOSS-pure**. Operator never pays
OpenRouter. See `specs/07-HERMES-PIVOT.md` § 4.2.

## § 5. Cross-references

| Concept | Authority |
|---|---|
| Pricing schema | `anicca-oss/skills/anicca-wallet-x402/pricing.schema.json` |
| Self-pay rationale | `specs/07-HERMES-PIVOT.md` § 4.2 |
| OpenRouter topup API | `openrouter.ai/docs/api/credits/topup` |
| Vault policy | `control-room/shared/security.md` § 4 |

---

**END OF profiles/earn-x402/env-map.md.**
