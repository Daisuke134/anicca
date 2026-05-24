---
name: anicca-core
description: "Anicca's self-management infrastructure — the Sutando-faithful core the autonomous beat depends on: core-status (liveness/step), read-quota (per-beat tier), health-check (self-diagnose + --fix), core-heartbeat (per-host .alive beacon), sync-memory (cross-machine). Called by HEARTBEAT.md each beat."
metadata:
  tags: autonomous, heartbeat, self-diagnose, quota, liveness, memory-sync, sutando
  requires:
    bins: [python3, bash, git, launchctl, hostname]
    env: [ANICCA_HOME]
---

# anicca-core

The infrastructure the autonomous beat (`workspace/HEARTBEAT.md`) stands on.
Ported faithfully from Sutando (`sonichi/sutando`): the loop *brain* was already
ours; this skill is the *body* — liveness, quota-awareness, self-repair, memory.

All scripts resolve paths from `$ANICCA_HOME` (default `~/.openclaw`); workspace
is `$ANICCA_HOME/workspace`. Nothing is hardcoded — the OSS mirror in
`anicca-oss/` reads the same env so any install runs unchanged.

## The five components (what each beat uses)

| script | when in the beat | what it does |
|---|---|---|
| `core-status.sh {running\|step\|idle\|read}` | step 0 (start), throughout, step 5 (end) | writes `workspace/core-status.json` = single truth of "alive + current step". stale-while-running = stuck-loop signal |
| `read-quota.py [--json\|--gate]` | step 1 (orient) | per-beat tier FULL/MEDIUM/LIGHT/MINIMAL. claude -p reads quota-state.json; OpenClaw/GPT path → FULL |
| `health-check.py [--fix\|--json\|--emit-task]` | step 2 (MUST chores / self-heal) | gateway alive + launchd loaded + critical files + memory index + stuck-loop + core liveness. `--fix` reloads launchd / restarts gateway. `--emit-task` queues unfixable failures for step 3 |
| `core-heartbeat.py [--once\|--status TAG]` | launchd-supervised, not per-beat | per-host `state/cores/<host>-<tag>.alive` beacon. lets self-diagnose see which cores (claude / openclaw / macbook) are alive across the fleet |
| `sync-memory.sh` | cron every 10-30min | Claude memory ↔ private repo (`ANICCA_MEMORY_REPO`), mtime-wins + content guard, machine-`<host>/` one-way backup. Mac Mini ↔ MacBook |

## Wiring (already applied to HEARTBEAT.md)

```
beat start ─→ core-status running ─→ read-quota (tier) ─→ read PERSONAL_CLAUDE menu
   ─→ health-check --fix --emit-task ─→ pick highest-ROI (step3) ─→ act
   ─→ build_log += 1 line ─→ pending-questions if blocked ─→ core-status idle ─→ #metrics report
```

`workspace/PERSONAL_CLAUDE.md` (gitignored) holds the per-user **Current Work
Menu** that HEARTBEAT.md §3 anchors to. `workspace/pending-questions.md` is the
blocked-→-ask queue.

## Run any of them manually

```bash
export ANICCA_HOME=~/.openclaw
python3 $ANICCA_HOME/skills/anicca-core/scripts/health-check.py        # see system state
python3 $ANICCA_HOME/skills/anicca-core/scripts/read-quota.py          # see tier
bash    $ANICCA_HOME/skills/anicca-core/scripts/core-status.sh read    # see what the beat is doing
```

## Multi-machine memory sync setup (one-time per machine)

1. Private repo (e.g. `Daisuke134/anicca-memory`).
2. `ANICCA_MEMORY_REPO=git@github.com:you/anicca-memory.git` in `$ANICCA_HOME/.env`.
3. `bash scripts/sync-memory.sh` (first run clones to `~/.anicca/memory-sync/`).
4. Cron it every 10-30min on each machine.

Conflict model: rsync-mtime-wins + `cmp` content guard. Append-only files
(MEMORY.md index, build_log.md) are safest. Each host backs up its own state to
`machine-<hostname>/` one-way for disaster recovery.

Source: ported from `sonichi/sutando` (src/core_heartbeat.py, src/health-check.py,
skills/quota-tracker/, skills/proactive-loop/, scripts/sync-memory.sh,
docs/workspace-contract.md). Diff vs upstream: dual-harness (claude -p + OpenClaw),
$ANICCA_HOME paths, OpenClaw gateway/launchd checks instead of voice/web ports.
