# anicca-heartbeat

Minimal Hermes skill that fires every 30 minutes to prove the Anicca genesis body is alive. It writes one JSONL line per fire to `~/.hermes/state/heartbeat.jsonl` containing the timestamp, the provider/model in use, and the SHA-256 of the live constitution. No outbound network calls. Wired by `2026-06-04-hermes-genesis-boot` plan; see `specs/00-MASTER.md` § GROUND TRUTH.

## Post-merge swap (Wave 1 only)

This Wave 1 install points two runtime paths at the development worktree:
- `~/.hermes/skills/anicca-heartbeat` → `.../.worktrees/p1-hermes-boot/skills/anicca-heartbeat`
- `~/.hermes/scripts/anicca-heartbeat.sh` (wrapper) execs `.../.worktrees/p1-hermes-boot/skills/anicca-heartbeat/scripts/heartbeat.sh`

After `feat/p1-hermes-boot` merges to `main` and the worktree is removed, the worktree paths vanish and `hermes cron` will silently produce no JSONL row. Re-point both:

```bash
ln -sfn /Users/operator/anicca-oss/skills/anicca-heartbeat /Users/operator/.hermes/skills/anicca-heartbeat
sed -i '' 's#/Users/operator/anicca-oss/.worktrees/p1-hermes-boot/skills/anicca-heartbeat/scripts/heartbeat.sh#/Users/operator/anicca-oss/skills/anicca-heartbeat/scripts/heartbeat.sh#' /Users/operator/.hermes/scripts/anicca-heartbeat.sh
```

Verify with: `/Users/operator/.hermes/scripts/anicca-heartbeat.sh` (should append one JSONL row with `ok:true`).
