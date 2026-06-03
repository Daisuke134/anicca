# profiles/earn-bittensor/env-map.md

## § 1. Env vars

| Key NAME | Required | Source | Used for |
|---|---|---|---|
| `BWS_ACCESS_TOKEN` | yes | `~/.openclaw/.env` | vault unlock |
| `OPENROUTER_API_KEY` | yes | Bitwarden vault | LLM for subnet selection / decision |
| `BITTENSOR_WALLET_PASSWORD` | yes | Bitwarden vault | encrypt TAO keystore |
| `BITTENSOR_WALLET_NAME` | yes | env per instance | e.g., `anicca-genesis-tao` |
| `BITTENSOR_ENDPOINT` | optional | env override | default `wss://entrypoint-finney.opentensor.ai:443` |
| `BITTENSOR_BANKROLL_CAP_USDC` | yes | env per instance | TAO position max value, e.g., `25` |
| `BITTENSOR_SUBNET_ALLOWLIST` | optional | env override | comma-separated UIDs |
| `KRAKEN_API_KEY` | conditional | Bitwarden vault | only if using Kraken for TAO ↔ USDC |
| `KRAKEN_API_SECRET` | conditional | Bitwarden vault | same |

## § 2. TAO wallet keystore

The Bittensor TAO wallet keystore lives at
`~/.hermes/profiles/<instance>-earn-bittensor/bittensor-wallet/` and is
encrypted with `BITTENSOR_WALLET_PASSWORD`. Permissions chmod 600.

| Why keystore is on-disk (vs CDP HSM model) | Bittensor SDK requires local keystore for signing; no managed HSM option (yet) |
| Mitigation | password lives in Bitwarden vault, not on disk; backup keystore is age-encrypted in R2 |

## § 3. Cross-references

| Concept | Authority |
|---|---|
| Bittensor wallet pattern | `docs.bittensor.com/getting-started/wallets` |
| Vault policy | `control-room/shared/security.md` § 4 |
| Backup of keystore | `profiles/earn-bittensor/backup.md` § 1 |

---

**END OF profiles/earn-bittensor/env-map.md.**
