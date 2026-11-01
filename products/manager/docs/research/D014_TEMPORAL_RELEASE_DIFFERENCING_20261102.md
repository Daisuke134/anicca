# D014 — 時系列の重複公開による differencing リスクの事前警告

**2026-11-02 JST · Manager research branch · P0 synthetic-only engineering**

Canonical progress authority: `docs/roadmap/tasks.json`. D014 remains **todo** because the external acceptance still requires appropriate ethics review, partner cooperation and availability of suitable published aggregates. H005 remains **blocked**; this work does not use HeartSteps or infer missing study-day data.

## 問い → 仮説 → 反証（imozuru）

**問い:** 同じ地域・同じ集団記述・同じ単位・同じアウトカムについて、別々の期間として公開された集計表は、単に期間文字列が異なるという理由で時間的な differencing の検討対象から外してよいか。

**危険な仮説 H0:** 期間が同一でなければ、表は比較不能なので追加の警告は不要。

**一次資料から得た反証:** Government Analysis Function の 2026-08-19 行政データ向け SDC 指針は、同一データセットからの過去のリリースとの linking/differencing、頻繁な同一指標の公開、日次・月次等の反復出力による小さな変動を考慮するよう求める。ONS の Future Population and Migration Statistics 方法論（2023-12-07改訂）は、反復公開の小さな時間差が小人数の純変化を示す可能性と、公開頻度がリスクに影響することを具体例で説明する。

**限定命題 H1:** 同一の route/outcome/description/unit/geography で、期間が厳密な `YYYY-MM-DD/YYYY-MM-DD` 形式として読み取れ、二つの異なる期間が日付単位で重なる場合、Managerは `CROSS_RELEASE_POSSIBLE_TEMPORAL_DIFFERENCING` を追加する。3件以上の release family では `FAMILY_POSSIBLE_TEMPORAL_DIFFERENCING` に伝播する。警告は review-only で、件数差分の計算・個人推定・データ取得・公開・介入は行わない。

## 一次資料（公式原典）

1. Government Analysis Function, *Statistical Disclosure Control for tables produced from administrative data*, published 2026-08-19.  
   https://analysisfunction.civilservice.gov.uk/policy-store/sdc-for-tables-produced-from-administrative-data/  
   Relevant guidance: linked tables and differencing (including non-coterminous geographies and slightly different classifications); risk from frequent releases of the same measure and small fluctuations between daily/monthly/quarterly outputs.

2. Office for National Statistics, *Disclosure control proposal for Future Population and Migration Statistics*, last revised 2023-12-07.  
   https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates/methodologies/disclosurecontrolproposalforfuturepopulationandmigrationstatistics  
   Relevant guidance: longitudinal differencing from small changes between releases, the role of geographic level and release frequency, and cell-key perturbation as one possible protection method.

These sources motivate a conservative review warning, not a claim that every overlapping pair is disclosive. The provider and a reviewer with knowledge of the underlying population must assess actual cohort continuity, movement, revisions, denominator changes, suppression and any perturbation. Overlap alone does not prove common records or a recoverable value.

## 実装・反証テスト

- `manager_core/public_aggregate_cross_release.py`: parse only exact ISO date-only intervals; reject malformed/reversed values from this narrow parser by returning no temporal inference. For two distinct, valid, inclusive date intervals, warn only if they overlap and all non-window cohort descriptors, route and outcome match.
- `manager_core/public_aggregate_release_family.py`: propagate pairwise temporal warnings to the bounded 3–8 release family result.
- `tests/test_public_aggregate_cross_release.py`: synthetic partial overlap, containment, shared endpoint, disjoint periods, impossible date, reversed range and opaque free-text windows. Assert no subtraction, no data echo and all authority/effect flags remain false.
- `tests/test_public_aggregate_release_family.py`: one overlapping pair inside a three-release family remains visible as a review warning.

**Conservative date convention:** Date-only interval endpoints are treated as inclusive for screening. This is not a universal convention for every statistical source. If a source uses half-open intervals, timestamp windows, fiscal periods or rolling-window definitions, its owner must provide an explicit mapping; this helper intentionally does not guess.

## 証拠レベルと残件

- Code and synthetic tests: P0 engineering evidence only.
- No original aggregate dataset, participant row, private source, partner system or account was accessed.
- No source bytes, publisher identity, cohort identity, disclosure safety, consent, ethics approval or causal effect is authenticated by this function.
- No simulation or engineering test establishes a real intervention effect or reduced suffering.
- D014 remains `todo`; H005 remains `blocked`; no task status is promoted.

The implementation preserves `can_ingest=false`, `can_publish=false`, `can_execute=false`, `disclosure_certified=false`, `beneficiary_effect=NOT_MEASURED`, and `next_action=NO_ACTION`.
