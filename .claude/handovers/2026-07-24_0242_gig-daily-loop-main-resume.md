# Gig daily loop — main restart handover

## Durable anchors

- Spec: `/Users/anicca/anicca-project/docs/loop-engineering/26-gig-loop-asis-tobe-plan.md`
- Current-state SSOT: §0
- Remaining-TODO/order/done SSOT: §6 table
- Target folder tree: §9（structure reference only; missing files are not automatically TODO）

## Repository routing

- Session start/spec repository: `/Users/anicca/anicca-project`, branch `main`, upstream
  `origin/main`, required merged baseline `22e2694bb`. The shared main worktree has many
  user-owned untracked paths. Never reset, clean, mass-add, delete, or switch it. For spec edits,
  create a clean worktree from fresh `origin/main`, open/merge a PR to `main`, then fast-forward
  local main only after checking untracked collisions.
- Implementation worktree: `/Users/anicca/anicca-project/.worktrees/gig-browser-ownership-profitable`,
  branch `fix/gig-browser-ownership-20260724`, upstream
  `origin/fix/gig-browser-ownership-20260724`, verified commit `d02f824`.
- Live runtime repository: `/Users/anicca/profitable-claude`, branch
  `deploy/gig-speedy-reply-cutover`. HEAD advances with concurrent article-writer merges, so treat
  any concrete SHA only as an observed baseline. Reviewed Gig deploy merges `59957c5`, `c4007a8`,
  and `a61b2ed` must remain first-parent ancestors of the current HEAD. Do not implement here or
  overwrite concurrent work.
- Old spec worktree `/Users/anicca/anicca-project/.worktrees/coconala-reply-sla` is historical and
  must not become the continuation SSOT.

## Current item and evidence

- Current item: §6 #1, close B1 native submit for Coconala thread `9967694`; the exact target
  remains externally blocked. The browser/native transport works on control threads, while
  `submit_rejected_sending_unavailable` also occurs on at least one active-profile thread, so the
  bounded code must not be reduced to a single inferred cause.
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
- A second production action proves the same target-state failure: thread `9967721`, counterpart
  `/users/6186059`, revisions `1` and `2`, both `submit_rejected_sending_unavailable`; authoritative
  reread after 120 seconds remains seller 0 / buyer last / matching hash 0. Action `2` is revision
  `3` `blocked`. Action `8` is also blocked before click because its counterpart profile is
  not-found.
- An active-profile control proves the transport works. Production action `3` on thread `9976213`
  sends once, rereads exact thread URL/hash/seller time, reaches `replied`, and emits exactly one
  sent Telegram report `gig:telegram:reply:v1:3:1` with message ID `3334`.
- Active-profile thread `9993478` action `4` also returns
  `submit_rejected_sending_unavailable`; its 120-second reread remains seller 0 / buyer last /
  matching hash 0 and it is revision `2` `blocked`. Active profile is therefore not sufficient for
  success, and Coconala does not expose the exact per-thread reason behind the bounded code.
- Reviewed implementation `4e956f7` and deploy merge `59957c5` persist only five bounded rejection
  codes. Explicit rejection becomes `blocked` only after executor quiescence, 120 seconds, and
  authoritative absence. Raw server text is not persisted. A new event during the window is
  transactionally moved to a fresh revision and deferred to the next pass; a stale read rolls back.
- Production proof after deploy: thread `9995190` action `5` rejects once, the immediate follow-up
  returns `consistency_window_open` with no resend, and the 120-second reread automatically makes
  revision `1` `blocked` with its intent `superseded` and Telegram count 0. In the same production
  pass, thread `9976947` action `6` sends once and reaches `replied` with verified hash
  `7922006b5050d7c1e935e866e24016a3b2575444ed2d06c59ec42880a57bd92b`, seller time `1784847705`,
  one verified intent, and exactly one sent Telegram event `gig:telegram:reply:v1:6:1`
  (message ID `3335`).
- Source: [Coconala Help — メッセージ機能について](https://coconala-support.zendesk.com/hc/ja/articles/218721057-%E3%83%A1%E3%83%83%E3%82%BB%E3%83%BC%E3%82%B8%E6%A9%9F%E8%83%BD%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6)
  / core quote: 「相手に機能制限がかかっている」場合は「メッセージが送信できません」。
  The same article says 「制限解除可否・時期をご案内することはできません」, so support is
  not an unblock guarantee.
- `ai.anicca.hf-gig-pass` and `ai.anicca.hf-gig-reply-detector` are loaded after reviewed deploy;
  both latest exits are `0`. The reply detector skips blocked actions and continues other threads;
  the half-hour pass remains available for the other lanes.
- No customer reply/application/delivery was manually performed in the handover session.
- Browser `ai.anicca.hf-gig-browser` is running. Gig pass/reply/auditor/core/self-improve labels
  remain installed; latest observed exits were `0`. Daily report has not yet naturally run since
  reload.
- §6 #2 is closed by reviewed test commits `b293831` + `d02f824` and deploy merges `c4007a8` +
  `a61b2ed`; production code is unchanged. The prior RED was a fixture-only missing `GIG_PASS_ID`
  that made its fake runner exit `46` before browser recovery. First pass proves builder
  1/browser 1/exit 1 and durable exact artifact/hash/acceptance binding; second pass proves
  builder/model 0, browser 1, same binding, and buyer-visible success. The same fixture proves the
  strategy/applied/task-request-map/shuppin/shared-lessons/playbook/gig-funnel/earnings ledger
  SHA256 values remain equal to their initial values after both passes. Shell integration 17 and
  related Python 34 pass; the focused test also passes on live merge `a61b2ed`.
- Self-improvement is implemented (`pass_count=529`, `improve_cycle=76`, kept/reverted evidence).
  The verifier still falsely lists six missing items after normal no-change operation.
- Next safe implementation item while §6 #1 remains externally blocked is §6 #3, the
  self-improvement verifier no-change false positive.
- Final Done requires every natural day to close all four lanes: Shuppin, Oubo, Reply, and Nouhin.
  Each lane must have either an authoritative verified action or a reasoned `verified_noop`, plus
  checked/eligible/action/outcome/duplicate/model-call/cost/revenue evidence. Missing one lane
  makes the daily proof fail.

## First safe resume action

Start on local `main`; read this file and spec §0/§6. Fetch all relevant remotes and re-measure
HEAD/upstream/dirty state, connector action/revision, launchd state, and Coconala authoritative
ground truth. Do not retry thread `9967694` for the same event. Resume §6 #1 only after a read-only
check shows a material counterpart/platform-state change, or after the same thread produces a new
unique buyer event (which reactivates the blocked action). Then let the production loop—not
Codex—perform exactly one customer action and reconcile it. If neither changes, there is no
loop-side unblock; leave #1 blocked and continue §6 #3. A Coconala inquiry may diagnose the
account state but does not guarantee restoration and requires new authority.
Mark #1 done only after the loop reads back thread URL, outgoing hash, seller send time,
outbox=`replied`, one Telegram event, and zero duplicate sends.
