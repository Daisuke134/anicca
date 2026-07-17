# LM P0/P1 execution notes（goal 実行状態。毎証拠パス後に更新）

goal: docs/superpowers/specs/2026-07-17-life-manager-p0p1-goal.md（gmail 送信済み 19f6ffd41bf3d722）

## Open items（P0/P1 = 14）
| item | state | evidence |
|---|---|---|
| LM-24 target_legs | **code done, dev merge 済み**（PR #296→dev、target_legs ×2 を origin/dev で実確認）。残り = prod deploy + 実着信で声確認 | a76252b, 54ba48964 |
| LM-2 claim解放 | **code done, dev merge 済み**（releaseWake+低残高TGアラート統合）。残り = prod deploy 後の実 E2E | 182 tests green 自走確認 |
| LM-23 callback_query | **code done, dev merge 済み**。残り = 本番 TG でボタン往復実測 | allowed_updates 実装確認済 |
| LM-3 search-before-ask | **code done, dev merge 済み**（2段 Gemini + closed 質問 + additive migrations ×2）。残り = migration 適用 + 実イベント E2E | lm-p0.test.js 含む green |
| LM-21 rotate | pre-check 開始 | runbook あり |
| LM-18 staging | part1 **done**: PR #295 merge 済み、`git ls-tree origin/dev apps/life-call` 実在確認。conflict は .vcsdd/history.jsonl のみ（両保持で解消）。part2 = Railway staging 配線（dashboard、agent 実行中）。staging 方針: **LIFE_RUN_LOOPS=false**（staging から実ユーザーへ二重 call させない）、smoke = /health 200 + boot | ls-tree 出力 |
| LM-5 出た？v1 | pending（LM-23 後） | — |
| LM-6 onboarding+Gmail | pending | — |
| LM-25 Unipile 化+cache | pending | 置換可能性は検証済 |
| LM-4 travel metrics | pending | baseline 88% 実測済 |
| LM-7 ledger | pending | — |
| LM-19 margin 表 | pending | Telnyx $0.002/min 実測済 |
| LM-20 repo 収斂 | pending | — |
| LM-22 TikTok bio | **caption CTA done**（post-daily.sh、openclaw `4e41c4a6` push 済み）。bio link = blocked: @anicca.comedy が daily-driver 未ログイン + ログイン試行中に Chromium クラッシュ（load avg 瞬間 122、システム枯渇）。再試行手順あり（handle+共通pw+gog OTP）。**教訓: fleet 同時実行を絞る。CDP :9222 は 21:41 時点で死亡（curl 000 実測）— 再起動は後続 agent で** | screenshots ×3 in scratchpad |
| LM-1 dev loop D0 | pending | — |

## 走行中
- codex Sol（flowb, worktree .worktrees/lm-p0, branch feature/lm-p0-fixes）: PLAN.md wave1。agmsg team=lm-p0。
- 監視: agmsg inbox（fable-main）+ codex background output。

## 決定ログ
- 2026-07-17: wave1 = P0 コード4件のみに絞る（codex run を bounded に保つ）。wave2 = LM-5/6/25 系は wave1 E2E 後。
- rotate は codex と並行可（worktree はユニットテストのみ、prod env 非依存）。
