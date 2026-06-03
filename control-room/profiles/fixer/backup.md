# profiles/fixer/backup.md

## § 1. What to back up

| Artifact | Path | Frequency | Retention |
|---|---|---|---|
| Profile config | `~/.hermes/profiles/<instance>-fixer/config.toml` | on change | forever |
| Sessions DB | `~/.hermes/profiles/<instance>-fixer/sessions.db` | daily | 90 days |
| Soul | `~/.hermes/profiles/<instance>-fixer/soul.md` | on change | forever |
| Learned skills (after-action library) | `~/.hermes/skills/learned/` | on add (= file watcher) | **forever** |
| Fixer audit log | `~/.hermes/logs/fixer-audit.log` | daily | 365 days |
| Verify audit log | `~/.hermes/logs/verify-audit.log` | daily | 365 days |
| Escalation audit log | `~/.hermes/logs/escalation-audit.log` | daily | forever |

## § 2. Where

| Destination | Use |
|---|---|
| Cloudflare R2 `anicca-instance-backup/<instance>/fixer/` | primary |
| `anicca-oss` repo (= for sharing high-value learned skills to other colonies) | optional, operator-curated |

## § 3. Restore

Standard pattern. Special:

| File | Special |
|---|---|
| `learned/` skills | concatenate + dedupe by filename; operator reviews diff for any contradictory rules |

```bash
INSTANCE=anicca-genesis

hermes -p fixer -g "halt: emergency restore"

LATEST=$(rclone lsf r2:anicca-instance-backup/${INSTANCE}/fixer/ | sort -r | head -1)
rclone copy r2:anicca-instance-backup/${INSTANCE}/fixer/${LATEST} /tmp/restore/
age -d -i ~/.hermes/backup-privkey.age /tmp/restore/${LATEST} | tar -xzf - -C /tmp/restore

# learned/ skills: merge carefully (no auto-overwrite)
diff -rq /tmp/restore/learned/ ~/.hermes/skills/learned/
# operator merges file by file, resolving conflicts via cook-loop MEASURE decision

cp /tmp/restore/config.toml ~/.hermes/profiles/${INSTANCE}-fixer/
cp /tmp/restore/soul.md     ~/.hermes/profiles/${INSTANCE}-fixer/
cp /tmp/restore/sessions.db ~/.hermes/profiles/${INSTANCE}-fixer/

hermes profile start fixer
```

## § 4. NOT backed up

| Artifact | Why |
|---|---|
| `/tmp/fix-workspaces/<id>/` | ephemeral |

---

**END OF profiles/fixer/backup.md.**
