# D014 — disclosure-method-aware aggregate comparison (2026-11-03 JST)

**Scope:** One offline, metadata-only engineering increment on the research branch. D014 remains todo: the collaboration/ethics/public-aggregate external acceptance is not met. H005 remains blocked; this work does not use HeartSteps or infer missing study-day data.

## 問い → 仮説 → 原典 → 反証（imozuru）

**問い:** 公開された表の数値に丸め・摂動が適用されている、またはその方法が不明なのに、Managerが正確な件数として合算・差分・抑制セル復元を試みてよいか。

**危険な仮説 H0:** 表示値と合計が整数であれば、同じカテゴリ名・母集団メタデータを持つ複数リリースを正確な件数として組み合わせられる。

**一次資料からの反証:**

1. Office for National Statistics (ONS), *Comparison of post-tabular statistical disclosure control methods*, released 3 May 2024, last revised 3 May 2024.  
   https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates/methodologies/comparisonofposttabularstatisticaldisclosurecontrolmethods  
   ONS describes the 10-5 rule (thresholding small counts and rounding larger counts) and cell-key perturbation (adding controlled noise). It explains that perturbation can protect against differencing because differently constructed or aggregated tables can contain inconsistencies. It also notes that the same combination of records can receive the same perturbation across tables. This is a method-specific design, not a universal guarantee.
2. ONS, *SRS Output Checking Guidance: Statistical Disclosure Control*, February 2025, sections 6.1.2 and 6.3.3.  
   https://www.ons.gov.uk/file?uri=/aboutus/whatwedo/statistics/requestingstatistics/secureresearchservice/gettingyourresearchoutputsapproved/srsoutputcheckingguidance.february2025.pdf  
   The guidance explains that rounded values may not sum to totals; where rounding is used as secondary disclosure control, it is applied consistently across all counts in the table. It treats secondary disclosure as a cross-output/differencing problem, not only a single-table problem.
3. Statistics Canada, *Statistics Canada Quality Guidelines — Disclosure control* (archived 2009 edition; historical guidance, not a current legal determination).  
   https://www150.statcan.gc.ca/n1/pub/12-539-x/2009001/control-controle-eng.htm  
   The agency describes residual disclosure from cross-referencing previous releases and overlapping categories/hierarchies. It notes that rounding or noise can affect accuracy and that absolute confidentiality cannot be guaranteed.

**限定仮説 H1:** The exact-count arithmetic checks in D014 are applicable only when every compared release explicitly declares exact_unmodified. If a method is rounded, perturbed, mixed, unknown, or omitted, the preflight must not use the displayed numbers to reconstruct a suppressed cell. It returns a fixed review reason and remains inert. This does not certify an exact release as safe.

**反証テスト:**
- Missing method plus a single suppressed cell must not trigger an arithmetic reconstruction reason.
- Rounded, perturbed and mixed declarations must skip small-cell, total-consistency and residual arithmetic that assumes exact counts.
- A pair with one exact and one unknown/adjusted release must skip pairwise arithmetic.
- A family of three perturbed releases must not trigger exact three-way reconstruction.
- An exact three-release subset must still be checked when a fourth unrelated release is rounded; an unrelated adjusted release must not mask a risk in the exact subset.
- All output remains fixed reason codes, no counts, category names, URLs, parameters or source text; all authority flags remain false.

## 実装

- manager_core/public_aggregate_preflight.py: optional strict disclosure_control.method field; missing means unknown. Allowed classifications are exact_unmodified, rounded, perturbed, mixed, unknown. The helper reports only whether exact arithmetic is eligible, not the publisher's method or its secret parameters. Numeric arithmetic in the single-release preflight is skipped unless the declaration is explicitly unmodified.
- manager_core/public_aggregate_cross_release.py: pairwise arithmetic is skipped unless both releases declare unmodified counts. Scope/temporal/source-alias warnings remain available because they do not require subtracting counts.
- manager_core/public_aggregate_release_family.py: family arithmetic requires unmodified counts; exact comparable subfamilies are still screened so an unrelated rounded release cannot mask a risk in three exact releases.
- Three synthetic test modules add seven regression methods. Existing arithmetic fixtures explicitly declare exact_unmodified; missing metadata is tested as unknown rather than silently treated as exact.
- pilot/PUBLIC_AGGREGATE_COLLABORATION_PROTOCOL.md and docs/MANAGER_PRODUCT_SPEC.md record the policy.

## 証拠レベル・限界

- Code and fictional fixtures: P0 engineering evidence only.
- No actual public aggregate values were ingested or compared in this task; no participant-level data, private records, partner system, credentials or accounts were accessed.
- The method label is an unverified source declaration. It does not authenticate the publisher, prove the actual protection method, or establish disclosure safety.
- No source retrieval, publication, contact, execution, clinical outcome, causal effect or human/animal suffering reduction is claimed.
- can_ingest, can_publish, can_execute, disclosure_certified, consent_or_ethics_approved remain false; beneficiary_effect=NOT_MEASURED; next_action=NO_ACTION.

## Remaining gates

D014 remains todo until the applicable ethics determination, partner cooperation, source rights and disclosure-approved public aggregates are available. H005 remains blocked because the original 2019 HeartSteps study-day/analytic exclusions cannot be reconstructed from the public release; no original paper number is fitted or imputed. F004/F007 remain blocked by third-party authority requirements.

**Product principle:** End suffering through lawful public non-personal macro-environment evidence. No human is required in the routine loop for a bounded, properly authorized action; this does not remove consent, rights, governance or independent safety review.


## Hosted verification (2026-11-03)

GitHub Actions workflow run #311 for commit 565187acd9146bc9696f4b0fe55a82f069d8d899 completed successfully:
https://github.com/Daisuke134/life-manager/actions/runs/41550440067

The Manager offline test job ran the canonical command, python -m unittest discover -s tests -v, from products/manager: **584 tests, 5 skipped, 0 failures**. The five skips are the existing optional pinned DoWhy dependency tests; they are not reported as completed tests. All seven newly added D014 disclosure-method regression methods appear as passing in the job log. The same run passed python -m manager_core and scripts/make_roadmap.py --check (113 tasks; task JSON untouched at that commit).

Earlier per-file commits in this sequence produced intermediate failing CI runs while code and test fixtures were being updated in separate commits. The completed tree at commit 565187a is the verified state; no intermediate run is presented as a successful final validation. The latest tasks.json update below is separately checked by its own subsequent workflow run.

This is hosted offline engineering verification only. The workflow did not authenticate a publisher, review a real aggregate release, activate a partner protocol, perform an intervention, or measure beneficiary effects.
