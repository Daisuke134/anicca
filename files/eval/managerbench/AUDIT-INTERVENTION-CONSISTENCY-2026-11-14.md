# ManagerBench intervention-case consistency audit — Issue #105
**Owner:** ChatGPT · **Source date:** 2026-11-14 JST · **Status:** offline software consistency check (NOT human efficacy)

## Why this exists
The canonical [intervention-case-schema-v1.json](intervention-case-schema-v1.json) records randomized decision points, but allows `proximal_outcome: null` and does not require `outcome_observed`. The existing [check_intervention_cases.py](check_intervention_cases.py) intentionally performs **minimum counting**, including returning zero for unrelated manifests. It does not establish that input decision points are internally consistent, that assignment was properly randomized, or that real human benefit was measured.

Our verified starting point is **0 actual ManagerBench intervention cases**, as recorded in `files/eval/managerbench/README.md` and `files/eval-benchmark-field-census-2026-11-14.md`. Synthetic passing cases in the tests MUST NOT be inserted into the canonical intervention dataset or claimed to resolve this gap.

## Primary prior art
- MRT design and conditional availability: [Klasnja et al., Microrandomized trials](https://pmc.ncbi.nlm.nih.gov/articles/PMC4732571/).
- Observed vs missing proximal outcomes: [Missing data in MRTs](https://pmc.ncbi.nlm.nih.gov/articles/PMC12618347/).
- Reviewable deterministic outcome graders, balanced positive/negative cases, and regression evals: [Anthropic, Demystifying evals for AI agents (2026)](https://www.anthropic.com/research/demystifying-evals-for-ai-agents).
- Reuse of the existing canonical v1 required fields: `check_intervention_cases.REQUIRED` / `validate`.

## Interface and strict profile
The **additive** script is `audit_intervention_cases.py`. The original schema, source data, frozen ManagerBench score baseline, MG-06 preregistered uplift results, and product notification code are **unchanged**. This script:
1. Accepts a JSON **list of decision points** or `{"cases": [...]}`; unrelated manifests fail closed instead of reporting a false clean bill of health. Explicit empty lists yield zero counts.
2. Reuses the original v1 field requirements and base checker. Strictly requires a boolean `outcome_observed` while remaining a **separate opt-in audit profile** (not claiming this is required in frozen schema v1).
3. Requires nonblank case/person IDs; no duplicate case IDs across input files; finite propensity strictly between 0 and 1; positive integer outcome window; timezone-aware ISO-8601 decision time.
4. Requires boolean availability/treatment/outcome-observed flags. A decision marked `available:false` may not also have `treatment_assigned:true`. Treated cases require nonblank intervention and delivery IDs.
5. If an outcome is observed, `proximal_outcome` must be a finite number or boolean. If not observed, it must be `null`. An optional `outcome_observed_at` must have timezone and may not precede the decision; **late recording is allowed**. No invented event time is inferred.
6. Aggregates `validated_decisions`, `available_randomized_decisions`, `unavailable_decisions`, `treated_available_decisions`, `observed_outcomes`, `missing_outcomes`, `distinct_person_ids`. These are **counts, not causal effects**.
7. Never reports raw participant IDs, histories or stimulus content to stdout or error messages. Invalid input/JSON/file is a nonzero exit.
8. `--require-min N` is an *optional case-count gate*, not a model-efficacy gate. The default minimum is zero to support accurate empty-data audits. Output uses `PASS_ZERO_CASES` for an explicit empty list, `PASS_CONSISTENCY_ONLY` for nonempty valid logs, and `FAIL_UNDER_MINIMUM` when the case-count gate fails; none is a causal-effect claim.

## Reproduce: no network, no extra packages
From repo root:
```bash
python3 -m unittest -v files/eval/managerbench/test_audit_intervention_cases.py
python3 files/eval/managerbench/audit_intervention_cases.py \
  /path/to/authorized-intervention-cases.json --require-min 0
```
All shipped tests use self-authored fictional records, not real participant rows. For an explicit empty JSON array `[]`, the output must show **0 validated decisions**, and `--require-min 1` must fail. Existing original `check_intervention_cases.py` is still the compatibility counting gate.

## This audit does NOT prove
- A human was actually available or randomized at the recorded probability.
- An intervention was delivered, viewed or voluntarily received.
- Missingness was random or correctly attributed.
- Proximal outcomes are measured by independent instrumentation.
- Uplift, WCLS/MRT, an individual's counterfactual, or decreased suffering.
- Data rights, informed consent, clinical safety, or commercial permissions.

Next scientific step is **legitimately collect and verify real decision-point data under MG-06 owner**, then apply appropriate MRT/WCLS analysis. Do not silently upgrade `0` to a successful causal effect.
