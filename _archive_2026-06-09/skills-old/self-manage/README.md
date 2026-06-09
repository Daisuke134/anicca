# self-manage (#336 P13)

Anicca's deliberate self-edit executor (spec 18 §4 MUTABILITY). Drains a proposal queue and
edits her own heartbeat cadence, spawns clones, edits her own skills, or files architecture
shifts — all gated by the constitution-guard (North Star + Law I immutable) and, for skills,
the eval-loop ≥0.7 quality gate.

Sibling of `self-improve` (#335): self-improve detects + fixes; self-manage executes
deliberate self-changes from a queue.

## Queue a proposal

```bash
echo '{"type":"heartbeat","schedule":"every 6h","reason":"reduce LLM cost"}' \
  >> ~/.hermes/state/self-manage-proposals.jsonl
hermes cron run self-manage   # or wait for the 12h tick
```

## Scripts

| script | purpose |
|---|---|
| `scripts/run.sh` | orchestrator — drain queue, dispatch by type, idempotent |
| `scripts/edit-heartbeat.sh` | guard → `hermes cron edit` heartbeat cadence → verify |
| `scripts/edit-skill.sh` | guard + denylist → worktree → hermes-chat diff → eval≥0.7 + tests → PR |
| `scripts/spawn-clone.sh` | guard → `spawn-child` (#327); colony row written by spawn-child |
| `scripts/architecture-shift.sh` | guard → forum issue for multi-instance vote (#338/#336b) |
| `scripts/_lib.sh` | shared: ids, guard call, decision log, queue helpers |

## Test

```bash
bash skills/self-manage/tests/test_self_manage_e2e.sh
```

Real (reverted) heartbeat cron edit: 180m → 360m → reverted to 180m. 4 assertions.
