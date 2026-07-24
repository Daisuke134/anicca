# Gig/Coconala loop alignment handover

## Source of truth

- Spec: `/Users/anicca/anicca-project/docs/loop-engineering/26-gig-loop-asis-tobe-plan.md`
- Remaining-TODO SSOT: §6 table and §6.1 test matrix
- Main currently records 7 remaining items: external-blocked #1 plus #4–#9. #2 and #3 are done.

## Repository routing and verified state

- Spec/control repository: `/Users/anicca/anicca-project`
  - branch `main`, upstream `origin/main`, verified `27e806f2e5c32fa61304ca9cb71c6d6bfe094113`
  - shared worktree has many user-owned untracked paths. Never reset, clean, mass-add, or switch it.
  - future spec edits belong in a fresh clean `.worktrees/gig-main-*` branch from current `origin/main`,
    then PR/merge and a collision-checked fast-forward of local main.
- Implementation worktree: `/Users/anicca/anicca-project/.worktrees/gig-browser-ownership-profitable`
  - branch `fix/gig-browser-ownership-20260724`, upstream
    `origin/fix/gig-browser-ownership-20260724`, verified/pushed HEAD `19ac5a548b6b77931b7af0ef90407d6e593287c3`
  - dirty warning: `scripts/lane_state_machine.py` and
    `tests/test_four_lane_state_machine.py` contain interrupted, uncommitted follow-up edits.
    They are not reviewed evidence. Preserve them; inspect the diff before deciding whether to keep or replace it.
- Live runtime: `/Users/anicca/profitable-claude`
  - branch `deploy/gig-speedy-reply-cutover`, upstream same, clean and verified
    `0cf56932e1fbe651a9d2a4d40c3ae667c115fb1f`
  - do not implement directly here. Deploy only an exact reviewed merge whose first parent is the latest live HEAD.

## What is done

- §6 #2 paid-work recovery is closed: accepted artifact reuse, browser retry, and lower-ledger
  invariance are recorded in the spec.
- §6 #3 self-improve no-change verifier is closed and deployed. Fresh successful `.last-pass`
  is bound to the exact poll-control artifact; no-change/model 0 is normal, and stale/malformed/material
  evidence remains fail-closed.
- Natural runtime is alive: reply detector run 23 exit 0, half-hour pass run 4 exit 0,
  self-improve verifier run 14 exit 0, browser PID 84850 remains running.
- No manual customer reply, application, listing, or delivery was performed for §6 #4.

## Actual bottlenecks

1. **#1 is externally blocked, not a coding task.** Coconala thread `9967694`, action `1`,
   revision `36` remains `blocked`, with no verified outgoing hash. Do not resend the same event.
   It can resume only after an authoritative counterpart/platform-state change or a new unique buyer event.
2. **#4 is the immediate engineering bottleneck.** The pushed common-envelope foundation
   `19ac5a5` is not deployable. Review reproduced three correctness defects:
   - a crash after the durable fence but before execution can remain in `reconcile_pending`;
   - another owner can enter through `run_once` while the active lease still belongs to the first owner;
   - an expired owner can still fence a side effect.
3. **#5–#9 depend on #4.** Exact four-lane reporting, provider canary, a real banked transaction,
   24-hour proof, and 7+14-day graduation are not credible until the common envelope prevents
   duplicates and deadlocks across Shuppin, Oubo, Reply, and Nouhin.

## Minimal solution to align on before coding

Keep the next change limited to the three #4 invariants:

1. After a fence, never execute again from timeout/ACK ambiguity. Reconcile first; only a bounded
   authoritative non-delivery proof may create a fresh revision.
2. `run_once` must respect a live owner lease. Only an expired pre-effect claim may receive a new
   monotonic fencing token.
3. Side-effect fencing must atomically require the current owner, current fencing token,
   allowed state, and an unexpired lease.

Then add only the three focused regression cases, obtain findings-zero review, and deploy the exact
merge. After that, connect the envelope to the four existing lane adapters one lane at a time and
record real action-or-`verified_noop` evidence. Do not add another generalized framework or broad
test expansion before these three defects are closed.

## First safe resume action

Start from `/Users/anicca/anicca-project` on `main`. Fetch and verify the spec, all three repository
HEAD/upstream/dirty states, the implementation diff against `19ac5a5`, and the live launchd/connector
state. Do not edit, deploy, kick, send, apply, list, or deliver yet. First present to the user:

1. the seven remaining TODOs in dependency order;
2. the distinction between the external #1 blocker and the engineering #4 blocker;
3. the three-invariant minimal #4 repair above;
4. a compact TO-BE flow showing how #4 unlocks #5–#9.

Wait for alignment before writing code. This restart is a handover prompt, not a `/goal`; do not
create or activate a goal.
