# SWITCHOVER — build-loop-unify (TODO #4)

**Not executed. Documentation only, per this feature's constraint ("実 launchd 操作禁止").**
Read `specs/behavioral-spec.md` REQ-000 first — it is the corrected finding this whole
document depends on.

## TL;DR

There is only **one** launchd job whose command chain ever invokes `claude`:
`ai.anicca.claude-p-mainloop` → `skills/self/claude-p-mainloop.sh`. `ai.anicca.founder-loop-cadence`
→ `skills/self/founder-loop/founder-loop.sh` invokes **zero** `claude` calls — it is a
deterministic ledger writer (`record-earn.mjs`) + a Python bandit capital allocator
(`ceo/run_pass.py`), not a second BUILD-loop cadence.

**Required launchd action: none.** "build loop = 1 launchd job" (the outcome TODO #4 asks
for) is already true today. No `launchctl unload`/`load` is required to reach it.

## What actually changed in this worktree

| File | Change |
|---|---|
| `skills/self/claude-p-mainloop.sh` | Added `CLAUDE_P_MAINLOOP_MODEL` override (default `sonnet`, unchanged); added `CLAUDE_P_MAINLOOP_TEST`+3 dir/file vars test-isolation seam (default paths unchanged when unset) |
| `skills/self/claude-p-mainloop-prompt.txt` | Added one paragraph making the LOOP B boundary explicit: never earn/simulate an earn action, wallet+ledger (not this loop's own report) is the only earn-truth |
| `skills/self/test-claude-p-mainloop.sh` (new) | RED→GREEN oracle for the above, safe to run repeatedly against production (never touches the live pidfile — verified via mtime check, see `evidence/green-phase.txt`) |

Because the default values of every new env var are unchanged, **this diff is safe to
merge to `main` with zero cron changes** — the live `ai.anicca.claude-p-mainloop` job will
behave byte-identically (still `claude --model sonnet`, still the same pidfile/log/workdir
paths) the next time it fires, whether or not `CLAUDE_P_MAINLOOP_MODEL`/`CLAUDE_P_MAINLOOP_TEST`
are ever set in its environment (they currently are not, per the live plist at
`/Users/anicca/Library/LaunchAgents/ai.anicca.claude-p-mainloop.plist`).

## If a real second BUILD-loop cron is ever added later

If a future change genuinely adds a second `claude --model ... -p ...` cron (i.e. REQ-000's
premise becomes true), this is the switchover recipe to fold it into one job — run these
from an interactive shell, one at a time, only after this worktree's changes are on `main`
and fresh-context adversary + this feature's own tests are green on that second script too:

```bash
# 1. Confirm which job is being retired and which stays (never run this blind):
launchctl list | grep ai.anicca.<new-second-build-loop-label>
cat ~/Library/LaunchAgents/ai.anicca.<new-second-build-loop-label>.plist

# 2. Unload the retired job FIRST (stops new fires; in-flight run finishes on its own):
launchctl unload ~/Library/LaunchAgents/ai.anicca.<new-second-build-loop-label>.plist

# 3. Remove its plist only after confirming no run is mid-flight
#    (pidfile for that job absent / kill -0 on its pid fails):
rm ~/Library/LaunchAgents/ai.anicca.<new-second-build-loop-label>.plist

# 4. The surviving job (ai.anicca.claude-p-mainloop) needs NO reload — it already exists
#    and already covers the unified role once its prompt is updated to also do the
#    retired job's OBSERVE step (or that step is added as an early line in
#    claude-p-mainloop-prompt.txt).

# 5. Verify: `launchctl list | grep anicca` shows exactly one claude-invoking job,
#    and its next scheduled fire produces a log line in
#    ~/.openclaw/logs/claude-p-mainloop.out.log covering both roles.
```

This recipe is written for a *hypothetical future* duplicate — it is **not** applicable to
`founder-loop-cadence` today (see TL;DR: that job is not a BUILD loop and must stay on its
own 30-min cadence per REQ-001, which protects wallet-reconciliation freshness).

## Recommendation to the parent / doc owner

`docs/loop-engineering/27-ideal-earn-record-verify-architecture.md` lines 45, 91, and 114
assert a "mainloop(6h) + founder-loop(30min)" claude-cadence duplication that this
session's code read (grep + find, reproducible — see `specs/behavioral-spec.md` REQ-000
evidence block) disproves. Recommend the doc be corrected to: TODO #4 status =
**already satisfied** (single build-loop cron confirmed by code read), with the LOOP-B
role-purity work (prompt boundary language) delivered as a real improvement on top, not a
cron merge.
