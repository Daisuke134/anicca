# Gig daily loop — main restart handover

## Durable anchors

- Spec: `/Users/anicca/anicca-project/docs/loop-engineering/26-gig-loop-asis-tobe-plan.md`
- Current-state SSOT: §0
- Remaining-TODO/order/done SSOT: §6 table
- Target folder tree: §9（structure reference only; missing files are not automatically TODO）

## Repository routing

- Session start/spec repository: `/Users/anicca/anicca-project`, branch `main`, upstream
  `origin/main`, current baseline `7b649bbc1`. The shared main worktree has many
  user-owned untracked paths. Never reset, clean, mass-add, delete, or switch it. For spec edits,
  create a clean worktree from fresh `origin/main`, open/merge a PR to `main`, then fast-forward
  local main only after checking untracked collisions.
- Implementation worktree: `/Users/anicca/anicca-project/.worktrees/gig-browser-ownership-profitable`,
  branch `fix/gig-browser-ownership-20260724`, upstream
  `origin/fix/gig-browser-ownership-20260724`, verified commit `f7f180a`.
- Live runtime repository: `/Users/anicca/profitable-claude`, branch
  `deploy/gig-speedy-reply-cutover`, commit `3993372`. Do not implement here or overwrite concurrent
  article-writer work.
- Old spec worktree `/Users/anicca/anicca-project/.worktrees/coconala-reply-sla` is historical and
  must not become the continuation SSOT.

## Current item and evidence

- Current item: §6 #1, close B1 native submit for Coconala thread `9967694`; it is externally
  blocked by the target account/profile state, not by the browser transport.
- Connector DB: `~/gig/connector-outbox.sqlite3`, action `1`, revision `36`, state `blocked`;
  verified thread URL/hash and seller send time remain empty. Slot is free and Telegram count is 0.
- The production loop reaches the exact Coconala native request: URL-encoded jQuery form, 10
  fields, one body, five empty attachments, and the exact AJAX endpoint. Revisions `34` and `35`
  both finish HTTP then return `submit_rejected_sending_unavailable`.
- Each failed attempt is reconciled only after the 120-second consistency window. Ground truth is
  seller message 0, last sender buyer, matching outgoing hash 0; therefore no delivery is unknown.
- The thread links its counterpart to `/users/6186053` in three places, the block form uses the
  same ID, and thread data contains the same ID. The authenticated profile read returns
  「ご指定のページが 見つかりませんでした」 and exposes no message control.
- Source: [Coconala Help — メッセージ機能について](https://coconala-support.zendesk.com/hc/ja/articles/218721057-%E3%83%A1%E3%83%83%E3%82%BB%E3%83%BC%E3%82%B8%E6%A9%9F%E8%83%BD%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6)
  / core quote: 「相手に機能制限がかかっている」場合は「メッセージが送信できません」。
- `ai.anicca.hf-gig-pass` and `ai.anicca.hf-gig-reply-detector` are loaded again after quarantine.
  The reply detector exits 0 without claiming the blocked action; the half-hour pass remains
  available for the other lanes.
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
ground truth. Do not retry thread `9967694` while `/users/6186053` remains not-found. Resume §6 #1
only after a read-only profile check proves the profile active, or after the same thread produces a
new unique buyer event (which reactivates the blocked action). Then let the production loop—not
Codex—perform exactly one customer action and reconcile it. If the profile remains not-found,
Coconala support/account restoration is the smallest external unblock; do not send the inquiry
without new authority. Mark #1 done only after the loop reads back thread URL, outgoing hash,
seller send time, outbox=`replied`, one Telegram event, and zero duplicate sends.
