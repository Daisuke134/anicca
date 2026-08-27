# Life Manager Cloud on-time core handover

## Read first / SSOT

- Spec: `/Users/anicca/Projects/life-manager-main/.worktrees/lm-cloud-core-spec/docs/superpowers/specs/2026-08-26-life-manager-cloud-on-time-core-design.md`
- Remaining-TODO authority: spec `§6 Execution Steps` plus `/Users/anicca/Projects/life-manager-main/.worktrees/lm-cloud-core-spec/.superpowers/sdd/2026-08-26-life-manager-cloud-on-time-core/progress.md` Tasks 10–12. Some old unchecked setup bullets are historical; reconcile them against the progress evidence and production before acting.

## Exact repository state

- Repository: `Daisuke134/life-manager`
- Writable worktree only: `/Users/anicca/Projects/life-manager-main/.worktrees/lm-cloud-core-spec`
- Required branch/upstream: `codex/lm-cloud-core-spec` → `origin/codex/lm-cloud-core-spec`
- Verified HEAD/upstream at handover creation: `a9ab7069c98c7d47e93361391b3312d699eb6488`
- Do not edit `/Users/anicca/Projects/life-manager-main` or `/Users/anicca/anicca-project`; do not switch/reset the shared worktree blindly.
- No workers are live. Worktree was clean immediately before this handover file was created.

## Current item and verified evidence

- Task 12 fixes route reminders for Calendar events whose free-form venue name cannot geocode but whose adjacent outbound `[Travel]` block contains the autofill-resolved full address.
- Production diagnosis: `MIRSUBISHI UFJ INFORMATION TECHNOLOGY` returned destination `ZERO_RESULTS`; the existing full Akasaka address returned a real Transit journey (信濃町→四ツ谷→赤坂見附) with the same production key.
- R0 `71c8e9dc2` was rejected by a realistic prior-event return-to-home counterexample.
- R1 `a9ab7069c` rejects home-destination helpers and fails closed when adjacent candidates are not unique. The realistic return/multiple-candidate tests were RED first; related reminder/wake suite is 78/78 PASS. R1 is pushed but has not received fresh review, PR merge, or production deployment.
- Task 10 reminder owner repair and Task 11 server-side clean actor isolation are already merged/deployed; progress.md has exact SHAs and official readbacks.

## Live/public side effects and boundaries

- Controlled private Calendar event ID `lnpffie7md7fp0qp5j9hrudkq4`, title `Life Manager controlled reminder E2E — 行動不要`, is scheduled 2026-08-27 21:55–22:05 JST. Expected natural calls: 21:45 and 21:50; Telegram: 21:50. After receipt/replay-zero readback, delete with `send-updates none` and verify exact ID is cancelled.
- Real physical event: `MUIT 出社 (着席)` on 2026-08-28 08:40 JST; adjacent Travel block is 08:14–08:40 with the resolved Akasaka address. Use it for no-mock route/Telegram proof after deployment.
- Telnyx calls have already succeeded in production; portal remains at Authenticator 2FA. Never use recovery/reset or browser Google `はい`. Do not top up unless current official evidence shows it is needed; any personal-card charge requires exact amount/currency/source approval first.
- Do not expose secrets. Local tests/PIDs/log prose do not close provider effects; require Google Calendar, Telegram message ID, Telnyx call/webhook, Supabase ledger, GitHub Deployment/Railway exact-SHA readbacks.

## First safe resume action

1. `git fetch origin`, verify HEAD/upstream/clean status at the exact worktree; do not rebase away the handover commits.
2. Re-run the 78-test focused command from `apps/life-manager`:
   `node --test lib/travel-reminder.test.js lib/wake-filter.test.js test/wake-levels.test.js test/wake-catchup.test.js test/wake-loop-isolation.test.js`
3. Spawn a fresh read-only Sol reviewer for `71054aff0..a9ab7069c`, specifically attacking return-block, multi-event, home-normalization, display/claim preservation, and tenant/privacy boundaries. Fix material findings with the same Luna implementation lane and TDD.
4. Then run the relevant/full verification, push, PR/merge, read back exact Railway SHA/health, and continue the official production E2Es until every real remaining acceptance item is either proven or honestly blocked.

## User-sendable `/goal`

The user must send this exact line in the fresh Codex session to activate the goal and permit `spawn_agent` use:

```text
/goal `/Users/anicca/Projects/life-manager-main/.worktrees/lm-cloud-core-spec/.claude/handovers/2026-08-27_1904_lm-cloud-core-finish.md`と`/Users/anicca/Projects/life-manager-main/.worktrees/lm-cloud-core-spec/docs/superpowers/specs/2026-08-26-life-manager-cloud-on-time-core-design.md`を最初に全文読み、隣接doc/testを必要な分だけ調べ、Life Manager Cloudのon-time coreを最後まで完成させる。Doneは、cloud本番で(1)移動時間blockが自動作成され、(2)physical/場所なしを含むDaisのtimed non-helper eventへT-10/T-5電話が最大1回ずつ届き、(3)出発T-5 Telegramが次予定とprovider由来の実乗換を1回送り、(4)public QRから別Telegram actorがGoogle/Supabase loginなしでtenant分離されたonboardingを完了でき、各結果がGoogle Calendar event ID、Telnyx call/webhook、Telegram message ID、Supabase durable ledger、Railway exact deploy SHAの公式readbackで証明され、replay時の追加effectが0である状態。唯一の書込先は`/Users/anicca/Projects/life-manager-main/.worktrees/lm-cloud-core-spec`、branch`codex/lm-cloud-core-spec`、upstream`origin/codex/lm-cloud-core-spec`、handover時HEAD`a9ab7069c98c7d47e93361391b3312d699eb6488`。`/Users/anicca/Projects/life-manager-main`と`/Users/anicca/anicca-project`は触らない。編集前に`git fetch`しHEAD/upstream/dirtyを照合する。まずTask 12の関連78 testを再実行し、`71054aff0..a9ab7069c`をfresh read-only Solの`spawn_agent`で、return block・複数event・home正規化・表示/claim不変・privacyを反証reviewする。correctness/Done findingは同じLuna implementation laneへTDDで戻す。Ponytail `full`で既存再利用・最小差分を先に通し、残る変更だけSuperpowersのsystematic-debugging→test-driven-development→verification-before-completionに従う。primaryだけがspec/progress/完了判定を更新し、workerは割当code/testのみ、reviewerはexact commitのread-only。review後にrelevant/full tests、diff/secret/dependency checks、PR/merge、GitHub DeploymentとRailway healthのexact SHA readbackを行う。21:55 JSTのcontrolled event`lnpffie7md7fp0qp5j9hrudkq4`と翌08:40 JSTの`MUIT 出社 (着席)`をno-mock E2Eに使い、前者はreceipt/replay-zero後にsend-updates noneで削除しcancelledを確認する。browser Google`はい`、recovery/reset、secret出力、local製品変更は禁止。Telnyxは現在call成功済みなので必要性を公式再確認し、個人カードchargeは正確な金額/通貨/sourceの承認前に絶対実行しない。証拠が不足する項目を完了扱いせず、spec/progressを状態変化ごとに更新・commit・pushし、未blockなら計画だけで止まらず次の最高risk未完へ進む。同一blockが3つの異なる安全な手段でも解けない、または認証/課金の新承認が必要な時だけ、実測・試行・最小の次操作を残して停止する。
```
