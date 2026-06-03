# profiles/earn-x402/backup.md

## § 1. What to back up

| Artifact | Path | Frequency | Retention |
|---|---|---|---|
| Pricing config | `~/.hermes/profiles/<instance>-earn-x402/x402-pricing.json` | on change | forever (versioned) |
| Profile config | `~/.hermes/profiles/<instance>-earn-x402/config.toml` | on change | forever |
| Soul | `~/.hermes/profiles/<instance>-earn-x402/soul.md` | on change | forever |
| Sessions DB | `~/.hermes/profiles/<instance>-earn-x402/sessions.db` | daily | 90 days |
| x402 audit log | `~/.hermes/logs/x402-audit.log` | daily | forever (= revenue history) |
| Wallet audit log | `~/.hermes/logs/wallet-audit.log` | daily | 365 days |
| Cloudflared tunnel creds JSON | `/etc/cloudflared/<tunnel-id>.json` | on rotation | secondary copy in Bitwarden vault |

## § 2. Where

| Destination | Use |
|---|---|
| Cloudflare R2 `anicca-instance-backup/<instance>/earn-x402/` | primary |
| Bitwarden vault (cloudflared creds JSON only) | rotation-safe |
| Daytona snapshot | tertiary fast restore |

## § 3. Backup script

```bash
#!/usr/bin/env bash
# ~/.hermes/skills/anicca-backup-earn-x402/daily.sh
set -euo pipefail
INSTANCE=${ANICCA_INSTANCE_NAME:-anicca-genesis}
TS=$(date -Iseconds)
TMP=$(mktemp -d)

cp ~/.hermes/profiles/${INSTANCE}-earn-x402/config.toml        $TMP/
cp ~/.hermes/profiles/${INSTANCE}-earn-x402/x402-pricing.json  $TMP/
cp ~/.hermes/profiles/${INSTANCE}-earn-x402/soul.md            $TMP/
cp ~/.hermes/profiles/${INSTANCE}-earn-x402/sessions.db        $TMP/
cp ~/.hermes/logs/x402-audit.log                                $TMP/
cp ~/.hermes/logs/wallet-audit.log                              $TMP/

tar -czf - -C $TMP . | age -r $(cat ~/.hermes/backup-pubkey.age) \
  > /tmp/${INSTANCE}-earn-x402-${TS}.tar.gz.age
rclone copyto /tmp/${INSTANCE}-earn-x402-${TS}.tar.gz.age \
  r2:anicca-instance-backup/${INSTANCE}/earn-x402/

# rotate: keep daily for 90d, weekly thereafter (handled by R2 lifecycle policy)
rm -rf $TMP /tmp/${INSTANCE}-earn-x402-${TS}.tar.gz.age
```

Scheduled via launchd plist `ai.anicca.backup.earn-x402.daily`.

## § 4. Restore

```bash
INSTANCE=anicca-genesis
LATEST=$(rclone lsf r2:anicca-instance-backup/${INSTANCE}/earn-x402/ | sort -r | head -1)

hermes -p earn-x402 -g "halt: stop listener, emergency restore"
cd /tmp/restore && rclone copy r2:anicca-instance-backup/${INSTANCE}/earn-x402/${LATEST} .
age -d -i ~/.hermes/backup-privkey.age $LATEST | tar -xzf -

mv ~/.hermes/profiles/${INSTANCE}-earn-x402/x402-pricing.json{,.pre-restore.$(date +%s)}
cp /tmp/restore/x402-pricing.json ~/.hermes/profiles/${INSTANCE}-earn-x402/
cp /tmp/restore/config.toml       ~/.hermes/profiles/${INSTANCE}-earn-x402/
cp /tmp/restore/soul.md           ~/.hermes/profiles/${INSTANCE}-earn-x402/
cp /tmp/restore/sessions.db       ~/.hermes/profiles/${INSTANCE}-earn-x402/

# audit logs are append-only; do NOT overwrite — concatenate and dedupe
cat /tmp/restore/x402-audit.log >> ~/.hermes/logs/x402-audit.log
# (consider a dedup step keyed by tx_hash if appending old data)

hermes profile start earn-x402
```

## § 5. NOT backed up

| Artifact | Why |
|---|---|
| Wallet private key | CDP HSM (never on disk) |
| Cloudflared tunnel ID itself | rebuildable via `cloudflared tunnel create` (creds change but tunnel name persists if recreated) |
| OpenRouter credit balance | reconciles via on-chain x402 topup history |

---

**END OF profiles/earn-x402/backup.md.**
