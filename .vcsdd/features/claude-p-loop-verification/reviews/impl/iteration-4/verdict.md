# Phase 3 実装レビュー verdict — claude-p-loop-verification / iteration-4（sprint 2 再レビュー）

Reviewer: fresh-context adversary（Builder / iteration-1〜3 adversary いずれとも文脈非共有、disk artifacts + 実機 launchd/launchctl 状態 + 実行テスト結果のみから判定）

Scope: iteration-3 verdict（blocking F-ITER3-1/2/3 + major F-ITER3-4）に対する修正 commit。
- `~/anicca/.worktrees/loop-verification`（branch `feature/loop-verification`、HEAD `f64b279`、iteration-3時点の`dad2fed`から1 commit進行、worktree clean）
- 前提: spec（`specs/behavioral-spec.md` REQ-LV-102/103/104/050/051、`specs/verification-architecture.md`）、iteration-3 verdict

## 総合判定: **PASS**（blocking 0件、major 0件。deployment-gated残作業1件あり、下記F-ITER3-3参照）

---

## A. F-ITER3-1（21:00 JST cadence-deadline escalationのcalendar-anchoring）: **RESOLVED**

`skills/self/cadence-deadline-check.sh`（新規46行）を専用スクリプトとして切り出し、`skills/self/launchd/ai.anicca.cadence-deadline-check.plist`（新規）で `StartCalendarInterval{Hour:21, Minute:5}` により起動する設計に修正されている。

- `plutil -lint skills/self/launchd/ai.anicca.cadence-deadline-check.plist` → `OK`（構文検証済み）。
- 既存の `ai.anicca.agentmail-nudge.plist`（実機、`plutil -p`で確認）と同型の `StartCalendarInterval{Hour,Minute}` + `StandardOutPath`/`StandardErrorPath` 構造で、iteration-3 verdictが指摘した「cfo-daily/agentmail-nudgeパターンをcopy+tweakすべき」に忠実に従っている。
- `verify-loops-audit.sh` からも同スクリプトを冗長呼び出ししているが（`bash "$SELF/cadence-deadline-check.sh"`）、`.cadence-escalated-$L-$TODAY_JST` マーカーファイルにより同一JST日内の二重escalationは実際にno-opになる（下記テストで確認）。旧`NOW_HOUR_JST`変数は`verify-loops-audit.sh`から完全に除去されており、ダングリング参照なし（grep確認済み）。
- `CADENCE_DEADLINE_NOW_HOUR_JST` テスト専用override seamは本番経路（`date +%H`フォールバック）を汚さない、既存の`EARN_LEDGER`/`FOUNDER_TEST`規約と同型。

`skills/self/tests/test_cadence_deadline_check.sh` を実行:
```
=== test_cadence_deadline_check: 3 passed 0 failed ===
```
21:00前のno-op、21:00時点での7 loop全escalation、同日2回目呼び出しでのmarker-gate抑制の3シナリオを実際に確認した。

## B. F-ITER3-2（weekly_report.py出力分離による偽陽性解消）: **RESOLVED**

`weekly_report.py::_weekly_output_path()`（新規）が `<ledger>-weekly.jsonl` という兄弟ファイルを算出し、`run()`のデフォルト書き込み先を元のledger自体から分離した。`verify-loops-audit.sh:63`の呼び出し（`python3 "$SELF/self-improve/weekly_report.py" "$L"`）は`--output-path`を渡していないため、このデフォルト分離が実際に効く経路になっている。

`cadence-evidence.py`の全5 loopのledgerパス解決関数（`_clip_ledger_path`等、grep確認）はいずれも単一の明示パスを返すのみでglob/wildcard読み込みはなく、`-weekly.jsonl`兄弟ファイルが`row-exists`判定に混入する経路は存在しない。

`test_weekly_report.py`を実行（iteration-3のadversary再現シナリオがそのまま回帰テスト化されている）:
```
=== test_weekly_report: 12 passed 0 failed ===
```
「weekly_report実行前後でaffiliateのempty-todayledgerに対する`cadence-evidence.py status`が`met=false`のまま変わらない」ことを実行して確認した——iteration-3で実際に再現されたバグの正確な回帰シナリオが green。

## C. F-ITER3-4（affiliate evaluatorのearn fieldキー名不一致）: **RESOLVED**

`ledger_metrics.py::score_from_rows()`のearn field fallback chainに`r.get("commission_jpy")`を追加（`earn_usdc → earn_jpy → commission_jpy`）。加算的（additive）な変更であり、grep確認の結果、clip/video/gig/bountyのいずれのledger writerも`commission_jpy`キーを書き込まないため他loopのスコアリングに影響なし。

`test_affiliate_evaluator_commission.py`（新規）を実行:
```
=== test_affiliate_evaluator_commission: 2 passed 0 failed ===
```
`commission_jpy=null`時はearn項0（捏造しない）、実値500.0が入った場合に`combined_score`が100(views)+500(commission)=600.0に正しく反映されることを確認した。evaluatorのdocstringが謳う「views weight + commission earn weight」が実装と一致する状態になった。

## D. F-ITER3-3（healthcheck-runtime-loop.sh launchd配線の実機反映）: **DEPLOYMENT-GATED（このiterationではblockingとしない）**

commit message通り、実機`cp`+`launchctl load`は今回のcommitに含まれていない。実機確認:
```
$ ls ~/Library/LaunchAgents/ | grep -E "cadence-deadline|runtime-loop-healthcheck"   # ヒットなし
$ launchctl list | grep -E "cadence-deadline|runtime-loop-healthcheck"               # ヒットなし
```
これは判断の結果として**blockingにしない**。理由:

1. **役割分担の正当性**: 両plist（`ai.anicca.cadence-deadline-check.plist`と`ai.anicca.runtime-loop-healthcheck.plist`）は`ProgramArguments`に`/Users/anicca/anicca/skills/self/...`という絶対パスを持つ——これは`~/anicca`（現在`main`ブランチ、`feature/loop-verification`は未merge）上の実パスである。**現時点で`cp`+`launchctl load`を実行すると、`~/anicca`のmainブランチにまだ存在しないスクリプトを指すjobを実機に登録することになり、むしろ壊れた状態を作る**。install はmerge後でなければ正しく実行できない——これはBuilderが逃げているのではなく、実際にorchestrator（merge実行者）の後工程でなければ意味をなさない技術的な制約である。
2. **TaskList整合性の改善確認**: iteration-3 verdictが問題視した「TaskList #5が実態と不一致のまま`[completed]`」という点は、現在のTaskListで`#5 P0-5: healthcheck-runtime-loop.sh を launchd 配線`が`[in_progress]`と正しく記載されており是正済み（虚偽のcompleted主張は解消されている）。
3. **deployment-readiness自体は検証済み**: 両plistとも`plutil -lint`でOK、`ProgramArguments`のパスがmerge後の`~/anicca`実パスと整合、`StandardOutPath`/`StandardErrorPath`が実在の`~/.openclaw/logs/`規約に整合、README（`skills/self/launchd/README.md`）のInstall/Verify/Uninstall手順が正確（コマンド自体を実行すれば動く内容）であることを確認した。

**残作業（converge/E2Eフェーズで必須、これ単体は今回blockingにしない）**: `feature/loop-verification`merge後に、両plistの`cp`+`launchctl load`を実機で実行し、`launchctl list`でPID/次回起動が確認できることをfresh evidenceとして検証すること。これが完了するまでP0-5はcompletedと書いてはならない（現状の`[in_progress]`表記は正しい）。

---

## E. 全テストスイート再実行（回帰なし確認）

`~/anicca/.worktrees/loop-verification`側:
```
test_cadence(23) test_cadence_evidence(10) test_loop_evaluators(15) test_weekly_compare(5)
test_weekly_report(12, F-ITER3-2回帰込み) test_affiliate_evaluator_commission(2, 新規)
test_guardrails(14) test_migration_gate(3) test_cadence_deadline_check(3, 新規)
test_startup_prompts_edd(8) test-healthcheck-lib(6) test-healthcheck-runtime-loop(12)
test-self-fix(13) test-founder-loop(PASS) test-record-earn(PASS)
```
全green。`bash -n`（cadence-deadline-check.sh, verify-loops-audit.sh）エラーなし。

`~/profitable-claude/.worktrees/loop-verification`側（HEAD `002a8f1`、iteration-4での変更なし、回帰確認のみ）:
```
test_affiliate_verify(10) test_measure_commission(6) test_dedupe(7)
test_funnel-gig(6) test_funnel-bounty(7) test_startup_prompts_edd(11)
```
全green、回帰なし。

---

## 結論

**総合: PASS（blocking 0件、major 0件）**。

| ID | iteration-3 severity | iteration-4 判定 |
|---|---|---|
| F-ITER3-1 | BLOCKING | RESOLVED（StartCalendarInterval化、実行テストで確認） |
| F-ITER3-2 | BLOCKING | RESOLVED（出力分離、adversary再現シナリオの回帰テストで確認） |
| F-ITER3-3 | BLOCKING | DEPLOYMENT-GATED（merge後のorchestrator実機install待ち。今回のcode-review dimensionはblockingにしない。TaskList表記は是正済み） |
| F-ITER3-4 | MAJOR | RESOLVED（additive fallback追加、他loop無影響を確認） |

次のアクション: `vcsdd-converge`（または次フェーズ）へ進行可。ただしF-ITER3-3の実機`launchctl load`実行 + `launchctl list`でのfresh evidence確認は、feature全体のE2E完了条件として明示的に残す（P0-5を`completed`にする前提条件）。
