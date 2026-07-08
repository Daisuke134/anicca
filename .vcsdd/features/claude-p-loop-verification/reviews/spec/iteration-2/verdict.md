# Spec Review Verdict — claude-p-loop-verification (Phase 1c, iteration 2)

Reviewer: fresh-context adversary（Builder コンテキストなし、iteration-1 adversary ともコンテキスト非共有）。
判定はディスク上の artifact のみから行った:
- `.vcsdd/features/claude-p-loop-verification/specs/behavioral-spec.md`
- `.vcsdd/features/claude-p-loop-verification/specs/verification-architecture.md`
- `docs/superpowers/specs/2026-07-08-claude-p-loop-verification-evidence-design.md`（設計正本）
- `.vcsdd/features/claude-p-loop-verification/reviews/spec/iteration-1/verdict.md`（前回 findings）

v2 で新規に参照された ground truth（`healthcheck-lib.sh`, `evaluator.py`, `promote_gate.sh`,
`telemetry-collect.sh`, `_instance_paths.sh`, `dashboard.json`, `jobs.json`, `earner.log`,
`founder-loop.sh`/`record-earn.mjs` の INV ゲート）を Read/Bash/grep で実ファイルに対して裏取りした。

## A. iteration-1 findings の解消確認

| ID | Severity | 解消 | 根拠 |
|---|---|---|---|
| F1 | blocking | **部分解消**（6/7 loop は解消、pm-earner の compound 内 hourly-pass サブ条件に新たな gap — 下記 G1 参照） | REQ-LV-100/101 が `kind` 判別子で row-exists/increment/pass-marker/compound の4分岐へ一般化。clip/affiliate/video/gig（row-exists）、bounty（increment、`today_value>previous_value`で差分ゼロを正しく false 判定 — PROP-LV-035 で確認）、founder-loop（pass-marker、`STATE.md`のみ参照し`earn-ledger.jsonl`を参照しない設計は`founder-loop.sh`のINV-H3atomic writeで実際に裏取り確認済み）は設計spec §Cadence Contract表と正しく整合。ただしpm-earnerのcompound内`hourly-pass`条件（下記G1）は未解消 |
| F2 | major | **解消** | REQ-LV-120が`clip_promote_status(payout_rows, today_jst_date)`を新設し、clip-promoteの`status`を`cadence_met()`と独立に定義。PROP-LV-026が両方（7loop分のcadence_met一致 + clip-promoteの独立判定）を明示的にテスト |
| F3 | minor | **解消** | REQ-LV-100本文が「7 loop」に修正済み（grep確認: line 293, 169, 282 は正しく「7 loop」、残る「8 loop」表記（line 170/208/217/224/227/338/374）は全て「7 cadence loop + clip-promote = 8」という別の正しい文脈でのみ使われており数え間違いは残っていない） |
| F4 | minor | **解消** | Ground truth節が`~/profitable-claude/skills/human-funded/gig/gig-cli.sh`に修正され、旧誤記載への言及（「F4修正」）も明記。実ファイル `ls` で存在確認済み、実在しない`~/anicca/skills/human-funded/gig/`への言及は無くなった |
| F5 | minor(非blocking) | **解消** | REQ-LV-019（Goal 6の独立REQ、8 loop全てでE2E+adversary PASSをMUSTとして明記）+ PROP-LV-038（8loop中1つでも欠ければ全体PASSにならないことの集計チェック）が新設された |

## B. 5次元の再判定

| # | 次元 | 判定 | 根拠 |
|---|---|---|---|
| 1 | Completeness | PASS | Goal 1-6・P0-1〜7・v2の5指示（Cadence/EDD/Dashboard/Loop Scaling/OpenClaw統合）が全てEARS要件で網羅されている。F5解消によりGoal 6の非対称も解消。section L（v2.2スコープ縮小）もWave1/Wave2/非移行の3分類全てにREQが対応し、欠落なし |
| 2 | Testability | **FAIL（blocking 1件: G1）** | 下記G1参照。それ以外（row-exists×4loop, increment×bounty, pass-marker×founder-loop, clip_promote_status）は全てTier1純関数+具体的fixtureケース（PROP-LV-020/021/022/035/036/026）が揃っており testable |
| 3 | Consistency | PASS（G1と表裏、二重計上せず） | REQ-LV-100↔101↔103↔104↔120の`kind`命名・evidence構造（event_dates/today_value・previous_value/marker_jst_date/by_condition）は全箇所で一致。「7 loop」/「8 loop」の使い分けも文脈上矛盾なし |
| 4 | Reality-grounding | PASS | v2で新規追加されたground truth（`healthcheck-lib.sh`のOUT_STALE_HRSデフォルト30h付近の記述、`evaluator.py`の`evaluate_stage1/stage2`が`combined_score`を返す実装、`promote_gate.sh`実在、`telemetry-collect.sh`実在、`_instance_paths.sh`実在、`dashboard.json`の17キー完全一致、`jobs.json`のenabled:true=103件完全一致、`earner.log`実在＋`healthcheck-runtime-loop.sh`が40分間隔で参照している実装、founder-loop.shのSTATE.md atomic write＋record-earn.mjsのINV-1/3/7ゲート）を全て実ファイルに対してRead/Bash/grepで確認、記載と相違なし |
| 5 | Agent-vs-code boundary | PASS | v2追加分（Cadence Contract宣言・EDD evaluator・Loop Scaling gate・OpenClaw移行gate REQ-LV-141）も一貫して「判断はagent、記録・判定は決定論純関数」の境界を維持。`channel_migration_eligible`は`has_verification_tool`という既に確定した事実の恒等写像であり新規judgmentのハードコードではない |

## 総合判定

**FAIL** — blocking finding 1件（G1、新規）。iteration-1のF1〜F5は4件完全解消・1件（F1）が6/7 loopで解消したが、その修正自体の中に新しいgapが生じている。

## Findings（詳細）

### G1 — BLOCKING（新規）— compound kind の `hourly-pass` サブ条件が宣言した cadence（1/hour）を実際には検証できない

**対象REQ**: REQ-LV-100（compound スキーマ）, REQ-LV-101（`kind=="pass-marker"`分岐）, REQ-LV-104（pm-earner向けevidence収集）

**問題**:
design spec §Cadence Contract表（`docs/superpowers/specs/2026-07-08-...-design.md:67`）は pm-earner の契約を
「**1 pass/時** + redeem確認/日」と定義している。REQ-LV-100 はこれを `kind:"compound"` として
`{"id":"hourly-pass","kind":"pass-marker","cadence":"1/hour","source":"earner.log mtime",...}` +
`{"id":"daily-redeem","kind":"row-exists","cadence":"1/day",...}` の2条件ANDに分解した。

しかし REQ-LV-101 が定義する `kind=="pass-marker"` 分岐の実際の判定ロジックは、`evidence={"marker_jst_date":str}`
（呼び出し元がファイルの mtime を **JST暦日文字列** に変換した値）を受け取り、
`today_jst_date == evidence["marker_jst_date"]` を返すだけである。つまり pass-marker が実際に検証できるのは
「**その JST 暦日のうちに一度でもファイルが更新されたか**」という **日単位** の粒度のみであり、
時間単位（1時間ごとに動いているか）を区別する仕組みを一切持たない。

この結果、`hourly-pass` 条件は宣言上 `cadence:"1/hour"` を持つにもかかわらず、実際の判定関数は
「その日のうち00:01に1回だけ earner.log が更新され、その後23時間59分間 pm-earner loop が完全に停止していた」
ケースでも `true` を返す。つまり `cadence_met()` の compound 判定は、pm-earner loop が実際には
「1時間ごとに動いている」ことを一切保証しない。これは iteration-1 の F1 が指摘したまさにその欠陥クラス
（「artifact が存在するだけで健全と誤判定する」＝旧`fresh()`方式の欠陥）を、`compound`/`pass-marker` の
組み合わせを通じて pm-earner のhourly-pass 条件にだけ**再導入**している。

実際、既存の `~/anicca/skills/self/healthcheck-runtime-loop.sh:97` は pm-earner に対し
`earner.log` を **40分間隔のstaleness閾値**（"interval" 判定、`hc_run`の`HC_STALE_MIN`相当）で監視しており、
これは「直近X分以内に更新されたか」という recency ベースの判定である。REQ-LV-101 の pass-marker
（暦日イコール判定）はこの既存メカニズムとは全く異なる粒度であり、REQ-LV-100 が `hourly-pass` に
`pass-marker` kind を割り当てたこと自体が、既存の正しい検証手段（recency閾値）を参照せず、
より粗い（かつ設計意図と食い違う）判定方式を新たに導入している。

`cadence:"1/hour"` フィールドは REQ-LV-101 のどの分岐からも参照されない（pass-marker 分岐は
`contract["cadence"]`を一切読まない）ため、このフィールドは spec 上「宣言されているが検証されない」
死んだデータであり、実装者に誤った期待（hourly cadence が実際に強制されると誤解）を与える。

verification-architecture.md 側でもこの gap は捕捉されていない: PROP-LV-036（pass-marker のテストケース）は
founder-loop（真に日単位の契約）のみを対象とし、hourly粒度のケースは1件も無い。PROP-LV-037（compound の
ANDテスト）は `hourly-pass`/`daily-redeem` を単なる bool 値として扱っており、その bool がどう導出されるか
（=hourly recency を実際に測っているか）はテスト対象外。REQ-LV-104（evidence収集の責務規定）も
「pm-earnerのearner.log mtime+redeem行」とだけ書き、hourly粒度の収集方法を規定していない。

**Severity**: blocking — 理由は3点:
1. これは iteration-1 の F1 と**同一の欠陥クラス**（under-verification による偽陽性）であり、しかも F1 の
   修正そのもの（`kind`分岐の新設）の中で発生している——「直した箇所の中で同じ欠陥を再現した」ケース。
2. pm-earner は claude-p 自身の実資金トレーディングループであり、機能不全（1時間ごとに動くべきものが
   実際には日1回しか動いていない）を6h ごとの scorecard も21:00 JSTのescalationも検知できないまま
   `✅posted-today`と誤報告し続ける——本feature全体のGoal「機械検証済みevidenceで自分のoutputを自分で
   検証する」を pm-earner についてのみ無効化する。
3. `cadence:"1/hour"`という宣言と実装ロジックの乖離は、Phase 2実装者が「specに書いてあるから検証できている」
   と誤認するリスクを生む（この乖離自体を指摘するテストがverification-architecture.mdに存在しない）。

**修正提案**:
`kind=="pass-marker"`分岐を暦日イコール判定に固定するのではなく、`contract["cadence"]`の値
（`"1/day"` vs `"1/hour"`）に応じて判定粒度を変える（例: `cadence=="1/hour"`の場合は
`evidence`に`marker_epoch_seconds`と`now_epoch_seconds`を持たせ、差分が3600秒以内かを見る）か、
または新しい5番目の`kind`（例: `"recency"`、既存`healthcheck-runtime-loop.sh`の40分閾値パターンを
copy+tweak）を追加してpm-earnerの`hourly-pass`条件はそちらを使う設計に変更する。どちらの方向でも、
「宣言したcadenceの粒度を実際に判定関数が区別できる」ことをPhase 2着手前にspecへ反映し、対応する
Tier1テストケース（hourly recency の正常系/違反系）をverification-architecture.mdに追加すること。

### サマリ表

| ID | Severity | 対象REQ | 状態 |
|---|---|---|---|
| F1（iter1） | blocking | REQ-LV-100〜104,120,135 | 6/7 loop解消、pm-earner hourly-passはG1として継続 |
| F2（iter1） | major | REQ-LV-120,100 | 解消 |
| F3（iter1） | minor | REQ-LV-100 | 解消 |
| F4（iter1） | minor | Ground truth節 | 解消 |
| F5（iter1） | minor(非blocking) | Goal 6 | 解消（REQ-LV-019新設） |
| **G1（新規）** | **blocking** | REQ-LV-100, REQ-LV-101, REQ-LV-104 | 未解消 — pm-earnerのhourly-pass条件が宣言cadence(1/hour)を検証できない |

## 修正後の再レビュー条件

1. G1: `kind=="pass-marker"`のcadence粒度対応（`contract["cadence"]`分岐 or 新kind追加）をREQ-LV-100/101/104に反映し、hourly recencyの正常系/違反系Tier1テストケースをverification-architecture.mdに追加する。
2. G1修正後、pm-earnerのcompound判定が「00:01に1回動いただけの日」を`hourly-pass=false`として正しく検知できることを新規テストケースで確認する。

blocking 0件に収束すれば次のiterationでPASS相当と判断できる規模の修正（G1は1箇所の設計変更で閉じる）。
