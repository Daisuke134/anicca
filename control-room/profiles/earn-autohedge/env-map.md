# profiles/earn-autohedge/env-map.md

## § 1. Env vars

| Key NAME | Required | Source | Used for |
|---|---|---|---|
| `BWS_ACCESS_TOKEN` | yes | `~/.openclaw/.env` | vault unlock |
| `OPENROUTER_API_KEY` | yes | Bitwarden vault | LLM call for trade decision |
| `CDP_API_KEY_ID` | yes | Bitwarden vault | sign Base tx |
| `CDP_API_KEY_SECRET` | yes | Bitwarden vault | sign Base tx |
| `CDP_WALLET_SECRET` | yes | Bitwarden vault | wallet identifier |
| `BASE_RPC_URL` | optional | env override | default `https://mainnet.base.org` |
| `SOLANA_RPC_URL` | optional | env override | default `https://api.mainnet-beta.solana.com` (or Helius) |
| `JUPITER_API_URL` | optional | env override | default `https://quote-api.jup.ag/v6` |
| `ONEINCH_API_KEY` | yes | Bitwarden vault | 1inch swap rate limit bump (free tier OK to start) |
| `AUTOHEDGE_BANKROLL_CAP_USDC` | yes | env (set per instance) | e.g., `50` — never exceed |
| `AUTOHEDGE_MAX_DRAWDOWN_PCT` | optional | env override | default `10` (= 10% per 24h triggers circuit breaker) |

## § 2. Identity

No PII. The wallet address is the only identity used (read from
`~/.hermes/profiles/<instance>-orch/wallet.json`).

## § 3. Allocation config

`~/.hermes/profiles/<instance>-earn-autohedge/autohedge-config.json`:

```json
{
  "bankroll_cap_usdc": 50,
  "allowlisted_pairs": ["USDC/SOL", "USDC/ETH"],
  "max_position_pct": 25,
  "stop_loss_pct": 5,
  "take_profit_pct": 10,
  "max_drawdown_pct_24h": 10,
  "halt_on_circuit_breaker": true
}
```

If `bankroll_cap_usdc` is exceeded by any single position, the trade is
refused at the L2 skill layer.

## § 4. Cross-references

| Concept | Authority |
|---|---|
| Vault policy | `control-room/shared/security.md` § 4 |
| Bankroll allocation | `anicca-oss/skills/anicca-fuel-broker/SKILL.md` |
| AutoHedge risk config | `~/.openclaw/skills/anicca-autohedge/vendor/risk_manager.py` |

---

**END OF profiles/earn-autohedge/env-map.md.**
