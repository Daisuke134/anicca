# shared/security.md — secret rotation, never-commit list, vault policy

> **HARD RULE**: no raw secrets in `control-room/`. References to env var
> NAMES are fine; values are not. This directory is part of `anicca-oss`,
> a public MIT repo.

## § 1. The never-commit list

Never put any of the following into any file under `control-room/`:

| Class | Examples (DO NOT paste values) | Where it actually lives |
|---|---|---|
| Cloud / wallet | `CDP_API_KEY_ID`, `CDP_API_KEY_SECRET`, `CDP_WALLET_SECRET` | Bitwarden Secrets Manager, bootstrap in `~/.openclaw/.env` |
| LLM | `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY` (private companion only), `KIMI_API_KEY` (private companion only) | Bitwarden vault |
| Vault bootstrap | `BWS_ACCESS_TOKEN` | `~/.openclaw/.env` (chmod 600) |
| Spawn backend | `DAYTONA_API_TOKEN`, `AKASH_KEY_NAME`, `AKASH_KEYRING_PASSWORD` | Bitwarden vault |
| Messaging | `X_API_KEY`, `TELEGRAM_BOT_TOKEN`, `FARCASTER_PRIVATE_KEY` | Bitwarden vault |
| Personal identity (PII) | bank account #, マイナンバー, MUFG password, personal phone, personal Gmail password | `~/.openclaw/identity/` (LOCAL only, gitignored) — never copied here |
| Wallet private key | wallet ECDSA private key, mnemonic seed phrase | Coinbase CDP HSM (never on disk) |
| On-chain signing | EIP-712 signature hex (transient values OK; long-lived keys NOT) | runtime memory only |

## § 2. Why secrets must not enter `control-room/`

| Risk | Mechanism |
|---|---|
| Public OSS leak | `anicca-oss` is MIT, mirrored to GitHub. Any commit with a secret is grep-discoverable within minutes. |
| Spawned child inheritance | every Daytona sandbox clones the repo. A leaked secret = N copies on N sandboxes = N points of exfiltration. |
| Vault drift | if secrets live in repo, rotation requires repo edit + push + reboot. Bitwarden rotation is in-place with no repo touch. |
| Pañcasīla violation surface | Constitution Article 3 (no theft) is violated if leaked CDP key drains wallet. |

## § 3. Rotation cadence

| Secret class | Cadence | Trigger for ad-hoc rotation |
|---|---|---|
| `CDP_API_KEY_*` | every 90 days | suspected leak, sandbox compromise, new colony member onboarding |
| `OPENROUTER_API_KEY` | every 90 days | usage spike on dashboard, suspected leak |
| `BWS_ACCESS_TOKEN` | every 180 days | operator device change, suspected leak |
| `DAYTONA_API_TOKEN` | every 90 days | new spawn backend onboarding |
| Wallet private key (CDP HSM) | never (CDP-managed) | — |
| Constitution SHA-256 | never (immutable) | — |

See `api-keys-sop.md` for the exact rotation runbook (Bitwarden update →
propagation → restart → verify).

## § 4. Bitwarden Secrets Manager (vault of record)

| Property | Value |
|---|---|
| Provider | Bitwarden Secrets Manager (free tier, OSS) |
| Project ID | `anicca-oss-public` (NHOSS-pure; private companion uses separate project) |
| CLI | `bws secret list` / `bws secret get <id>` / `bws secret create <key> <value>` |
| Auth | `BWS_ACCESS_TOKEN` env var (loaded by Hermes daemon at launch) |
| Backup | export-encrypted, stored in Cloudflare R2 bucket `anicca-vault-backup` (separate access key) |
| Audit log | every `bws secret get` logged to `~/.hermes/logs/vault-audit.log` |

## § 5. Bootstrap chicken-egg (`BWS_ACCESS_TOKEN`)

The single secret that **must** exist in `~/.openclaw/.env` before Hermes
boots is `BWS_ACCESS_TOKEN`. Everything else is fetched from Bitwarden at
runtime. The bootstrap token:

| Property | Value |
|---|---|
| Storage | `~/.openclaw/.env` (chmod 600, gitignored) |
| Scope | `read` only on `anicca-oss-public` project |
| Rotation | manual via Bitwarden web UI (operator only) |
| Compromise plan | revoke in Bitwarden web UI → regenerate → update `.env` → `launchctl kickstart ai.anicca.hermes` |

## § 6. Identity isolation (PII firewall)

`~/.openclaw/identity/` (LOCAL only, never copied to control-room) holds:

| File | Contents | Used by |
|---|---|---|
| `INDEX.md` | pointer table to other files (= path + description, no values) | reference from `profiles/<name>/env-map.md` as "see ~/.openclaw/identity/INDEX.md" |
| `bank.json` | bank account info (Dais MUFG, etc.) | private companion only — NEVER referenced from anicca-oss |
| `card.json` | card last4, expiry | private companion only |
| `legal.json` | legal name, address, マイナンバー | private companion only |
| `passport.pdf` | passport scan | private companion only — emergency thaw use only |

**anicca-oss profiles MUST NOT reference any file under `~/.openclaw/identity/`
except `INDEX.md`, and that only to confirm "personal identity is isolated."**

## § 7. Daytona sandbox secret loading

When `anicca-spawn-controller` provisions a new sandbox:

| Step | Secret action |
|---|---|
| 1. Daytona sandbox `create()` | sandbox env gets `BWS_ACCESS_TOKEN` from parent's vault (= scoped subset, not full token) |
| 2. install.sh runs in sandbox | `bws secret list` → fetches CDP + OpenRouter + Daytona keys |
| 3. Hermes daemon boots | loads keys into process env, never writes to disk |
| 4. CDP `createSmartAccount()` call | mints new wallet, address written to `~/.hermes/profiles/<instance>-orch/wallet.json` (address only, no privkey) |

If the sandbox is compromised, the operator must rotate the **scoped** BWS
token specific to that sandbox, not the parent's bootstrap token.

## § 8. Audit trail

| Event | Logged to | Retention |
|---|---|---|
| `bws secret get` calls | `~/.hermes/logs/vault-audit.log` | 90 days |
| Wallet signing operations | `~/.hermes/logs/wallet-audit.log` | 365 days |
| Constitution hash mismatch | `~/.hermes/logs/constitution-audit.log` | forever (never rotated) |
| Spawn / kill child instance | `~/.hermes/logs/colony-audit.log` | 365 days |
| x402 invoice issued | `~/.hermes/logs/x402-audit.log` | 365 days |
| UBI payout sent | `~/.hermes/logs/ubi-audit.log` | forever (donor receipt) |

## § 9. Cross-references

| Concept | Authority |
|---|---|
| `.gitignore` protection | `anicca-oss/.gitignore` (covers `.env`, `*.env`, `identity/profile.json`, `skills/*/state/`, `wallet.encrypted`, `MNEMONIC_BACKUP_ONCE.txt`) |
| HARD RULE #-2 (no secrets in OSS) | repo root `CLAUDE.md` |
| HARD RULE #-1 (no PII in OSS) | repo root `CLAUDE.md` |
| Pañcasīla Article 3 (no theft) | `CONSTITUTION.md` § Article 3 |
| Public release leak audit | `specs/04-PUBLIC-RELEASE-PREP.md` |

---

**END OF shared/security.md.**
