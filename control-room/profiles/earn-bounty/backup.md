# profiles/earn-bounty/backup.md

## § 1. What to back up

| Artifact | Path | Frequency | Retention |
|---|---|---|---|
| Profile config | `~/.hermes/profiles/<instance>-earn-bounty/config.toml` | on change | forever |
| Filter config | `~/.hermes/profiles/<instance>-earn-bounty/bounty-filter.json` | on change | forever |
| Active PRs | `~/.hermes/profiles/<instance>-earn-bounty/active-prs.json` | every 15 min | 30 days |
| Sessions DB | `~/.hermes/profiles/<instance>-earn-bounty/sessions.db` | daily | 90 days |
| Soul | `~/.hermes/profiles/<instance>-earn-bounty/soul.md` | on change | forever |
| Bounty audit log | `~/.hermes/logs/bounty-audit.log` | daily | 365 days |

## § 2. Where

| Destination | Use |
|---|---|
| Cloudflare R2 `anicca-instance-backup/<instance>/earn-bounty/` | primary |

## § 3. Restore

Standard restore pattern (see `profiles/orch/backup.md` § 4). Special note
for `active-prs.json`:

```bash
# after restore, reconcile with GitHub truth
hermes -p earn-bounty -g "reconcile active-prs.json with GitHub API: for each PR, check current state (open/merged/closed); update local file."
```

## § 4. NOT backed up

| Artifact | Why |
|---|---|
| `/tmp/bounty-workspaces/<id>/` | ephemeral; re-clone if needed |
| GitHub token | rotation-on-restore via vault |

---

**END OF profiles/earn-bounty/backup.md.**
