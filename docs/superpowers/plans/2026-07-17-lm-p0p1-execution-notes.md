# LM P0/P1 execution notes（goal 実行状態。毎証拠パス後に更新）

goal: docs/superpowers/specs/2026-07-17-life-manager-p0p1-goal.md（gmail 送信済み 19f6ffd41bf3d722）

## Open items（P0/P1 = 14）
| item | state | evidence |
|---|---|---|
| LM-24 target_legs | in_progress（codex wave1） | — |
| LM-2 claim解放 merge | in_progress（codex wave1、fix branch 統合） | 残高fix済+実着信済（無言）|
| LM-23 callback_query | in_progress（codex wave1） | — |
| LM-3 search-before-ask | in_progress（codex wave1） | — |
| LM-21 rotate | pre-check 開始 | runbook あり |
| LM-18 staging | pending | — |
| LM-5 出た？v1 | pending（LM-23 後） | — |
| LM-6 onboarding+Gmail | pending | — |
| LM-25 Unipile 化+cache | pending | 置換可能性は検証済 |
| LM-4 travel metrics | pending | baseline 88% 実測済 |
| LM-7 ledger | pending | — |
| LM-19 margin 表 | pending | Telnyx $0.002/min 実測済 |
| LM-20 repo 収斂 | pending | — |
| LM-22 TikTok bio | pending | — |
| LM-1 dev loop D0 | pending | — |

## 走行中
- codex Sol（flowb, worktree .worktrees/lm-p0, branch feature/lm-p0-fixes）: PLAN.md wave1。agmsg team=lm-p0。
- 監視: agmsg inbox（fable-main）+ codex background output。

## 決定ログ
- 2026-07-17: wave1 = P0 コード4件のみに絞る（codex run を bounded に保つ）。wave2 = LM-5/6/25 系は wave1 E2E 後。
- rotate は codex と並行可（worktree はユニットテストのみ、prod env 非依存）。
