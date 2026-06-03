# profiles/earn-autohedge/backup.md

## § 1. What to back up

| Artifact | Path | Frequency | Retention |
|---|---|---|---|
| Profile config | `~/.hermes/profiles/<instance>-earn-autohedge/config.toml` | on change | forever |
| Autohedge config | `~/.hermes/profiles/<instance>-earn-autohedge/autohedge-config.json` | on change | forever |
| Open positions | `~/.hermes/profiles/<instance>-earn-autohedge/positions.json` | every 5 min | 30 days |
| Sessions DB | `~/.hermes/profiles/<instance>-earn-autohedge/sessions.db` | daily | 90 days |
| Soul | `~/.hermes/profiles/<instance>-earn-autohedge/soul.md` | on change | forever |
| Audit log | `~/.hermes/logs/autohedge-audit.log` | daily | 365 days (= PnL history) |

## § 2. Where

| Destination | Use |
|---|---|
| Cloudflare R2 `anicca-instance-backup/<instance>/earn-autohedge/` | primary |
| Daytona snapshot | fast restore |

## § 3. Restore (positions.json is critical)

If `positions.json` is corrupted or lost, the profile cannot safely
calculate PnL or risk size. Restore procedure:

```bash
INSTANCE=anicca-genesis

# 1. halt
hermes -p earn-autohedge -g "halt: emergency restore"

# 2. fetch latest backup
LATEST=$(rclone lsf r2:anicca-instance-backup/${INSTANCE}/earn-autohedge/ | sort -r | head -1)
rclone copy r2:anicca-instance-backup/${INSTANCE}/earn-autohedge/${LATEST} /tmp/restore/
age -d -i ~/.hermes/backup-privkey.age /tmp/restore/${LATEST} | tar -xzf - -C /tmp/restore

# 3. reconcile with on-chain truth (CRITICAL — backup may be 5-min stale)
hermes -p earn-autohedge -g "reconcile: compare /tmp/restore/positions.json with on-chain wallet state, output diff, do NOT apply yet"

# 4. operator reviews diff, then approves
hermes -p earn-autohedge -g "apply reconciled positions.json from /tmp/restore, log to autohedge-audit.log as restore-from-backup"

# 5. resume
hermes profile start earn-autohedge
```

## § 4. NOT backed up

| Artifact | Why |
|---|---|
| Wallet private key | CDP HSM |
| Allocation cap value | comes from env at boot |

---

**END OF profiles/earn-autohedge/backup.md.**
