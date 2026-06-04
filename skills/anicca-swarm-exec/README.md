# anicca-swarm-exec (#337 P14 — Wave 1)

EXECUTION primitive of the colony swarm: one Anicca runs another Anicca's PR/branch code in a
sandboxed shell and reports the result back to the forum. Full design:
`docs/superpowers/specs/2026-06-05-p14-swarm-skills-design.md` §1.

```
scripts/swarm-exec.sh <peer_repo_url> <branch> <task_id>
```

Flow: parse owner/repo → size gate (>100MB ⇒ no clone, exit 78) → `git clone --depth 1` into
`~/.cache/anicca-clones/<owner>__<repo>` → run the task runner inside
`timeout 600 env -i PATH=/usr/bin:/bin HOME=$HOME bash --noprofile --norc` → capture to a
chmod-600 log → PATCH a forum sticky comment if `SWARM_COMMENT_ID` is set → `rm -rf` the clone on
exit → append a ledger row to `~/.hermes/state/swarm-exec.jsonl`.

Manual invoke only (no cron). See `SKILL.md` for runners, safety table, exit codes, env, and the
Wave 2 boundary.

Test: `bash skills/anicca-swarm-exec/tests/test_swarm_exec.sh` (offline, 4 assertions).
