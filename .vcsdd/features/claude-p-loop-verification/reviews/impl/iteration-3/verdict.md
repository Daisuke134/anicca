# Phase 3 実装レビュー verdict — claude-p-loop-verification / iteration-3（sprint 2）

Reviewer: fresh-context adversary（Builder / iteration-1,2 adversary いずれとも文脈非共有、disk artifacts + 実機 launchd/launchctl 状態 + 実行テスト結果のみから判定）

Scope: sprint 2 の新規 diff。
- `~/anicca/.worktrees/loop-verification`（branch `feature/loop-verification`、HEAD `dad2fed`）: commits `260913d`(REQ-LV-018 founder-loop mail配線) `67b3035`(REQ-LV-050/051 launchd plist) `e4e7224`(REQ-LV-104 env-var override seam + healthcheck-lib scope note) `4ed3fc9`(REQ-LV-012/013/014/017 video TikTok + pm verify_positions) `dad2fed`(REQ-LV-020/021/031/111/113 EDD + weekly_report.py + verify-loops-audit.sh 21:00 escalation/週次配線)
- `~/profitable-claude/.worktrees/loop-verification`（branch `feature/loop-verification`、HEAD `002a8f1`）: sprint2新規分 `049a8d4`(REQ-LV-015/016 funnel_report.py CLI + F-VERIF-5 dedupe fix) `705bb3e`(REQ-LV-014 affiliate_verify.py) `002a8f1`(EDD STARTUP prompt)（`496ad22`はiteration-2で既レビュー済みのため対象外）
- 前提: spec（`specs/{behavioral-spec.md,verification-architecture.md}`）、iteration-1/2 verdict、Phase5 `verification/verification-report.md`（F-VERIF-1〜5）

## 総合判定: **FAIL**（blocking 3件、major 1件）

---

## 1. REQ-LV-102/104「21:00 JST 未達 → self-fix escalate」の配線確認

### F-ITER3-1（BLOCKING）: REQ-LV-102 の 21:00 JST トリガーがカレンダー非固定の rolling interval に乗っており、恒久的に一度も発火しない可能性がある

`skills/self/verify-loops-audit.sh:46`（`if [ "$NOW_HOUR_JST" -ge 21 ] ... then escalate`）自体のロジックは正しい（実装・マーカーによる1日1回制限も妥当）。しかし、このチェックを実行する launchd job `ai.anicca.verify-loops-audit.plist` は

```
$ plutil -p ~/Library/LaunchAgents/ai.anicca.verify-loops-audit.plist
"StartInterval" => 21600   # 6h、カレンダー非固定
```

`StartCalendarInterval`（`Hour`/`Minute` 固定）ではなく `StartInterval`（load/前回起動からの相対秒数）である。1日4回（6h間隔）の起動時刻は load 時点のオフセット `o∈[0,6)` により `o, o+6, o+12, o+18`（mod 24）に固定され、`[21:00, 24:00)` という3時間幅の窓に一度でも入るのは `o∈[3,6)` の場合のみ——**オフセットの半分（`o∈[0,3)`）では、その日 4 回の実行が一度も 21:00 以降に落ちず、REQ-LV-102 の escalation 条件が一切評価されないまま日付が変わり、翌日分の cadence 判定に上書きされる**（`cadence-evidence.py` は「今日」を再計算するため、見逃された前日の未達は再チェックされない）。

このコードベース自身に、まさにこの「1日のうちの特定時刻に確実に起動する」ケース向けの確立されたパターンが存在する:

```
$ plutil -p ~/Library/LaunchAgents/ai.anicca.cfo-daily.plist
"StartCalendarInterval" => { "Hour" => 9, "Minute" => 0 }
$ plutil -p ~/Library/LaunchAgents/ai.anicca.agentmail-nudge.plist
"StartCalendarInterval" => { "Hour" => 9, "Minute" => 0 }
```
（`autohedge.plist` も同様）。REQ-LV-102 は copy+tweak すべきこの既存パターンを使わず、既存の 6h 汎用監査 interval に相乗りさせた設計になっている。

**根拠（実測）**: 直近ログの実行時刻は `06:32 / 12:32 / 16:03 / 17:03`（本日 2026-07-08、開発中の複数回 launchctl reload によるオフセットのブレを含む）。安定稼働時のオフセットが `o∈[0,3)` 側に落ち着けば、`NOW_HOUR_JST -ge 21` が真になる瞬間はスケジュール上存在しなくなる——これは「稀に遅延する」ではなく「原理的に半分の確率で恒久的に一度も起きない」という設計上のギャップである。

**修正方針（記録のみ）**: 21:00 チェック専用の `StartCalendarInterval`（例: Hour 21, Minute 5）付き launchd job を新設するか、既存 audit の `StartInterval` を 3h 以下（窓幅3hを必ず跨ぐ間隔）に短縮する。

---

## 2. founder-loop.sh mail 配線が record-earn.mjs / INV-H2/H3 を壊していないか

### 判定: **PASS**

`skills/self/founder-loop/founder-loop.sh` を読んだ（260913d, 19行追加）。
- mail 配線（52-69行）は `STATE.md` の atomic write（39-50行、INV-H3）**の後**に置かれており、STATE書き込みの構造・timing に変更なし。
- `$RECORD`（record-earn.mjs）呼び出し（24行目）・`$LEDGER` 読み取りは一切変更されておらず、record-earn.mjs は引き続き ledger の唯一の writer（INV-H2 unaffected）。
- エラー伝播: `REPORT_JSON` の node 呼び出しは `2>/dev/null` でエラーを握りつぶし、失敗時は空文字列 → `if [ -n "$REPORT_JSON" ]` で後続処理がスキップされる。`loop-report.sh` 呼び出し自体も `|| true` で握りつぶす。mail 経路のどの失敗も `set -uo pipefail` 下でスクリプトを落とさない。
- `exit "$RC"`（73行、INV-H6）は record-earn.mjs の実終了コードのままで、mail 配線の成否に一切影響されない。
- `report-args.mjs::founderReportArgs()` の `evidence` は成功時 `increase +N USDC, wallet 0x810f...`、非増分時 `none: ${status}` — REQ-LV-003 の evidence gate（bare "none" 拒否）を正しく満たす形式。

新たな問題なし。iteration-2 で確認済みの evidence gate 実挙動（`lr_valid_evidence`）にも抵触しない。

---

## 3. F-VERIF-5（gig funnel 多重カウント）dedupe 解消確認

### 判定: **PASS**（実行して確認）

`skills/human-funded/gig/funnel.py::dedupe_latest_status()` を実際にテスト実行:
```
$ python3 skills/human-funded/gig/__tests__/test_dedupe.py
=== test_dedupe: 7 passed 0 failed ===
```
同一 requestId 3行（applied→replied→受注）→ dedupe後1行（最新状態）に正しく縮退し、多重カウント（旧: applied:3,replied:2,won:1）が単一カウント（新: applied:1,replied:1,won:1）に修正されることを確認。`funnel_report.py`（049a8d4）が実際に `dedupe_latest_status()` を経由してから `summarize_gig_funnel()` を呼ぶ配線になっていることをソース確認済み。実データでの smoke test（`/tmp/gig-repro/applied.jsonl` 4行→`funnel_report.py`実行→`applied:2,replied:1,won:1`）でも dedupe が実際に効くことを確認した。bounty 側は `gated.json` の集計値を直接読む設計のため dedupe 不要（構造的にこの問題が起きない）。

---

## 4. affiliate ground-truth 訂正（`commission_jpy=null`固定）と EDD 要件の整合性

### F-ITER3-4（MAJOR）: `commission_jpy` フィールド名と evaluator が読む `earn_jpy` の不一致により、`commission_jpy` が null でなくなった場合でも affiliate evaluator の収益項が恒久的に効かない

`affiliate_verify.py`（705bb3e）が `~/.cloak/affiliate-metrics.jsonl` に書く行の shape は `{ts, slideshow_url, views, commission_jpy, ok}`。`commission_jpy` を常に `null` にする設計判断自体は spec Ground truth（Amazon月次集計しか取得できず投稿単位の按分は不可能）に忠実で、捏造しない原則にも合致しており妥当。

しかし `skills/self/self-improve/affiliate/evaluator.py` が呼ぶ `skills/self/self-improve/lib/ledger_metrics.py::score_from_rows()`:
```python
total_earn = sum(float(r.get("earn_usdc") or r.get("earn_jpy") or 0) for r in rows)
```
は `earn_usdc`/`earn_jpy` というキーしか見ない — `commission_jpy` というキー名を一切参照しない。これは「値がnullだから0になる」のではなく「**キー名が違うので存在してもしなくても常に0になる**」というバグであり、`commission_jpy=null固定`という設計判断とは独立した問題である。将来 Amazon 側の仕様変更などで投稿単位の按分が可能になり `commission_jpy` に実数値が入るようになったとしても、このコードは黙って収益項を0として扱い続ける。

`evaluator.py` 自身のdocstringは「`combined_score = views weight + commission earn weight`」（2語構成のスコア）を謳っているが、実態は views のみのスコアである。`test_loop_evaluators.py`・`test_affiliate_verify.py`のいずれも `commission_jpy`/`earn_jpy` のキー名一致を検証しておらず、このギャップは既存テストで検出されない。

**根拠**: `ledger_metrics.py:33`、`affiliate_verify.py:69`（実ソース比較）。修正方針（記録のみ）: `score_from_rows` に `r.get("commission_jpy")` を追加するか、affiliate 固有の evaluator ラッパーで別途フィールド名を吸収する。

---

## 5. weekly_report の週1回 marker gate と verify-loops-audit の 6h 周期の整合性

### F-ITER3-2（BLOCKING、実行して再現）: `weekly_report.py` が Cadence Contract の row-exists 判定と**同じledgerファイル**に書き込むため、週次レポート実行日に「今日は何もしていないのに達成済み」という偽陽性が発生する

`skills/self/self-improve/weekly_report.py:106`（`run()`）は算出した `{ts, week_start, combined_score, beats_previous_week}` を、読み込み元と**同一の** `ledger_path`（例: affiliateなら`~/.cloak/affiliate-metrics.jsonl`、gigなら`~/gig/gig-funnel.jsonl`、clipなら`clip-earn-ledger.jsonl`、videoなら`earn-video-metrics-<handle>.jsonl`）に追記する。この4ファイルは同時に `cadence-evidence.py::_row_exists_event_dates()`（REQ-LV-101 `row-exists` kind の evidence 収集元）が読む ledger そのものであり、この関数は行の中身を一切見ず「`ts` フィールドが存在し、その日付が今日か」しか判定しない。

実際に再現した:
```
$ python3 skills/self/cadence-evidence.py status affiliate   # 空ledger（今日は何もしていない）
{"loop": "affiliate", "met": false, ...}
$ python3 skills/self/self-improve/weekly_report.py affiliate --ledger-path <同ファイル>
{"ts": ..., "week_start": "2026-07-06", "combined_score": 0.0, "beats_previous_week": false}
$ python3 skills/self/cadence-evidence.py status affiliate   # weekly_report実行「後」、実パスは依然ゼロ
{"loop": "affiliate", "met": true, "streak": 1, "scorecard": "✅posted-today (streak=1)"}
```

`weekly_report.py` が `verify-loops-audit.sh`（`EDD_LOOPS="clip affiliate video gig bounty"`）から週1回・marker gate 付きで呼ばれた**その回の audit 実行時点**で、対象4 loop（clip/affiliate/video/gig。bountyは`increment`kindが`checked`フィールドを要求するため偶然無傷）は cadence が「達成済み」に化ける——G1/F-VERIF-2 が潰そうとした「artifact が存在するだけで健全と誤判定する」欠陥クラスの、この feature 自身による再導入である。これは REQ-LV-102（1で指摘した恒常的未発火リスクとは独立に）の前提そのものを壊す: たとえ1の calendar-anchoring を修正しても、週次レポート実行日には本物の未達が隠蔽される。

**根拠**: `cadence-evidence.py:109-125`（`_row_exists_event_dates`は`ts`存在のみで判定）、`weekly_report.py:87-108`（同一ledgerへの追記）、上記の実行再現ログ。

**修正方針（記録のみ）**: `weekly_report.py` の追記先を各loopの ledger とは別ファイル（例: `<loop>-weekly.jsonl`）に分離する、または `_row_exists_event_dates()` 側で `week_start`/`combined_score` キーを持つ行を除外するフィルタを追加する。

---

## 6. 全テスト再実行 + `bash -n` + EDD prompt のハードコード判定チェック

### 判定: **テストは全green（回帰なし）、EDD文言はハードコードなし。ただし別軸でBLOCKING（F-ITER3-3）を検出**

`bash -n` 全4ファイル（founder-loop.sh, verify-loops-audit.sh, clip-cli.sh, video-cli.sh, gig-cli.sh, bounty-cli.sh, affiliate-cli.sh, affiliate/run.sh）: エラーなし。

再実行した既存+新規テスト（anicca側13スイート + profitable-claude側4スイート + loop-report.sh + EDDプロンプトgrepテスト2本）は**全て green、0 failed**（回帰なし）:
`test_cadence`(23) `test_cadence_evidence`(10) `test_loop_evaluators`(15) `test_weekly_compare`(5) `test_weekly_report`(6) `test_guardrails`(14) `test_migration_gate`(3) `test_ytdlp_parse`(7) `test_positions`(5) `test_verify_positions`(7) `test_record_earn_onchain_wiring`(4) `test_selfimprove_tiktok`(13) `test-report-args.mjs` `test-loop-report.sh`(15) `test_funnel(gig)`(6) `test_dedupe`(7) `test_funnel(bounty)`(7) `test_affiliate_verify`(10) `test_startup_prompts_edd.sh`(anicca 8, profitable-claude 11)。

EDD STARTUP prompt追加文言（`dad2fed`/`002a8f1`）を実diffで確認: 「this reading is your judgment call, nothing here is scripted」「deciding what counts as a mistake is your judgment, not scripted」と明記されており、evaluator/weekly_compare/dedupe 等の決定論ツールは値を渡すのみで、その値に基づく改善判断自体はagentに委ねられている。`~/.claude/rules/building-effective-ai-agents.md` のjudgment hardcode禁止に抵触しない。

### F-ITER3-3（BLOCKING）: REQ-LV-050/051（healthcheck-runtime-loop.sh の launchd 配線、TaskList #5 `[completed]`）が実機に反映されていない

`67b3035` は `skills/self/launchd/ai.anicca.runtime-loop-healthcheck.plist` と README をrepoに追加したのみで、実機確認:
```
$ ls ~/Library/LaunchAgents/ | grep runtime-loop-healthcheck   # → ヒットなし
$ launchctl list | grep runtime-loop-healthcheck               # → ヒットなし（verify-loops-auditのみ存在）
```
README自身が「## Install (orchestrator step, NOT done by this commit)」と明記しており、`cp`＋`launchctl load`が意図的に未実施であることをBuilder自身が認識している。しかし REQ-LV-050 の文言は「THE SYSTEM SHALL...新規作成し...、`launchctl load` する」であり、install はこのrequirementのスコープ内。`cp`+`launchctl load`はDais個人資金の不可逆送金でも設計外broadcastでもなく、プロジェクトのno-human-loop方針（cron設置含め自分のツールで完結させる）の対象そのもの——「orchestrator step」に切り出す理由がない。

結果として、P0-5 が対象とする4つの healthcheck 対象（a3cdd4=20分/franklin=90分/pm-earner=40分/founder-proxy=120分のうちの最小値=20分以下の周期で監視するはずだったもの）は**現在いずれも新しい healthcheck-runtime-loop.sh によっては監視されていない**。TaskList上「#5 [completed]」という記載は実態と一致せず、プロジェクトCLAUDE.mdの「終わっていない作業をcompletedと書かない」に反する。

---

## 結論

**総合: FAIL（blocking 3件、major 1件）**。

| ID | severity | 内容 |
|---|---|---|
| F-ITER3-1 | BLOCKING | REQ-LV-102の21:00 JSTチェックが`StartInterval`(rolling 6h)に乗っており、load時オフセット次第で恒久的に一度も発火しない設計。既存の`StartCalendarInterval`パターン（cfo-daily等）を使うべきだった |
| F-ITER3-2 | BLOCKING | `weekly_report.py`が cadence 判定と同一ledgerに書き込み、週次レポート実行日に4/7 loop（clip/affiliate/video/gig）で偽陽性のcadence達成を発生させる。実行して再現済み |
| F-ITER3-3 | BLOCKING | REQ-LV-050/051（healthcheck-runtime-loop.sh launchd配線）が実機未反映。`launchctl list`・`~/Library/LaunchAgents/`いずれにも存在しない。TaskList「#5 completed」は実態と不一致 |
| F-ITER3-4 | MAJOR | affiliate evaluatorが`earn_jpy`キーを読むが実際のledgerは`commission_jpy`——nullうんぬん以前にキー名不一致で恒久的に収益項が0になる |

PASS判定した項目: founder-loop mail配線（INV-H2/H3非破壊）、F-VERIF-5 dedupe修正、既存+新規テスト全件green（回帰なし）、EDD prompt文言のjudgment非ハードコード、healthcheck-lib.sh scope-boundary claim（7 Cadence Contract loopは対象外という主張はgrepで実証済み）。

次のアクション: 3件のBLOCKINGを解消（1: launchd calendar-anchored trigger化 or audit interval短縮、2: weekly_report.py出力先分離 or row-exists側フィルタ、3: 実際に`cp`+`launchctl load`を実行して`launchctl list`で確認）した上で iteration-4 の再レビューへ。F-ITER3-4は次イテレーションでの修正を推奨（blocking昇格はしないが、EDD全体の信頼性に関わるため放置しない）。
