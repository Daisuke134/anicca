# RED phase evidence — claude-p-loop-verification (Phase 2a, mode: lean)

## 作業場所

- `~/anicca` worktree: `.worktrees/loop-verification` (branch `feature/loop-verification`)
- `~/profitable-claude` worktree: `.worktrees/loop-verification` (branch `feature/loop-verification`)
  — spec の In-scope 節が `~/profitable-claude/skills/human-funded/{gig,affiliate,bounty}/` を含む
  ため（`~/anicca` とは別 git repo, F4修正で確認済み）。`~/profitable-claude` の main working tree は
  gig/bounty の live loop state で dirty だったため、こちらも worktree で隔離した。
- 両 worktree とも push はまだ行っていない（orchestrator 指示どおり commit のみ）。

## スコープ: 対象にした Tier1 PROP（lean mode, Required=true）

verification-architecture.md の Proof obligations 表から Tier=1 かつ Required(lean)=true の
全21件のうち、19件を新規 RED テストで作成した。残り2件は以下の理由でこの RED phase の新規作成対象
から除外し、理由を明記する:

| PROP | 状態 | 理由 |
|---|---|---|
| PROP-LV-009 | 対象外（既存, 既に GREEN） | `skills/earn/video/tests/test_record_earn.py` が既存でこの回帰を既にカバーしており spec 自身も「変更なしで green のまま通ることを確認（回帰）」と規定。新規実装ギャップがないので新規 RED テストは書かない。ベースライン確認としてこの pass 内で再実行し GREEN のままであることを確認済み（下記ログ参照） |
| PROP-LV-031 | 対象外（Phase 1 で既に確定済みの事実） | 5分類件数 30+23+7+24+19=103 と `jobs.json` の実 `enabled:true` 件数(103)一致は spec 本文に「確認済み」と明記されており、新規コードに依存しない静的事実。実装ギャップがないため RED 対象外 |

## テストファイル一覧（13ファイル、19 PROP を実装）

| # | PROP | ファイル | 対象実装（未実装、RED理由） |
|---|---|---|---|
| 1 | PROP-LV-001, REQ-LV-001/002/003 | `~/anicca/.worktrees/loop-verification/skills/report/test-loop-report.sh` | `loop-report.sh` に `lr_valid_evidence`(`--valid-evidence`flag), evidence gate(exit 1), AGENTMAIL_API_KEY 自己解決が未実装 |
| 2 | PROP-LV-020/022/035/036/037/040 | `~/anicca/.worktrees/loop-verification/skills/self/tests/test_cadence.py` | `skills/self/cadence.py`（`cadence_met`/`streak`）が存在しない。★PROP-LV-040 = G1 blocking finding の直接回帰テスト★ |
| 3 | PROP-LV-026 (clip_promote_status部分) | `~/anicca/.worktrees/loop-verification/skills/earn/clip-promote/tests/test_clip_promote_status.mjs` | `skills/earn/clip-promote/clip-promote-status.mjs` が存在しない |
| 4 | PROP-LV-007 | `~/anicca/.worktrees/loop-verification/skills/self/founder-loop/test-report-args.mjs` | `skills/self/founder-loop/report-args.mjs`（`founderReportArgs`）が存在しない |
| 5 | PROP-LV-003 | `~/anicca/.worktrees/loop-verification/skills/_shared/__tests__/test_ytdlp_parse.py` | `skills/_shared/lib/ytdlp_parse.py`（`parse_ytdlp_json`）が存在しない |
| 6 | PROP-LV-004 | `~/profitable-claude/.worktrees/loop-verification/skills/human-funded/gig/__tests__/test_funnel.py` | `skills/human-funded/gig/funnel.py`（`summarize_gig_funnel`）が存在しない |
| 7 | PROP-LV-005 | `~/profitable-claude/.worktrees/loop-verification/skills/human-funded/bounty/tests/test_funnel.py` | `skills/human-funded/bounty/funnel.py`（`summarize_bounty_funnel`）が存在しない |
| 8 | PROP-LV-006 | `~/anicca/.worktrees/loop-verification/skills/earn/polymarket-trade/test_positions.py` | `skills/earn/polymarket-trade/positions.py`（`parse_positions_response`）が存在しない |
| 9 | PROP-LV-008 | `~/anicca/.worktrees/loop-verification/skills/earn/video/tests/test_record_earn_onchain_wiring.py` | `record_earn.py::verify_onchain` が依然ハードコード `False` スタブ（既存 `onchain.py::confirm_usdc_inflow` へ配線されていない） |
| 10 | PROP-LV-023 | `~/anicca/.worktrees/loop-verification/skills/self/self-improve/tests/test_loop_evaluators.py` | `skills/self/self-improve/{clip,affiliate,video,gig,bounty}/evaluator.py` が5件とも存在しない |
| 11 | PROP-LV-024 | `~/anicca/.worktrees/loop-verification/skills/self/self-improve/tests/test_weekly_compare.py` | `skills/self/self-improve/lib/weekly_compare.py`（`beats_previous_week`）が存在しない |
| 12 | PROP-LV-028/029/030 | `~/anicca/.worktrees/loop-verification/skills/self/loop-scale/tests/test_guardrails.py` | `skills/self/loop-scale/guardrails.py`（`scale_eligible`/`cooldown_ok`/`fleet_at_capacity`/`is_ban_suspected`）が存在しない |
| 13 | PROP-LV-039 | `~/anicca/.worktrees/loop-verification/skills/self/openclaw-migrate/tests/test_migration_gate.py` | `skills/self/openclaw-migrate/migration_gate.py`（`channel_migration_eligible`）が存在しない |

## 実行コマンドと結果（全件 FAIL を確認、exit code = 1）

```bash
# 1
cd ~/anicca/.worktrees/loop-verification/skills/report && bash test-loop-report.sh
# 2
cd ~/anicca/.worktrees/loop-verification/skills/self/tests && python3 test_cadence.py
# 3
cd ~/anicca/.worktrees/loop-verification/skills/earn/clip-promote/tests && node --test test_clip_promote_status.mjs
# 4
cd ~/anicca/.worktrees/loop-verification/skills/self/founder-loop && node --test test-report-args.mjs
# 5
cd ~/anicca/.worktrees/loop-verification/skills/_shared/__tests__ && python3 test_ytdlp_parse.py
# 6
cd ~/profitable-claude/.worktrees/loop-verification/skills/human-funded/gig/__tests__ && python3 test_funnel.py
# 7
cd ~/profitable-claude/.worktrees/loop-verification/skills/human-funded/bounty/tests && python3 test_funnel.py
# 8
cd ~/anicca/.worktrees/loop-verification/skills/earn/polymarket-trade && python3 test_positions.py
# 9
cd ~/anicca/.worktrees/loop-verification/skills/earn/video/tests && python3 test_record_earn_onchain_wiring.py
# 10
cd ~/anicca/.worktrees/loop-verification/skills/self/self-improve/tests && python3 test_loop_evaluators.py
# 11
cd ~/anicca/.worktrees/loop-verification/skills/self/self-improve/tests && python3 test_weekly_compare.py
# 12
cd ~/anicca/.worktrees/loop-verification/skills/self/loop-scale/tests && python3 test_guardrails.py
# 13
cd ~/anicca/.worktrees/loop-verification/skills/self/openclaw-migrate/tests && python3 test_migration_gate.py
```

### 集計結果

全13ファイル、exit code = 1（FAIL）を個別実行 + 連続実行の両方で確認済み。詳細ログ:
`/private/tmp/claude-501/-Users-anicca-anicca-project/ad907a0b-9a31-4f8d-b55d-6450d253f198/scratchpad/red-phase-run.log`
（このセッションのスクラッチパッド、feature の commit には含めない）。

主要な失敗理由の内訳:
- `ModuleNotFoundError` / `ERR_MODULE_NOT_FOUND`（インポート先ファイルが未実装）: #2〜13 の全て
- assertion failure（既存コードの挙動がまだ spec の要求を満たさない）: #1（15件中9件 FAIL）、
  #9（4件中1件 FAIL — `verify_onchain` が常に `False` を返すハードコードスタブのため）

### ベースライン回帰確認（GREEN のまま、崩していないことの確認）

PROP-LV-009 に対応する既存テストと、この feature が触れていない同ディレクトリの既存テストが
このセッション内で引き続き GREEN であることを確認した:

```bash
cd ~/anicca/.worktrees/loop-verification/skills/earn/video
for f in tests/test_decide.py tests/test_onchain.py tests/test_record_earn.py tests/test_state_io.py; do
  python3 "$f" || exit 1
done
# => exit_code=0（4ファイル全て ALL ... TESTS PASSED）
```

## 設計上の判断（GREEN phase 実装者向け、spec が file path を明示していない箇所）

spec (`verification-architecture.md`/`behavioral-spec.md`) は各新設純関数の **シグネチャ** は
明示するが、一部は具体的な配置ファイルパスまでは固定していない。以下は RED テスト作成にあたり
このセッションで行った判断であり、Phase 2b（GREEN実装）着手前に必要なら spec に追記/確定すること:

1. **`cadence_met`/`streak`** → 新規 `~/anicca/skills/self/cadence.py`（Python）。理由: `contract`/
   `evidence` が spec 本文で JSON dict として記述されており、`compound` kind の再帰処理が
   dict ベースで最も自然。呼び出し元の `verify-loops.sh`/`verify-loops-audit.sh`（bash）からは
   `python3 cadence.py <subcommand> ...` で呼ぶ想定（`hrl_classify --classify` と同型の
   flag-entrypoint パターンを踏襲する）。
2. **`parse_ytdlp_json`** → 新規 `~/anicca/skills/_shared/lib/ytdlp_parse.py`。理由: REQ-LV-014が
   「REQ-LV-012と同じ関数を再利用、重複実装しない」と明記しており、video(`~/anicca`)と
   affiliate(`~/profitable-claude`、別repo)の両方から参照される共有関数のため `_shared/lib/` に
   置いた。affiliate 側からは `sys.path` にこのパスを追加してインポートする想定（cross-repo
   だが同一 $HOME 配下、既存の cross-repo 参照パターン——`profitable-claude` の各 `*-cli.sh` が
   既に `anicca/skills` パスを参照している——と整合）。
3. **`summarize_gig_funnel`/`summarize_bounty_funnel`** → 各 loop 自身のディレクトリ直下
   （`funnel.py`）。理由: 既存の `redeem.py`/`record_earn.py` 等が「この loop 専用のロジックは
   この loop のディレクトリに置く」という一貫した配置規約に従っているため。
4. **`founder_report_args`** → `~/anicca/skills/self/founder-loop/report-args.mjs`（Node/mjs）。
   理由: 返り値が構造化オブジェクト `{result, earned_usdc, evidence}` であり、同ディレクトリの
   `record-earn.mjs`/`mock-rpc.mjs` と言語を揃えた。
5. **`clip_promote_status`** → `~/anicca/skills/earn/clip-promote/clip-promote-status.mjs`。理由:
   `record-payout.mjs` と同じディレクトリ・言語（mjs）、payout ledger の行形状を直接扱う。
6. **`parse_positions_response`** → `~/anicca/skills/earn/polymarket-trade/positions.py`。理由:
   `redeem.py` と同じディレクトリに配置し、既存の `test_redeem.py`（同ディレクトリ直下、
   `tests/` サブディレクトリなし）という配置規約に倣った。
7. **per-loop evaluator（PROP-LV-023）** → `~/anicca/skills/self/self-improve/<loop>/evaluator.py`
   （spec本文 REQ-LV-110 に明記のパス、5 loop: clip/affiliate/video/gig/bounty）。
8. **`beats_previous_week`** → `~/anicca/skills/self/self-improve/lib/weekly_compare.py`（新設）。
9. **Loop Scaling ガードレール群（`scale_eligible`/`cooldown_ok`/`fleet_at_capacity`/
   `is_ban_suspected`）** → 新規ディレクトリ `~/anicca/skills/self/loop-scale/guardrails.py`。
   ★重要な判断★: 既存 `~/anicca/skills/self/spawn/lib/`（`spawn-decision.js`/`treasury-gate.mjs`等）
   は Anicca-colony の **citizen（新しい Anicca instance そのもの）を spawn する既存の別システム**
   であり、本 feature の REQ-LV-130〜135（**既存 earn loop のアカウント fleet を増殖させる**、
   全く異なる粒度の概念）と衝突・混同するリスクがあったため、意図的に新規の隣接ディレクトリへ
   分離した。Phase 2b 着手時にこの判断が妥当か再確認すること。
10. **`channel_migration_eligible`** → 新規ディレクトリ
    `~/anicca/skills/self/openclaw-migrate/migration_gate.py`（OpenClaw統合セクション専用の
    新規ディレクトリ）。

## 未対応（この RED phase のスコープ外、Tier2/Tier3 統合テストは別 phase）

verification-architecture.md の Tier2/Tier3 required=true 項目（PROP-LV-002/010/012〜019/021/
025〜027/032〜034/038 等）はこの Phase 2a（TDD RED = Tier1純関数中心）の対象外。REQ-LV-001/002/003
（loop-report.sh の自己解決・evidence gate）のみ、orchestrator 指示により Tier2 の決定論境界として
このセッションで先行してテストを書いた（上記ファイル#1）。残りの Tier2/Tier3 は Phase 2b 以降、
実装と合わせて統合テストとして追加する。

## Commit

両 worktree それぞれで、このセッション内で新規作成した test ファイル一式を1 commit にまとめて
`feature/loop-verification` ブランチへ commit した（push はまだ、orchestrator 指示どおり）。
