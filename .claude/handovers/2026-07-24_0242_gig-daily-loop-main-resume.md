# Gig daily loop — main restart handover

## Durable anchors

- Spec: `/Users/anicca/anicca-project/docs/loop-engineering/26-gig-loop-asis-tobe-plan.md`
- Current-state SSOT: §0
- Remaining-TODO/order/done SSOT: §6 table
- Target folder tree: §9（structure reference only; missing files are not automatically TODO）

## Repository routing

- Session start/spec repository: `/Users/anicca/anicca-project`, branch `main`, upstream
  `origin/main`, verified minimum baseline `7ce9db9b3`. The shared main worktree has many
  user-owned untracked paths. Never reset, clean, mass-add, delete, or switch it. For spec edits,
  create a clean worktree from fresh `origin/main`, open/merge a PR to `main`, then fast-forward
  local main only after checking untracked collisions.
- Implementation worktree: `/Users/anicca/anicca-project/.worktrees/gig-browser-ownership-profitable`,
  branch `fix/gig-browser-ownership-20260724`, upstream
  `origin/fix/gig-browser-ownership-20260724`, verified commit `da9bcd6`.
- Live runtime repository: `/Users/anicca/profitable-claude`, branch
  `deploy/gig-speedy-reply-cutover`, commit `da9bcd6`. Do not implement here. Preserve its user WIP:
  deleted `skills/article-writer/topics/queue/genshijin-codex-token-cost-benchmark.md` and untracked
  `skills/article-writer/topics/in-progress/genshijin-codex-token-cost-benchmark.md`.
- Old spec worktree `/Users/anicca/anicca-project/.worktrees/coconala-reply-sla` is historical and
  must not become the continuation SSOT.

## Current item and evidence

- Current item: §6 #1, close B1 native submit for Coconala thread `9967694`.
- Connector DB: `~/gig/connector-outbox.sqlite3`, action `1`, revision `19`,
  state `reconcile_pending`; verified thread URL/hash and seller send time remain empty.
- No customer reply/application/delivery was manually performed in the handover session.
- Browser `ai.anicca.hf-gig-browser` is running. Gig pass/reply/auditor/core/self-improve labels
  remain installed; latest observed exits were `0`. Daily report has not yet naturally run since
  reload.
- Fresh RED: `bash skills/gig-work/tests/test_gig_paid_work_gate.sh` exits `1`; browser-fail
  recovery expects `deterministic-paid-progress`, but the recovery browser log is empty.
- Self-improvement is implemented (`pass_count=529`, `improve_cycle=76`, kept/reverted evidence).
  The verifier still falsely lists six missing items after normal no-change operation.
- Final Done requires every natural day to close all four lanes: Shuppin, Oubo, Reply, and Nouhin.
  Each lane must have either an authoritative verified action or a reasoned `verified_noop`, plus
  checked/eligible/action/outcome/duplicate/model-call/cost/revenue evidence. Missing one lane
  makes the daily proof fail.

## First safe resume action

Start on local `main`; read this file and spec §0/§6. Fetch all relevant remotes and re-measure
HEAD/upstream/dirty state, connector action/revision, launchd state, and Coconala authoritative
ground truth before editing. Then reproduce §6 #1 at the sender/native-submit boundary without
manually sending. Make the smallest fix in the clean implementation worktree, independently review
the exact commit, deploy it to `origin/deploy/gig-speedy-reply-cutover`, kick the production reply
loop, and let the loop—not Codex—perform the customer action. Mark #1 done only after the loop reads
back thread URL, outgoing hash, seller send time, outbox=`replied`, one Telegram event, and zero
duplicate sends.
