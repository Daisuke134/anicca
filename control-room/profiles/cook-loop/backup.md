# profiles/cook-loop/backup.md

## § 1. What to back up

| Artifact | Path | Frequency | Retention |
|---|---|---|---|
| Profile config | `~/.hermes/profiles/<instance>-cook-loop/config.toml` | on change | forever |
| Imitation targets | `~/.hermes/imitation-targets.jsonl` | on append | forever (append-only history) |
| Cook priors | `~/.hermes/cook-priors.json` | hourly | 30 days |
| Learned skills | `~/.hermes/skills/learned/` | on add | forever |
| Sessions DB | `~/.hermes/profiles/<instance>-cook-loop/sessions.db` | daily | 90 days |
| Soul | `~/.hermes/profiles/<instance>-cook-loop/soul.md` | on change | forever |
| Audit log | `~/.hermes/logs/cook-audit.log` | daily | forever (= imitation history) |

## § 2. Where

| Destination | Use |
|---|---|
| Cloudflare R2 `anicca-instance-backup/<instance>/cook-loop/` | primary |
| `anicca-oss` repo (= for community sharing of learned skills, opt-in) | optional, requires operator approval per-skill |

## § 3. Restore

Standard pattern (see `profiles/orch/backup.md` § 4). Special notes:

| File | Special |
|---|---|
| `imitation-targets.jsonl` | append-only; restore = concatenate, dedupe by `id` |
| `~/.hermes/skills/learned/` | careful — restoring old learned skills may conflict with current; review per skill |
| `cook-priors.json` | safe to overwrite; will re-adjust on next MEASURE cycle |

```bash
INSTANCE=anicca-genesis

hermes -p cook-loop -g "halt: emergency restore"

LATEST=$(rclone lsf r2:anicca-instance-backup/${INSTANCE}/cook-loop/ | sort -r | head -1)
rclone copy r2:anicca-instance-backup/${INSTANCE}/cook-loop/${LATEST} /tmp/restore/
age -d -i ~/.hermes/backup-privkey.age /tmp/restore/${LATEST} | tar -xzf - -C /tmp/restore

# imitation-targets: concatenate + dedupe
cat /tmp/restore/imitation-targets.jsonl ~/.hermes/imitation-targets.jsonl \
  | jq -c -s 'unique_by(.id) | sort_by(.id) | .[]' \
  > /tmp/imitation-merged.jsonl
mv /tmp/imitation-merged.jsonl ~/.hermes/imitation-targets.jsonl

# cook-priors: overwrite
cp /tmp/restore/cook-priors.json ~/.hermes/

# learned skills: operator review per skill
diff -r /tmp/restore/learned/ ~/.hermes/skills/learned/
# operator decides what to merge

hermes profile start cook-loop
```

## § 4. NOT backed up

| Artifact | Why |
|---|---|
| `/tmp/cook-workspaces/<id>/` | ephemeral; re-clone if needed |

---

**END OF profiles/cook-loop/backup.md.**
