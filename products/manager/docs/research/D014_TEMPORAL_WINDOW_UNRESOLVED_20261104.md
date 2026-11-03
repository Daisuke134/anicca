# D014 — Unknown temporal-window semantics must remain explicit (2026-11-04 JST)

**Scope:** one P0 offline metadata-only safety increment. The canonical task registry remains `products/manager/docs/roadmap/tasks.json`; D014 remains `todo`. No external partner, ethics determination, data ingestion, publication, intervention, or welfare outcome is claimed.

## Question → hypothesis → falsification (imozuru)

**Question:** When two aggregate releases have the same declared population description, unit, geography, outcome and route but different time-window labels, what should the preflight report if one or both windows cannot be parsed as the supported ISO date interval?

**Unsafe hypothesis H0:** If a window label is opaque or malformed, the system can treat the pair as not overlapping because its date parser returns false.

**Counterexample:** Compare a synthetic release labelled `monthly publication; dates unavailable` with another labelled `quarterly release Q1`. Both may refer to intervals that overlap, but neither label gives enough machine-readable information to prove overlap or disjointness. Returning only the generic scope mismatch hides the specific temporal uncertainty from downstream review.

**Narrow safe rule H1:** For otherwise aligned temporal scope, classify distinct windows as:
- `overlap` only when both are valid inclusive `YYYY-MM-DD/YYYY-MM-DD` ranges and the ranges intersect;
- `disjoint` only when both are valid ranges and the ranges do not intersect;
- `unknown` when either label is malformed, opaque, reversed, or unsupported.

An unknown relation adds `CROSS_RELEASE_TEMPORAL_WINDOW_UNRESOLVED`; the family aggregator propagates `FAMILY_TEMPORAL_WINDOW_UNRESOLVED`. It remains `REVIEW_REQUIRED` / `NO_ACTION`. No counts are subtracted, no cohort identity is inferred, and no release is certified.

## Primary sources

1. UK Government Analysis Function, **Statistical Disclosure Control for tables produced from administrative data**, published 19 August 2026: https://analysisfunction.civilservice.gov.uk/policy-store/sdc-for-tables-produced-from-administrative-data/ . The guidance describes the mosaic/jigsaw effect and multiple releases from a similar collection over time, including successive months or quarters where small changes can expose people. It also says linked tables may disclose by differencing and combining data. This supports treating uncertain release periods as unresolved, not as proven disjoint. (See “Mosaic, or jigsaw effect” and “Assessing the disclosure risk”.)

2. UK Government Analysis Function, **Statistical Disclosure Control for tables produced from surveys**, published 19 August 2026: https://analysisfunction.civilservice.gov.uk/policy-store/statistical-disclosure-control-for-tables-produced-from-surveys/ . The guidance defines differencing as comparing two or more tables and says groups of publicly released tables should be checked for disclosure by differencing. It also notes that weighted estimates have different uncertainty properties; this implementation does not infer any such protection from an opaque window label.

3. Office for National Statistics, **Policy on protecting confidentiality in tables of birth and death statistics**, section R5: https://www.ons.gov.uk/methodology/methodologytopicsandstatisticalconcepts/disclosurecontrol/policyonprotectingconfidentialityintablesofbirthanddeathstatistics . It describes geographical, linked-table and sub-population differencing, including how overlapping periods and tables can expose previously unpublished small cells.

These are official methodological sources, not evidence that any particular Manager input is disclosive. The implementation is a conservative review signal, not an ONS-approved SDC method.

## Implementation

- `manager_core/public_aggregate_cross_release.py`: parse supported ISO date windows into a three-way relation (`overlap`, `disjoint`, `unknown`). Preserve the existing boolean helper for its narrow overlap meaning. When the other scope dimensions align and distinct time labels are not both parseable, emit `CROSS_RELEASE_TEMPORAL_WINDOW_UNRESOLVED`.
- `manager_core/public_aggregate_release_family.py`: propagate the pair-level uncertainty as `FAMILY_TEMPORAL_WINDOW_UNRESOLVED`.
- `tests/test_public_aggregate_cross_release.py`: synthetic cases for overlapping, inclusive-boundary, disjoint, invalid calendar date, reversed interval, opaque labels and mixed valid/opaque labels.
- `tests/test_public_aggregate_release_family.py`: ensure unresolved temporal semantics propagate across a 3-release family without arithmetic or disclosure certification.

The result remains metadata-only. No participant-level rows, public statistics, publisher credentials, network requests, or private records are accessed.

## Verification boundary

A separate local 8-case logic check passed for the new three-way relation. This is not a substitute for the repository's Python unittest suite or hosted CI. The final hosted CI result for this commit must be checked before calling the change CI-verified.

The check does not establish that two releases actually share records, that their declared population labels are true, that their source bytes or publisher are authentic, or that disclosure has occurred. It does not calculate a difference or reveal a suppressed count. Real disclosure review remains the responsibility of a qualified data publisher under the applicable law, consent and institutional process.

**Research vs simulation vs field effect:** this is a software rule tested with synthetic metadata (P0). No empirical study result, real-world intervention, downstream benefit, income change, or reduction in human/animal suffering is measured.

**Safety:** no human/animal participant data, personal data, external messages, payment, physical actuation, or Life Manager runtime/main files were touched. H005 remains blocked; no HeartSteps study-day values or original paper numbers were imputed.


## Hosted CI readback (2026-11-04 JST)

The final roadmap commit `d9c52c1ab62dc307a6fba2fa57c6a2ef63a3afd8` triggered three hosted workflows on the requested research branch:

- **Manager Independent Offline Research #322 — success:** https://github.com/Daisuke134/life-manager/actions/runs/41740549152 . Its job log reports `Ran 585 tests`, `OK (skipped=5)`, the new `test_unknown_temporal_window_propagates_as_unresolved_review` passed, the Life Manager import boundary passed, and `PASS 113 tasks; task JSON untouched`.
- **Manager EBA v0 Open Benchmark #91 — success:** https://github.com/Daisuke134/life-manager/actions/runs/41740548982 . Its two jobs succeeded; the offline benchmark also reports 585 tests and 5 skips. EBA values are synthetic-only.
- **Manager Phase06 Digital Environment #228 — failure:** https://github.com/Daisuke134/life-manager/actions/runs/41740549132 . Its Manager unit contracts, boundaries, registry check and service bundle build succeeded. It failed later while installing Playwright 1.56.1 browser dependencies because the hosted runner resolved to `ubuntu26.04-x64`, which that Playwright version does not support. Browser/live verification steps were skipped. This is an environment/toolchain blocker, not evidence of a failure in the D014 unit tests; nevertheless the overall Phase06 workflow is not green.

The offline code/test validation is therefore green, EBA is green, and Phase06 remains red for an upstream runner/browser compatibility reason. No workflow establishes an actual disclosure event, partner collaboration, public outcome, intervention or beneficiary improvement.
