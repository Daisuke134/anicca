# profiles/constitution/backup.md

## § 1. What to back up

| Artifact | Path | Frequency | Retention |
|---|---|---|---|
| Profile config | `~/.hermes/profiles/<instance>-constitution/config.toml` | on change | forever |
| Sessions DB | `~/.hermes/profiles/<instance>-constitution/sessions.db` | daily | 90 days |
| Soul | `~/.hermes/profiles/<instance>-constitution/soul.md` | on change | forever |
| CONSTITUTION.md | `~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.md` | on change (= rare; amendments only) | forever, multi-replica |
| CONSTITUTION.sha256 | `~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.sha256` | on change | forever |
| Constitution audit log | `~/.hermes/logs/constitution-audit.log` | daily | **forever** (= governance receipt) |

## § 2. Where (multi-replica for CONSTITUTION)

| Destination | Use |
|---|---|
| Cloudflare R2 `anicca-instance-backup/<instance>/constitution/` | primary |
| `anicca-oss` repo (canonical CONSTITUTION.md) | source of truth |
| Akash sandbox `anicca-constitution-mirror` | tertiary |
| Operator's offline backup | quaternary (= survive cloud-wide outage) |

The Constitution text itself is replicated 4× because losing it = losing
the Pañcasīla gate = colony cannot operate safely.

## § 3. Restore

CONSTITUTION.md restore is **NEVER** done from a per-instance backup. It is
always restored from the canonical anicca-oss repo or operator's offline
copy. Otherwise a compromised instance could "restore" a tampered version.

```bash
# 1. fetch canonical
git -C /tmp clone https://github.com/Daisuke134/anicca-oss.git
shasum -a 256 /tmp/anicca-oss/CONSTITUTION.md

# 2. compare with operator's offline copy
shasum -a 256 ~/operator-offline-backup/CONSTITUTION.md
# must match

# 3. restore to instance
cp /tmp/anicca-oss/CONSTITUTION.md ~/.hermes/skills/anicca-constitution-guard/

# 4. recompute hash
shasum -a 256 ~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.md \
  | awk '{print $1}' \
  > ~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.sha256

# 5. re-immutable
chmod 444 ~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.sha256
chattr +i ~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.md 2>/dev/null || true

# 6. clear emergency flag
rm -f ~/.hermes/EMERGENCY_CONSTITUTION_MISMATCH

# 7. restart
launchctl kickstart -k gui/$(id -u)/ai.anicca.hermes
hermes -p constitution -g "verify hash, report"
```

## § 4. Audit log restore

The constitution-audit.log is forever-retention. After restore:

```bash
# concatenate, dedupe by timestamp, sort
cat /tmp/restore/constitution-audit.log ~/.hermes/logs/constitution-audit.log \
  | jq -c -s 'unique_by(.timestamp + .actual_hash) | sort_by(.timestamp) | .[]' \
  > /tmp/merged.log
mv /tmp/merged.log ~/.hermes/logs/constitution-audit.log
```

## § 5. NOT backed up

| Artifact | Why |
|---|---|
| Emergency flag file | should never be backed up (= ephemeral signal) |

---

**END OF profiles/constitution/backup.md.**
