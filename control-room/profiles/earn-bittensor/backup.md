# profiles/earn-bittensor/backup.md

## § 1. What to back up

| Artifact | Path | Frequency | Retention |
|---|---|---|---|
| TAO wallet keystore (encrypted) | `~/.hermes/profiles/<instance>-earn-bittensor/bittensor-wallet/` | on creation + on rotation | forever (= losing this loses TAO) |
| Profile config | `~/.hermes/profiles/<instance>-earn-bittensor/config.toml` | on change | forever |
| Subnet positions | `~/.hermes/profiles/<instance>-earn-bittensor/subnet-positions.json` | hourly | 30 days |
| Sessions DB | `~/.hermes/profiles/<instance>-earn-bittensor/sessions.db` | daily | 90 days |
| Soul | `~/.hermes/profiles/<instance>-earn-bittensor/soul.md` | on change | forever |
| Audit log | `~/.hermes/logs/bittensor-audit.log` | daily | forever (= yield history) |

## § 2. Where

| Destination | Use |
|---|---|
| Cloudflare R2 `anicca-instance-backup/<instance>/earn-bittensor/` | primary |
| Bitwarden vault (keystore secondary) | extra redundancy for TAO wallet |

## § 3. TAO wallet keystore — CRITICAL

The TAO wallet is the only on-disk private key in this Anicca instance
(USDC wallet is in CDP HSM; this is the exception per spec 07 § 3.2 limits).

| Risk | Mitigation |
|---|---|
| Sandbox compromise → keystore stolen | encrypted with `BITTENSOR_WALLET_PASSWORD` (password in Bitwarden) |
| Sandbox destroyed → keystore lost | age-encrypted backup in R2 + secondary copy in Bitwarden vault |
| Operator loses Bitwarden access | TAO lost; document mnemonic at wallet creation in operator's own offline backup (= one-time manual step) |

## § 4. Restore

```bash
INSTANCE=anicca-genesis

hermes -p earn-bittensor -g "halt: emergency restore"

# fetch latest backup
LATEST=$(rclone lsf r2:anicca-instance-backup/${INSTANCE}/earn-bittensor/ | sort -r | head -1)
rclone copy r2:anicca-instance-backup/${INSTANCE}/earn-bittensor/${LATEST} /tmp/restore/
age -d -i ~/.hermes/backup-privkey.age /tmp/restore/${LATEST} | tar -xzf - -C /tmp/restore

# restore keystore (CRITICAL)
mv ~/.hermes/profiles/${INSTANCE}-earn-bittensor/bittensor-wallet \
   ~/.hermes/profiles/${INSTANCE}-earn-bittensor/bittensor-wallet.pre-restore.$(date +%s)
cp -r /tmp/restore/bittensor-wallet ~/.hermes/profiles/${INSTANCE}-earn-bittensor/
chmod -R 600 ~/.hermes/profiles/${INSTANCE}-earn-bittensor/bittensor-wallet

# restore other state
cp /tmp/restore/config.toml             ~/.hermes/profiles/${INSTANCE}-earn-bittensor/
cp /tmp/restore/subnet-positions.json   ~/.hermes/profiles/${INSTANCE}-earn-bittensor/
cp /tmp/restore/soul.md                 ~/.hermes/profiles/${INSTANCE}-earn-bittensor/
cp /tmp/restore/sessions.db             ~/.hermes/profiles/${INSTANCE}-earn-bittensor/

# verify keystore unlocks
hermes -p earn-bittensor -g "verify TAO wallet unlocks with current vault password, report address + balance"

# restart
hermes profile start earn-bittensor
```

## § 5. NOT backed up

| Artifact | Why |
|---|---|
| `BITTENSOR_WALLET_PASSWORD` | rotation pattern; password lives in vault, not in backup tarball |

---

**END OF profiles/earn-bittensor/backup.md.**
