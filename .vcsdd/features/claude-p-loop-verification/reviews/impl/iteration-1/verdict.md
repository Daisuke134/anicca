# Phase 3 実装レビュー verdict — claude-p-loop-verification / iteration-1

Reviewer: fresh-context adversary (no Builder context, disk artifacts only)
Scope reviewed:
- `~/anicca/.worktrees/loop-verification` (branch `feature/loop-verification`, diff `main...HEAD`, commits 99fcf2e/607face/7f8bd4c + earlier RED dd7383b)
- `~/profitable-claude/.worktrees/loop-verification` (branch `feature/loop-verification`, diff `main...HEAD`, commits c2d7e40..3e45cc0, feature-relevant: 333fc69/b923b9e)
- Spec: `.vcsdd/features/claude-p-loop-verification/specs/{behavioral-spec.md,verification-architecture.md}`
- Green evidence: `.vcsdd/features/claude-p-loop-verification/evidence/sprint-1-green-phase.log`

## 総合判定: **FAIL**（blocking 1件）

---

## 次元別判定

### 1. Spec準拠 — **FAIL**

- 実装されたREQのシグネチャ・分岐仕様は spec と正確に一致（cadence.py の `cadence_met(today_jst_date, contract, evidence)` / `streak(evidence_by_date, today_jst_date, contract)` は REQ-LV-101/103 の記述と1:1、5 kind 全て実装済み、clip-promote-status.mjs は REQ-LV-120 と一致、funnel.py 2種は REQ-LV-015/016 のフィールド名・カウント規則と一致、guardrails.py/migration_gate.py/positions.py/ytdlp_parse.py/report-args.mjs/ledger_metrics.py も対応する REQ の記述通り）。
- **BLOCKING — REQ-LV-004 未実装、かつ REQ-LV-003 と組み合わさって実害のある回帰を生む**:
  spec の `### A` 節は REQ-LV-001〜004 を一括で「P0-1, P0-7」とラベルしており、タスクリスト上も
  `#1 P0-1: loop-report.sh の env 自己解決 + evidence gate` が `completed` になっている。しかし
  `~/profitable-claude/skills/human-funded/{gig,affiliate,bounty}/*-cli.sh` の `STARTUP` 文字列は
  この diff で一切変更されていない（`git diff main...HEAD -- skills/human-funded/` は
  `funnel.py`×2 と `.gitignore` のみ）。3ファイルとも実際に grep すると、投稿/応募/納品が無い回の
  evidence として今も文字通り
  `"<evidence: ... or the string none if there was none>"` を送る指示のままになっている
  （例: `bounty-cli.sh:17`、`affiliate-cli.sh:9`、`gig-cli.sh:21`）。
  一方 `~/anicca/skills/report/loop-report.sh` は同じ diff で REQ-LV-003 の evidence gate
  （`lr_valid_evidence()`）を追加済みで、bare `"none"` を渡すと **`exit 1` + ログに `REJECTED`**
  を返すようになった（`skills/report/loop-report.sh:44-49` 相当、`test-loop-report.sh` で確認済み）。
  結果: gig/affiliate/bounty loop が「今回は何もなかった」回に `loop-report.sh gig ... none` を
  呼ぶと、この evidence gate が既に有効な状態では **mail が REJECTED になり黙って送信されない**
  （呼び出し元プロンプトは exit code を見ていないため、agent 自身も気づかない）。これは
  「既存の fail-closed 契約は一切弱めない」という non-functional constraint には反しないが、
  spec が REQ-LV-004 で明示的に予告していた副作用そのものであり、**片方（gate）だけ実装して
  もう片方（prompt更新）を実装しないと本番で可視性が失われる**、実害のある未完了。
  P0-1 を "completed" とマークするのは時期尚早。

### 2. テスト実効性 — **PASS**

- 新規/変更テスト13ファイル・112アサーションを本セッションで独立に再実行し、全て green
  であることを確認（green-phase.log の主張と完全一致 — 個別に再カウントした合計も112で一致）:
  `test-loop-report.sh`=15, `test_cadence.py`=21, `test_clip_promote_status.mjs`=6,
  `test-report-args.mjs`=4, `test_ytdlp_parse.py`=7, gig `test_funnel.py`=6,
  bounty `test_funnel.py`=7, `test_positions.py`=5, `test_record_earn_onchain_wiring.py`=4,
  `test_loop_evaluators.py`=15, `test_weekly_compare.py`=5, `test_guardrails.py`=14,
  `test_migration_gate.py`=3。
- 既存回帰テスト4本（`test_decide.py`/`test_onchain.py`/`test_record_earn.py`/`test_state_io.py`）
  も再実行し green。`test_record_earn.py` の `PROP-LV-009` stub-injection シームは触れられておらず
  green のまま — record_earn.py の `verify_onchain` デフォルト値差し替えのみで注入シーム自体は
  無変更、spec の「注入可能な引数は変更しない」と一致。
- RED phase コミット（`dd7383b`）以降、テストファイル自体への変更は無し（`git diff dd7383b HEAD --
  '**/tests/**' '**/test_*'` で確認、diff は空）— テストを実装に迎合させて弱めた形跡なし。
- `run.sh` の P0-3 修正後 `bash -n run.sh` で構文エラーなし。

### 3. 境界・安全 — **FAIL（上記1と同一の blocking finding）+ 他はPASS**

- (a) evidence gate の既存呼び出し元互換性: 上記1のBLOCKING参照 — `gig/affiliate/bounty`
  の3呼び出し元が新gateと非互換のまま。`clip`/`clip-promote` 側は本feature対象外（Ground truth
  通り、clip は post_url を渡す設計で bare "none" を送らない）でこの問題は無い。
- (b) `record_earn.py::verify_onchain` の on-chain 配線: `onchain.py::confirm_usdc_inflow`
  （Base RPC、USDC contract + Transfer topic0 + `to`-topic + amount一致 + self-transfer拒否、
  fail-closed）に配線されており、誤検知で偽収益を記帳するリスクは低い。import/RPC例外時は
  `False` に fail-closed（`record_earn.py` 該当箇所を確認済み）。既存 `onchain_check` 注入シームは
  無変更（テストは引き続きスタブ注入可能）。実際に実 Base mainnet tx
  `0xce52f06ffb1b09d4189925a261f174b1d642ee7f5dfbdd0c3d14733630e7006c` で正しく True/False を返す
  ことを確認済み（4/4テストPASS）。P0-4 は要件通り。
- (c) 判断のregex/if-elseハードコード混入: 新規決定論ツール（cadence.py, funnel.py×2,
  clip-promote-status.mjs, guardrails.py, migration_gate.py, ledger_metrics.py, evaluator.py×5）
  を確認したが、いずれも「既に agent が書き込んだカテゴリラベル/timestamp/数値の集計・比較」
  という bookkeeping/arithmetic の範囲に留まっており、「どの案件に応募するか」「何が
  mistake か」等の業務判断をコード側に持ち込んでいない。`~/.claude/rules/
  building-effective-ai-agents.md` の regex-judgment 禁止ルールに抵触する箇所は見つからなかった。

### 4. 来歴不明コードの検査 — **PASS（懸念解消）**

- Builder報告にあった「別プロセス由来」ファイル群
  （`clip-promote-status.mjs`, `cadence.py`, `cadence-contracts.json`, `cadence-evidence.py`,
  `verify-loops.sh`/`verify-loops-audit.sh` の変更）を `git log --diff-filter=A` / `git show
  99fcf2e --stat` で来歴確認した結果、**全てこのfeatureブランチのGREENフェーズ第1コミット
  （99fcf2e、著者 Daisuke Sato、このworktree内）で一括追加されたもの**であり、外部プロセスからの
  混入ではなかった。green-phase.log の「pre-existed in the worktree, untracked」という記述は
  同一セッション内で `git add` 前に書かれていたことを指すだけで、由来不明という意味ではない。
  内容も精査済みで、spec (REQ-LV-100〜104/120) と一致し、危険な副作用（他loopの状態を書き換える、
  スコープ外ファイルへの書き込み等）は見当たらなかった。`verify-loops.sh`/
  `verify-loops-audit.sh` の変更は既存 capafy/reddit/life-manager の3ブロックを一切変更せず
  （`fresh()`/`stale_hrs()` 呼び出しをそのまま維持）、新設8 loop分ブロックのみを追加しており
  REQ-LV-104 の「対象外3ブロックは無変更」制約を守っている。

### 5. P0-3 修正の妥当性 — **PASS**

- `run.sh` 内の `exit` 経路を全数確認（grep で `exit 0`/`exit 1` を検索、ヒットは2箇所のみ
  ＋末尾の暗黙終了）。3つの早期return分岐（`S1_warmup`失敗時、`verify-only`失敗時）と
  正常終了パスの全てが `write_audit()` を経由してから抜けることを確認 — P0-3で報告された
  「6日間 stall が audit ledger に一切残らなかった」根本原因（早期exitがaudit appendより前に
  抜けていた）は解消されている。JSON schema（`date/handle/transition/did/earned_usdc`）は
  リファクタ前後で不変、既存 ledger reader との互換性も維持。

---

## Findings一覧

| # | severity | 内容 |
|---|---|---|
| F1 | **blocking** | REQ-LV-004未実装。`~/profitable-claude/skills/human-funded/{gig,affiliate,bounty}/*-cli.sh` のSTARTUPが今も evidence引数に bare `"none"` を送る指示のまま。同diffで有効化された `loop-report.sh` のevidence gate（REQ-LV-003）と組み合わさり、"queue-empty"系の回でmail報告が黙ってREJECTEDになる実害のある回帰を生む。P0-1タスクの"completed"マークを見直すか、REQ-LV-004を別タスクとして即座に着手すべき。修正は3ファイルの `STARTUP` 文字列内 `or the string none if there was none` 相当の一文を `none: <理由>` 形式に更新するだけで、spec (REQ-LV-004) が既に許可している変更範囲内。 |
| F2 | major | REQ-LV-018（P0-6, founder-loop mail配線）が実質未着手。`report-args.mjs::founderReportArgs()` は実装・テスト済み（4/4 green）だが、`founder-loop.sh` からもその他の本番コードからも一切呼ばれていない（grep 0件、`founder-loop.sh` 自体は今回diffで無変更）。タスクリスト#6は"pending"のままで虚偽の完了主張はないが、Goal 6（REQ-LV-019、8 loop全てのE2E+adversary PASS）には founder-loop の実配線が必須であり、次イテレーションの優先項目として明記が必要。 |
| F3 | major | REQ-LV-050/051（P0-5, healthcheck-runtime-loop.sh launchd配線）も未着手。`~/Library/LaunchAgents/`には capafy/reddit/life-manager/clip/clip-promote/video/bounty/affiliate の `*-core-healthcheck.plist` は存在するが、`healthcheck-runtime-loop.sh`（a3cdd4/franklin/pm-earner/founder-proxy対象）用のplistは存在しない。タスクリスト#5も"pending"で虚偽主張なし。 |
| F4 | minor | `cadence-evidence.py::evidence_by_date_for_streak()` の pm-earner分岐は、14日ウィンドウの各日について "hourly-pass"（recency種）の evidence に**現在時点の**`marker`/`now_epoch` をそのまま使い回している（過去日ごとの実際のmtime履歴を持たないため）。結果、現在 `earner.log` が新しければ streak の全過去日が実態に関わらず `hourly-pass=true` として計算されうる。`cadence_met()`本体（REQ-LV-102のエスカレーション判定、当日のみ評価）には影響しないが、`streak` KPI（scorecard表示）がpm-earnerに限り誤解を招く可能性がある。ドキュメント化 or 既知の制約として次イテレーションで扱うことを推奨。 |

---

## 結論

**総合: FAIL**（blocking 1件: F1）。F1は「gate側とprompt側のどちらか片方だけ実装した」ことで
生じる典型的な統合バグであり、テストは個別には全てGREENだが、2つのworktree間の相互作用を跨いだ
検証（Tier2統合テスト、spec表の「`*-cli.sh`のSTARTUPにgrepで文言確認」）が行われていないために
見逃された。次イテレーションでF1を解消し、F2/F3を明示的なスコープ確認（今イテレーションでは意図的に
未着手であることの確認）としてから再レビューを推奨する。
