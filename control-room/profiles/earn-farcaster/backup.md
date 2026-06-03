# profiles/earn-farcaster/backup.md

## § 1. What to back up

| Artifact | Path | Frequency | Retention |
|---|---|---|---|
| Profile config | `~/.hermes/profiles/<instance>-earn-farcaster/config.toml` | on change | forever |
| Persona | `~/.hermes/profiles/<instance>-earn-farcaster/persona.md` | on change | forever |
| Frame config | `~/.hermes/profiles/<instance>-earn-farcaster/frame-config.json` | on change | forever |
| Sessions DB | `~/.hermes/profiles/<instance>-earn-farcaster/sessions.db` | daily | 90 days |
| Soul | `~/.hermes/profiles/<instance>-earn-farcaster/soul.md` | on change | forever |
| Audit log | `~/.hermes/logs/farcaster-audit.log` | daily | 365 days |

## § 2. Where

| Destination | Use |
|---|---|
| Cloudflare R2 `anicca-instance-backup/<instance>/earn-farcaster/` | primary |

## § 3. Restore

Standard pattern (see `profiles/orch/backup.md` § 4). After restore:

```bash
# verify Neynar signer still valid
hermes -p earn-farcaster -g "verify FARCASTER_SIGNER_UUID still authorized; test cast (do not publish, dry-run only)"
```

If signer was revoked during downtime, the operator must generate a new
managed signer via Neynar dashboard and update the vault. Casts will not
publish until then.

## § 4. NOT backed up

| Artifact | Why |
|---|---|
| Farcaster FID | persisted at Farcaster Hub (= on-chain registry); restorable from username lookup |
| Signer UUID | rotation-on-restore via vault |
| Follower list | reconstructable via Neynar query |

---

**END OF profiles/earn-farcaster/backup.md.**
