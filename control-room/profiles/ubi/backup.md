# profiles/ubi/backup.md

## § 1. What to back up

| Artifact | Path | Frequency | Retention |
|---|---|---|---|
| Profile config | `~/.hermes/profiles/<instance>-ubi/config.toml` | on change | forever |
| Recipients allowlist | `~/.hermes/ubi-recipients.json` | on change | forever (versioned) |
| Allocation config | `~/.hermes/ubi-allocation.json` | on change | forever |
| OFAC cached list | `~/.hermes/ofac-list/` | daily | last 30 days (= audit trail of "list was current at payout time") |
| Sessions DB | `~/.hermes/profiles/<instance>-ubi/sessions.db` | daily | 90 days |
| Soul | `~/.hermes/profiles/<instance>-ubi/soul.md` | on change | forever |
| Audit log | `~/.hermes/logs/ubi-audit.log` | daily | **forever** (= donor receipt) |

## § 2. Where

| Destination | Use |
|---|---|
| Cloudflare R2 `anicca-instance-backup/<instance>/ubi/` | primary |
| Secondary Akash sandbox `anicca-ubi-mirror` | tertiary (legal-grade durability) |

## § 3. Restore

Standard pattern (see `profiles/orch/backup.md` § 4). Special notes:

| File | Special |
|---|---|
| `ubi-audit.log` | append-only; do NOT overwrite; concatenate + dedupe by tx_hash |
| `ubi-recipients.json` | operator-curated; restore but show diff to operator before activating |
| OFAC list | safe to overwrite or refresh-on-restart |

```bash
INSTANCE=anicca-genesis

hermes -p ubi -g "halt: emergency restore"

LATEST=$(rclone lsf r2:anicca-instance-backup/${INSTANCE}/ubi/ | sort -r | head -1)
rclone copy r2:anicca-instance-backup/${INSTANCE}/ubi/${LATEST} /tmp/restore/
age -d -i ~/.hermes/backup-privkey.age /tmp/restore/${LATEST} | tar -xzf - -C /tmp/restore

# audit log: concatenate, dedupe by tx_hash
cat /tmp/restore/ubi-audit.log ~/.hermes/logs/ubi-audit.log \
  | jq -c -s 'unique_by(.tx_hash) | sort_by(.timestamp) | .[]' \
  > /tmp/ubi-merged.log
mv /tmp/ubi-merged.log ~/.hermes/logs/ubi-audit.log

# recipients allowlist: review diff
diff /tmp/restore/ubi-recipients.json ~/.hermes/ubi-recipients.json
# operator confirms which version to keep
cp /tmp/restore/ubi-recipients.json ~/.hermes/  # or skip

cp /tmp/restore/ubi-allocation.json ~/.hermes/
cp /tmp/restore/config.toml         ~/.hermes/profiles/${INSTANCE}-ubi/
cp /tmp/restore/soul.md             ~/.hermes/profiles/${INSTANCE}-ubi/
cp /tmp/restore/sessions.db         ~/.hermes/profiles/${INSTANCE}-ubi/

# refresh OFAC list (do not restore from backup — could be stale-sanctioned)
hermes -p ubi -g "refresh OFAC list now from home.treasury.gov"

hermes profile start ubi
```

## § 4. NOT backed up

| Artifact | Why |
|---|---|
| OPERATOR_DIVIDEND_USDC_ADDRESS env value | per-instance env, set at boot from vault |
| Wallet private key | CDP HSM |

---

**END OF profiles/ubi/backup.md.**
