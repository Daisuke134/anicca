# gig-feasibility-volume — Phase 3 実装レビュー verdict (iteration-1)

- **Reviewer**: fresh-context adversary（Builder文脈なし、disk専用）
- **対象**: repo A `~/profitable-claude/.worktrees/gig-fv` (HEAD ff3a43f) + repo B `~/anicca/.worktrees/gig-fv` (HEAD 3df9081)
- **照合 spec**: `.vcsdd/features/gig-feasibility-volume/specs/{behavioral-spec.md,verification-architecture.md}` (REQ-GFV-001..024, PROP-001..038)

## 総合判定: PASS（blocking 0件）

全6次元 PASS。green-phase log（`evidence/sprint-1-green-phase.log`）の claim を鵜呑みにせず、14件の新規テストファイル＋既存 regression baseline（10ファイル/121アサーション）を自分で実行し、全て独立に GREEN 再現した。

---

## 次元別判定

### 1. Spec準拠 — PASS

- `passprep.py`（repo A）を Read し、`merge_missing_keys`/`compute_listings_due`/`compute_cold_start` が REQ-GFV-002/005/017 通りの純粋関数であることを確認。fake/スタブ/ハードコード返値なし。
- `cadence-evidence.py::_gig_activity_event_dates`（repo B）を Read し、`_GIG_REAL_ACTION_STATUSES = {"applied","replied"} | _WON | _PAID` に対する **厳密一致**（`row.get("status") not in ...`）で判定していることを確認。`applied_0`/`applied_1`/`no_action` 等の housekeeping ステータスは集合に含まれないため確実に除外される。table-driven テスト（`test_gig_activity_event_dates.py`）でも `EXACT-match rule (not startswith): 'applied_1'/'applied_2' summary rows do NOT count as activity (False)` を自分で実行し確認した。
- PROP-036（実データ検証）: `test_gig_cadence_real_evidence.py` は SUT とは別に独立実装した reference tally（stdlib のみ、SUTのパーサーを呼ばない）を実データ `~/gig/applied.jsonl` に対して計算し、SUT の出力と完全一致することを assert する構造。循環検証ではない。自分で実行し `SUT ... matches the independent reference tally exactly` を再現した（実データは270行超、まだ成長中のライブファイル）。

### 2. テスト実効性 — PASS

以下を自分でこの session 内で実行し、green-phase log の claim を再現した（弱められている形跡なし、RED phase の意図と一致）。

**新規14テストファイル、全GREEN:**
- repo A: `test_cold_start_pure.py`(8/8) `test_feasibility_fillforward.py`(10/10) `test_funnel_by_category.py`(27/27) `test_funnel_report_schema.py`(8/8) `test_listing_categories_seed.py`(5/5) `test_listings_due_pure.py`(7/7) `test_listings_live_pure.py`(7/7) `test_passprep_new_fields.test.mjs`(7/7)
- repo B: `test_gig_evaluator_by_category.py`(8/8) `test_gig_ts_parser.py`(8/8) `test_gig_activity_event_dates.py`(10/10) `test_cadence_contracts_gig_source.py`(10/10) `test_cadence_evidence_gig_branch.py`(4/4) `test_gig_cadence_real_evidence.py`(4/4)

**既存regression baseline、全GREEN（0 failures）:**
- repo A: `test_funnel.py`(6/6) `test_dedupe.py`(7/7) `test_gig_run_shim_darwin.py`(exit 0) `test_gig_run_shim_no_human_touch.py`(exit 0) `passprep.test.mjs`(6/6) `self-improve.test.mjs`(28/28) `no-human-loop.test.mjs`(7/7) `bash -n gig-cli.sh`(OK)
- repo B: `test_cadence_evidence.py`(10/10) `test_cadence.py`(23/23) `test_loop_evaluators.py`(15/15) `test_weekly_compare.py`(5/5) `test_weekly_report.py`(12/12) `test_affiliate_evaluator_commission.py`(2/2)

`test_feasibility_fillforward.py`/`test_passprep_new_fields.test.mjs` を Read し、real `~/gig/strategy.json` を書き換えていないことを確認（前者は in-memory dict fixture のみ、後者は `HOME: homeDir`（tmpdir）override で spawnSync している — real path非接触）。

### 3. 境界・安全 — PASS

- **(a)** `git diff ec059d2^ 3df9081 -- skills/self/cadence-contracts.json` = 1 insertion/1 deletion、`gig.source` フィールドのみ変更、`kind` は `"row-exists"` のまま。`test_cadence_contracts_gig_source.py` で他5 loop（affiliate/video/bounty/founder-loop/pm-earner）の byte-for-byte 不変も確認済み（実行して確認）。
- **(b)** `gig-cli.sh` の壊れたパス修正: `grep -c '~/anicca/skills/human-funded/gig/'` = 0（旧パス残存なし）、`~/profitable-claude/skills/human-funded/gig/passprep.py` および `.../scripts/coconala/APPLY_RUNBOOK.md` が各1回以上出現。`bash -n gig-cli.sh` = SYNTAX_OK（single-quote STARTUP 内アポストロフィ問題なし）。
- **(c)** `strategy.default.json`（seed）の変更が LIVE `~/gig/strategy.json` を上書きしないこと: 実際に LIVE ファイルを確認し、`listing_categories`/`feasibility_rules`/`listing_playbook` キーがまだ存在しない（このfeatureはまだ本番へmerge/pushされておらずcronは旧passprep.pyのまま動いている）ことを確認。かつ `merge_missing_keys` は追加専用（既存キーは一切上書きしない）ことをコード読解＋テストで確認済み — deploy後もLIVEの自己改善済み値（`apply_skip_thresholds.max_applicants:12`, `category_performance`等）は保持される設計。

### 4. 判断のハードコードのハードコード検査 — PASS

- `grep -n "import re\|re\.compile\|re\.match\|re\.search"` を diff対象の全実装ファイル（`passprep.py`/`funnel.py`/`funnel_report.py`/`gig-cli.sh`/`cadence-evidence.py`/`evaluator.py`）に対して実行し、**0件**。feasibility 判定・category 選定・提案文の judgment は全て `gig-cli.sh` STARTUP プロンプトの自然文（`strategy.json.feasibility_rules` のprose参照）に委譲されており、regex/keyword配列によるハードコードなし。`~/.claude/rules/building-effective-ai-agents.md` の rule に準拠。
- B4 の search half + metrics half: `grep -o 'if cold_start'` = 0件（skip条件としての `cold_start` 分岐なし）、STARTUP テキストを直接読み、「BOTH halves below run on EVERY do_improve pass, never only one」の文言と、SEARCH HALF/METRICS HALF の両方が無条件文として記述されていることを確認。`cold_start` は emphasis modulator としてのみ使われる（PROP-024/025の要求通り）。

### 5. ★Dais 制約 — PASS

`grep -rni "AI.*disclos|disclos.*AI|AI利用.*明記|AIであること|AI生成.*である旨|human-style pass|I am an AI|as an AI"` を repo A の変更ファイル全体（テスト除く）と repo B の3変更ファイルに対して実行し、**両repoとも0件**。「違法/scam skip」の文言（`illegality/scam/ToS-violation`）はSTARTUPプロンプト内に1件のみ存在し、これは許容された never-refuse clause の一部（feasibleかつ合法な依頼は断らない、というルールの唯一の例外条件）。

### 6. 占い再分類 / LIVE strategy.json 無変更 — PASS

- `strategy.default.json`（seed）: `skip_categories` は0件（占いエントリなし）、`listing_categories` に `霊感/スピリチュアル/占い`（tier standard, price_jpy_initial 2000/target 3500, notes "AI-completable text-reading content, saturated market, repeat-purchase culture"）が1件のみ存在。REQ-GFV-003のAcceptance Criteriaと一致。
- LIVE `~/gig/strategy.json` を実際に Read し、旧来の `霊感/スピリチュアル/占い (requires psychic abilities)` skip エントリが**そのまま残存**していることを確認 — ただしこれは behavioral-spec.md REQ-GFV-003 の Edge Cases（55-57行目）で明示的に許容された設計（「live file's skip_categories を強制書き換えしない、217パス分の自己改善judgmentを保護する」）であり、bug ではない。次パスの B4 self-improve の agent judgment、または手動migrationでの除去を意図的に許容している。

---

## Findings

Blocking: 0件。Major: 0件。Minor: 0件。

補足観察（non-blocking、記録のみ）:
- LIVE `~/gig/strategy.json` の `skip_categories` から占いエントリが実際に除去されるのは、このfeatureのdeploy後、B4 self-improve pass（agent judgment）または手動migrationが実行されて初めてであり、merge直後に自動で反映されるわけではない。spec が明示的にこの trade-off を認めているため blocking にはしないが、Dais/team-leadが「reclassification が即座に効く」ことを期待している場合は認識齟齬に注意。

## 検証実行ログ（自分で実行したコマンドの要約）

- 両worktree: `git log`/`git diff --stat`/`git show <commit> -- <file>` でコミット内容確認
- repo A: 7 python + 1 mjs 新規テスト + 4 regression（python2 + mjs3）+ `bash -n` を個別実行、全GREEN
- repo B: 6 python 新規テスト + 6 regression python を個別実行、全GREEN
- `grep` によるstatic inspection: broken path残存確認、never-refuse clause、category field要求、cold_start非skip条件、regex不使用、AI disclosure不存在
- `python3 -c` によるJSONインラインスクリプトで `strategy.default.json`/LIVE `~/gig/strategy.json` の実データ確認
