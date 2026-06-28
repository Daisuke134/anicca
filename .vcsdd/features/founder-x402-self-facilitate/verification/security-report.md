# Security Hardening Report — founder-x402-self-facilitate (Phase 5, lean)

Date: 2026-06-28 · Sprint: 1 · Mode: lean · Status: PASS

## Tooling

- `grep -rE '@coinbase/x402|CDP_API_KEY|x402\.org/facilitator|RAILWAY_|DATABASE_URL|OPENAI_API_KEY|@prisma/client'`
  over `apps/x402-agents/src/`: 0 matches (PROP-007 Tier-0, asserted by test suite).
- `npm audit --omit=dev` on the cleaned `apps/x402-agents/package.json`: dependency surface reduced
  to 8 direct deps (was 14). All are widely-used, MIT-licensed packages with no known
  high-severity CVEs at install time (re-audit before each merge).
- Hardcoded secret scan: no private-key, API-key, or wallet-mnemonic literals in source
  (`EVM_PRIVATE_KEY` is read only via `process.env`; the test fixture key is a synthetic
  all-hex string, never a real key).

## Threat model snapshot

| Surface | Threat | Mitigation |
|---|---|---|
| `EVM_PRIVATE_KEY` env | leakage via logs / errors | `validateEnv` previews only first 6 hex chars + length; settle errors log `[x402.settle.error]` with sanitized message + code only (no key bytes). |
| `X402_RPC_URL` | malicious RPC could lie about balance / blocks | impl uses the env-supplied URL as-is; deployments should pin to a trusted Base mainnet RPC. NFR-004 gas probe failure mode is non-fatal (server boots, signals `gas_ready:false`). |
| settle path | replay across networks | scheme registered only for `eip155:8453`; cross-network signatures rejected by the x402 exact-scheme verifier (SDK-enforced). |
| HTTP DoS | bot buyer flood | `express-rate-limit` (`windowMs: 60s, max: 30`) applies before paid routes. |
| CORS preflight | wrong header set blocks legit buyers | `allowedHeaders: ['Content-Type','Authorization','X-PAYMENT']` + `exposedHeaders: ['X-PAYMENT-RESPONSE']` matches x402 spec exactly. |
| Buyer-facing 5xx | retry storms | wrapSettle logs + rethrows; SDK responds with its 402 (verified against installed @x402/express 2.17.0). |

## Summary

No high-severity exposures found in sprint-1 scope. The seller surface is narrow (one paid
endpoint, one chain, one asset, no DB, no upstream model deps). Tier-2 children inherit the
same hardening through the Mother Curriculum (`docs/superpowers/specs/2026-06-28-mother-doctrine-and-spawn-automation.md`
§5). Re-audit at sprint-2 (post-host) for live-deployment-specific concerns (rate limits at
the tunnel layer, RPC pinning, secret rotation cadence).
