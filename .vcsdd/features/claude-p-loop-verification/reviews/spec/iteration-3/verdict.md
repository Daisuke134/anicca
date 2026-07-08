# Spec Review Verdict — claude-p-loop-verification (Phase 1c, iteration 3)

Reviewer: fresh-context adversary（Builder コンテキストなし、iteration-1/2 adversary ともコンテキスト
非共有）。判定はディスク上の artifact のみから行った:
- `.vcsdd/features/claude-p-loop-verification/specs/behavioral-spec.md`
- `.vcsdd/features/claude-p-loop-verification/specs/verification-architecture.md`
- `docs/superpowers/specs/2026-07-08-claude-p-loop-verification-evidence-design.md`（設計正本、§Cadence
  Contract表 40-72行を Read で再確認）
- `.vcsdd/features/claude-p-loop-verification/reviews/spec/iteration-1/verdict.md`
- `.vcsdd/features/claude-p-loop-verification/reviews/spec/iteration-2/verdict.md`

G1 修正の裏取りとして `~/anicca/skills/self/healthcheck-runtime-loop.sh` を実際に Read し、97行目
（`check "claude-p-pm" "ai.anicca.pm-earner" interval "$HERE/../earn/polymarket-trade/earner.log" 40`）
の実装が spec の記述（pm-earner の `earner.log` に対する40分閾値）と一致することを確認した。加えて
`~/anicca/skills/earn/polymarket-trade/redeem.py` を Read し、`record_row()` が `"polymarket-redeem"`
ラベル・`f"redeem-{conditionId[:10]}"` id で `~/anicca/skills/earn/state/earn-ledger.jsonl` に行を
記帳する実装を確認し、REQ-LV-104 が言う「redeem 行」が実データ上区別可能であることを裏取りした。

## A. G1（iteration-2 blocking）の解消判定

**解消 — PASS。**

根拠:

1. **REQ-LV-100** が `hourly-pass` サブ条件の `kind` を `"pass-marker"` から新設 `"recency"` へ変更した
   （behavioral-spec.md:314-317）。`recency` の contract スキーマは `{"kind":"recency","source":...,
   "max_age_min":<int>}` で、`boundary_tz` フィールドを持たないことが明示されている（behavioral-spec.md:312、
   「JST暦日境界に依存しない」）。
2. **REQ-LV-101** の `kind=="recency"` 分岐（behavioral-spec.md:334-340）は
   `(evidence["now_epoch_seconds"] - evidence["marker_epoch_seconds"]) <= contract["max_age_min"] * 60`
   という**エポック秒差の直接比較**で判定する。これは G1 が指摘した欠陥（「暦日イコール判定は日単位の
   粒度しか持たず、00:01に1回動いて23時間59分止まっていたケースを`true`と誤判定する」）を構造的に解消
   する——JST 暦日境界を一切参照しないため、暦日をまたぐかどうかに関係なく経過時間そのものを測る。
3. **PROP-LV-040**（verification-architecture.md:105）が G1 が指摘した正確なシナリオ（`marker`=当日00:01、
   `now`=同日21:00、経過≈75540秒 > `max_age_min*60`=2400秒）を直接のテストケースとして持ち、期待値
   `false` を明示している。境界値（2400秒ちょうど→true、2401秒→false）も含め、実装すべき比較演算子
   （`<=`）まで一意に固定されている。
4. **PROP-LV-037**（verification-architecture.md:104）の compound AND テストが、`hourly-pass` の
   bool 値を「決め打ち定数」ではなく PROP-LV-040 の `recency` 分岐の実出力から導出したものとして扱うと
   明記しており、compound と recency の結合自体もテスト対象になっている（G1 が指摘した「compound の
   ANDテストが hourly-pass を不透明な bool として扱っている」という欠陥も解消）。
5. `hourly-pass`/`recency` の全参照箇所（behavioral-spec.md 8箇所、verification-architecture.md 5箇所、
   grep で全量確認済み）を通じて、旧 `pass-marker`（暦日イコール判定）への言及が一切残っていない——
   置換が中途半端でない。

## B. 5次元の再判定

| # | 次元 | 判定 | 根拠 |
|---|---|---|---|
| 1 | Completeness | PASS | Goal 1-6・P0-1〜7・v2/v2.2 全指示（Cadence/EDD/Dashboard/Loop Scaling/OpenClaw統合）がEARS要件で網羅済み。G1修正はCadence Contractのkind種別を4→5に拡張しただけで、既存のカバレッジを欠損させていない |
| 2 | Testability | PASS | `recency`分岐のTier1テスト（PROP-LV-040: 境界値含む4ケース）と、`compound`分岐がその実出力を使うテスト（PROP-LV-037）が揃っている。row-exists/increment/pass-marker側（PROP-LV-020/021/022/035/036）はiteration-2から無変更でPASS済み。**非blocking観察**: REQ-LV-103の`streak()`をpm-earner（recency含むcompound）に適用する際、`evidence_by_date`の過去日分をどう収集するかは未規定——`recency`の evidence（現在mtime・現在epoch）は単一時点のスナップショットであり、過去日ぶんの`marker_epoch_seconds`/`now_epoch_seconds`を遡って再構成する手段がspecに書かれていない。ただしこれはG1修正が新規に持ち込んだ欠陥ではない（`pass-marker`＝founder-loopも同じ「mtimeは単一時点」という性質を持ち、iteration-2で既にPASS判定済み）。REQ-LV-103は`evidence_by_date`の構築を明示的に「呼び出し元の責務」としており（REQ-LV-101と同じ設計方針）、Phase 2の収集ロジック実装時に確定させるべき事項として扱うのが妥当——REQ-LV-070（video warmupバグの対象コードパス未確定）と同種の「Phase 2で確定」区分であり、blockingには格上げしない |
| 3 | Consistency | PASS | `hourly-pass`↔`recency`の対応关係はbehavioral-spec.md/verification-architecture.mdの全参照箇所（grep 13箇所）で一貫。**非blocking観察**: REQ-LV-100の compound スキーマ例に残る`"cadence":"1/hour"`フィールドはREQ-LV-101のどの分岐（row-exists/increment/pass-marker/recency/compound）からも読まれない（実際の頻度強制は`max_age_min:40`が担う）——iteration-2 G1が指摘した「死んだデータ」パターンの残滓だが、今回は対応する実効的な検証（`max_age_min`）が既に存在するため、誤った期待を生む実害はない（G1本体の問題＝検証ロジックの不在、ではなく単なる未使用metadataフィールド）。severityはcosmetic程度、blocking/majorではない |
| 4 | Reality-grounding | PASS | `healthcheck-runtime-loop.sh:97`の40分閾値・`earner.log`パス、`redeem.py`の`"polymarket-redeem"`/`redeem-<id>`行によるearn-ledger.jsonl記帳、を実ファイルRead/grepで再確認し、spec記載と一致した。v1/v2で既に確認済みの他ground truth（jobs.json enabled=103件等）に変更なし |
| 5 | Agent-vs-code boundary | PASS | `recency`分岐追加はG1修正の範囲内の決定論比較（エポック秒差の比較）のみで、新規judgmentのハードコードではない。他REQへの逸脱もなし |

## C. 収束確認（finding diminishment）

| iteration | blocking | major | minor | 傾向 |
|---|---|---|---|---|
| 1 | 1（F1: cadence_metが単一「行の存在」判定に固定） | 1（F2） | 3（F3/F4/F5） | — |
| 2 | 1（G1: F1修正の中でpm-earnerのhourly-passのみ同種欠陥が再導入） | 0 | 0 | F1系のスコープが「7 loop全体」→「pm-earnerの1サブ条件」に縮小。F2〜F5は完全解消 |
| 3 | **0** | 0 | 0（非blocking観察2件のみ、いずれも新規finding番号を採番するに値しない程度） | G1完全解消。新規blocking/major finding なし |

同種finding（「artifactの存在/単一時点スナップショットだけで健全性を誤判定する」欠陥クラス）は
iteration 1→2→3で「7 loop全体」→「pm-earnerの1サブ条件」→「解消」と単調に縮小しており、finding
diminishment・specificityの両方の収束基準を満たす。新たな欠陥クラスの出現もない。重複finding（同一
根本原因を異なるIDで再掲するもの）も無い。

## 総合判定

**PASS** — blocking finding 0件、major finding 0件。iteration-1のF1〜F5、iteration-2のG1、全て解消
確認済み。非blocking観察2件（streak()のrecency分過去日evidence収集方法の未規定、`cadence:"1/hour"`の
未使用metadataフィールド）を記録するが、いずれもPhase 2実装時の確定事項として扱えばよく、Phase 1c
のgate条件（存在しないsymbol/path参照なし・判断のハードコードなし・各REQにTier1/2の具体的検証手段あり）
を妨げない。

## 次フェーズへの申し送り（非blocking、記録のみ）

1. REQ-LV-103の`streak()`をpm-earner（`recency`含む`compound`）に適用する際の`evidence_by_date`過去日分
   収集方法をPhase 2着手時にspecへ確定させること（founder-loopの`pass-marker`にも同じ性質の未規定が
   既にあり、この2 kind双方に共通する論点として扱ってよい）。
2. REQ-LV-100の`hourly-pass`スキーマ例にある`"cadence":"1/hour"`フィールドは`cadence_met`のどの分岐
   からも読まれないドキュメント専用値であることをコメント等で明示するとPhase 2実装者の混乱を避けられる
   （必須修正ではない）。

## サマリ表

| ID | Severity | 対象REQ | 状態 |
|---|---|---|---|
| F1（iter1） | blocking | REQ-LV-100〜104,120,135 | 解消（iter2で6/7、iter3でpm-earner分含め完全解消） |
| F2（iter1） | major | REQ-LV-120,100 | 解消（iter2） |
| F3（iter1） | minor | REQ-LV-100 | 解消（iter2） |
| F4（iter1） | minor | Ground truth節 | 解消（iter2） |
| F5（iter1） | minor(非blocking) | Goal 6 | 解消（iter2） |
| G1（iter2） | blocking | REQ-LV-100,101,104 | **解消（iter3）** — `recency` kind新設により pm-earner hourly-pass が実際に時間粒度で判定可能になった |
