# profiles/orch/env-map.md

> Lists which env vars `orch` reads. Values are NEVER in this file — see
> `shared/security.md` for storage policy. Raw values live in
> `~/.openclaw/.env` (chmod 600) bootstrap + Bitwarden vault runtime.

## § 1. Env vars (names only)

| Key NAME | Required | Source | Used for |
|---|---|---|---|
| `BWS_ACCESS_TOKEN` | yes | `~/.openclaw/.env` (bootstrap) | unlock Bitwarden vault on daemon start |
| `OPENROUTER_API_KEY` | yes | Bitwarden vault | LLM calls (Kimi K2.6 primary + fallback chain) |
| `CDP_API_KEY_ID` | yes | Bitwarden vault | wallet balance check + sign (delegated to `earn-x402` for tx, `orch` only reads) |
| `CDP_API_KEY_SECRET` | yes | Bitwarden vault | wallet auth |
| `CDP_WALLET_SECRET` | yes | Bitwarden vault | smart wallet identifier |
| `DAYTONA_API_TOKEN` | yes | Bitwarden vault | spawn child sandboxes via `anicca-spawn-controller` |
| `HERMES_PROFILE_DIR` | optional | env override | default = `~/.hermes/profiles/` |
| `HERMES_LOG_DIR` | optional | env override | default = `~/.hermes/logs/` |
| `HERMES_KANBAN_DB` | optional | env override | default = `~/.hermes/kanban.db` |
| `ANICCA_INSTANCE_NAME` | yes | set at sandbox boot | e.g., `anicca-genesis`, `anicca001` |
| `ANICCA_COLONY_LEDGER` | optional | env override | default = `~/.hermes/colony.json` |

## § 2. Identity reference (PII isolation)

`orch` does NOT read any file from `~/.openclaw/identity/`. The only
reference allowed is `~/.openclaw/identity/INDEX.md` (= a pointer table
that documents what PII files exist), and even that is only consulted by
the operator manually, not by the daemon.

| Why not | Detail |
|---|---|
| Operator legal name | private companion only |
| Bank account number | NHOSS-irrelevant (Anicca operates on USDC) |
| マイナンバー | NHOSS-irrelevant |
| Card last4 | NHOSS-irrelevant |
| Personal Gmail / phone | NHOSS-irrelevant |

If a goal arrives that requires PII (e.g., "transfer to MUFG account"),
`orch` MUST reject with `category=ops, status=failed, error="PII required;
private companion repo handles this"`. This is enforced by spec 07 § 9
anti-goals.

## § 3. Vault read pattern

```python
# orch profile reads vault at daemon boot, then refreshes every 60s tick
from bitwarden_secrets import Client
bw = Client(access_token=os.environ['BWS_ACCESS_TOKEN'])
secrets = bw.secrets.list(project='anicca-oss-public')
env = {s.key: s.value for s in secrets}
# env now has OPENROUTER_API_KEY, CDP_*, DAYTONA_API_TOKEN
# never written to disk; lives in process memory only
```

If `BWS_ACCESS_TOKEN` is invalid or vault unreachable:

| Severity | Action |
|---|---|
| First fail | retry with exponential backoff (max 3 attempts) |
| 3 fails in a row | emit `vault-down` event to `daemon.err`, continue with cached values from previous tick |
| 60 min unreachable | halt instance (Constitution Article 3: can't operate blind on a wallet) |

## § 4. Env-leak protection

| Layer | Protection |
|---|---|
| `os.environ` dump | filtered via `hermes_state.py` — keys matching `*_KEY*`, `*_SECRET*`, `*_TOKEN*`, `*_PASSWORD*` are redacted in any log output |
| LLM prompt | system prompt template explicitly redacts; if a tool returns a value matching a secret pattern, it's replaced with `<REDACTED>` |
| Crash dump | `~/.hermes/logs/daemon.err` rotation script greps for `eyJ...` (JWT pattern), `sk_...`, `0x[0-9a-f]{64}`, replaces with `<REDACTED>` |

## § 5. Cross-references

| Concept | Authority |
|---|---|
| Vault policy | `control-room/shared/security.md` § 4 |
| Bootstrap token | `control-room/shared/security.md` § 5 |
| PII isolation | `control-room/shared/security.md` § 6 |
| Identity INDEX.md | `~/.openclaw/identity/INDEX.md` (LOCAL, not in OSS repo) |
| Spawn controller env | `anicca-oss/skills/anicca-spawn-controller/SKILL.md` |
| Bitwarden Secrets Manager | `bitwarden.com/products/secrets-manager` |

---

**END OF profiles/orch/env-map.md.**
