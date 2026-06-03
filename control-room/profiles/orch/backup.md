# profiles/orch/backup.md

> Backup and restore procedure for the `orch` profile state. Critical
> because `orch` owns the Kanban DB (shared with all 10 profiles) + the
> colony ledger + the wallet address index.

## § 1. What to back up

| Artifact | Path | Frequency | Retention |
|---|---|---|---|
| Kanban DB | `~/.hermes/kanban.db` | hourly | 30 days rolling |
| Sessions DB | `~/.hermes/profiles/<instance>-orch/sessions.db` | daily | 90 days |
| Profile config | `~/.hermes/profiles/<instance>-orch/config.toml` | on change | forever (versioned) |
| Profile soul | `~/.hermes/profiles/<instance>-orch/soul.md` | on change | forever (versioned) |
| Wallet address index | `~/.hermes/profiles/<instance>-orch/wallet.json` | on change | forever (versioned) — address only, no privkey |
| Colony ledger | `~/.hermes/colony.json` | on change | forever (append-only) |
| Constitution hash record | `~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.sha256` | on change | forever (must match parent) |
| Audit logs | `~/.hermes/logs/*-audit.log` | daily | per `shared/security.md` § 8 |

## § 2. Where (backup destinations)

| Destination | Use case |
|---|---|
| Cloudflare R2 bucket `anicca-instance-backup` | primary — encrypted-at-rest, $0.015/GB/mo |
| Akash sandbox `anicca-backup-mirror` | secondary — paid in USDC, fully NHOSS |
| Daytona snapshot | tertiary — fast restore, sandbox-local |
| operator-supplied SFTP / SSH target | optional override (set via `BACKUP_TARGET_URL` env) |

## § 3. Backup runbook (hourly)

```bash
#!/usr/bin/env bash
# ~/.hermes/skills/anicca-backup-orch/hourly.sh
set -euo pipefail

INSTANCE=${ANICCA_INSTANCE_NAME:-anicca-genesis}
TS=$(date -Iseconds)
TMP=$(mktemp -d)

# 1. snapshot Kanban (online backup via SQLite .backup)
sqlite3 ~/.hermes/kanban.db ".backup '$TMP/kanban.db'"

# 2. include sessions + config + soul + wallet address
cp ~/.hermes/profiles/${INSTANCE}-orch/sessions.db   $TMP/
cp ~/.hermes/profiles/${INSTANCE}-orch/config.toml   $TMP/
cp ~/.hermes/profiles/${INSTANCE}-orch/soul.md       $TMP/
cp ~/.hermes/profiles/${INSTANCE}-orch/wallet.json   $TMP/
cp ~/.hermes/colony.json                              $TMP/

# 3. tar + encrypt (age, OSS-friendly)
tar -czf - -C $TMP . | age -r $(cat ~/.hermes/backup-pubkey.age) > /tmp/${INSTANCE}-orch-${TS}.tar.gz.age

# 4. upload to R2
rclone copyto /tmp/${INSTANCE}-orch-${TS}.tar.gz.age r2:anicca-instance-backup/${INSTANCE}/orch/

# 5. rotate (keep last 30 days)
rclone delete --min-age 720h r2:anicca-instance-backup/${INSTANCE}/orch/

# 6. cleanup
rm -rf $TMP /tmp/${INSTANCE}-orch-${TS}.tar.gz.age
```

Schedule via launchd plist `ai.anicca.backup.orch.hourly`.

## § 4. Restore procedure

If the orch profile state is corrupted (Kanban DB lost, sessions lost,
colony ledger lost, etc.):

```bash
INSTANCE=anicca-genesis
LATEST=$(rclone lsf r2:anicca-instance-backup/${INSTANCE}/orch/ | sort -r | head -1)

# 1. halt the instance
hermes -p orch -g "halt: emergency restore in progress"
launchctl unload ~/Library/LaunchAgents/ai.anicca.hermes.plist

# 2. fetch + decrypt
mkdir -p /tmp/restore && cd /tmp/restore
rclone copy r2:anicca-instance-backup/${INSTANCE}/orch/${LATEST} .
age -d -i ~/.hermes/backup-privkey.age $LATEST | tar -xzf -

# 3. backup current state first (in case restore is wrong choice)
mv ~/.hermes/kanban.db ~/.hermes/kanban.db.pre-restore.$(date +%s)
mv ~/.hermes/profiles/${INSTANCE}-orch ~/.hermes/profiles/${INSTANCE}-orch.pre-restore.$(date +%s)

# 4. restore files
mkdir -p ~/.hermes/profiles/${INSTANCE}-orch
cp /tmp/restore/kanban.db    ~/.hermes/kanban.db
cp /tmp/restore/sessions.db  ~/.hermes/profiles/${INSTANCE}-orch/
cp /tmp/restore/config.toml  ~/.hermes/profiles/${INSTANCE}-orch/
cp /tmp/restore/soul.md      ~/.hermes/profiles/${INSTANCE}-orch/
cp /tmp/restore/wallet.json  ~/.hermes/profiles/${INSTANCE}-orch/
cp /tmp/restore/colony.json  ~/.hermes/

# 5. verify Constitution hash unchanged
shasum -a 256 ~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.md

# 6. restart
launchctl load ~/Library/LaunchAgents/ai.anicca.hermes.plist
sleep 5
hermes status
hermes profile list
```

## § 5. Disaster recovery (whole instance lost, e.g., sandbox destroyed)

```
parent (anicca-genesis):
  └─ detects anicca001 sandbox missing for > 60 min
  └─ executes templates/new-instance.md provisioning with name=anicca001-restored
  └─ on first boot, anicca001-restored fetches its latest backup from R2
  └─ restores Kanban + sessions + wallet address
  └─ CDP wallet privkey is in CDP HSM — not lost (smart wallet address persists)
  └─ verify hash match with parent
  └─ register in colony.json: { "name": "anicca001-restored", "restored_from": "anicca001" }
```

## § 6. What is NOT backed up

| Artifact | Why not |
|---|---|
| Wallet private key | lives in Coinbase CDP HSM (never on disk) |
| `BWS_ACCESS_TOKEN` | rotation-on-restore is cheaper than risking a leaked backup |
| OpenRouter credit | balance reconciles via on-chain USDC topup history |
| Daytona sandbox image | rebuildable from `Dockerfile`; not state |

## § 7. Cross-references

| Concept | Authority |
|---|---|
| Audit log retention | `control-room/shared/security.md` § 8 |
| age encryption tool | `github.com/FiloSottile/age` (OSS) |
| rclone | `rclone.org` (OSS, R2-compatible) |
| Daytona snapshot | `docs.daytona.io/snapshots` |
| Constitution propagation (must hash match) | `specs/00-MASTER.md` § 6.3 |

---

**END OF profiles/orch/backup.md.**
