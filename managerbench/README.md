# ManagerBench

An open research package for evaluating behavior-intervention systems: historical behavioral prediction receipts, and a small reproducible synthetic restraint suite.

**Real intervention cases = 0.** This release does not establish that any model changes human behavior or improves wellbeing. It contains no raw intervention records, individual human labels, or personal me-data.

## What is actually published

| Asset | Size | Meaning |
|---|---:|---|
| [Runnable restraint cases](cases.json) | 10 | Existing generic synthetic situations, reused unchanged |
| [Earlier frozen ledger](baseline/baseline-2026-11-14.json) | 192 rows | Aggregated evaluation receipts, **not 192 input cases** |
| [Latest frozen baseline](baseline/baseline-2026-11-15.json) | 260 rows + 10 incomplete records | Historical scores and provenance, not runnable third-party datasets |
| Real intervention cases | **0** | No measured intervention-to-response cases in this release |

The 260-row snapshot extends the earlier 192-row snapshot. Counts are verified from actual JSON rather than the older dataset-card wording. Missing metadata remains null; restricted underlying datasets are not redistributed. [Manifest and source hashes](manifest.json).

## Run the published suite

Python 3.9+; only the primary scoring harness is a dependency:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r managerbench/requirements.txt
(cd managerbench && python -m unittest test_compare -v)
# Set OPENROUTER_API_KEY securely in your local environment; never commit it.
python managerbench/compare.py --output managerbench-run
```

[Rubric / rubric-eval](https://github.com/Kareem-Rashed/rubric-eval) **0.2.0 is the primary harness**, using TestCase and ExactMatch for deterministic action grading. [compare.py](compare.py) supplies only OpenRouter transport, strict output validation, and checkpoint receipts. No LLM judge or paid grader. [promptfoo](SECONDARY.md) is secondary for optional declarative regression and is not used to claim primary scores. No new tool-use/trace benchmark is claimed: these are single-turn action choices without tool calls.

[models.json](models.json) pins the nine exact OpenRouter model IDs and catalog metadata resolved for this comparison. Latest Claude resolves to **anthropic/claude-fable-5.2**. Each model receives every one of the same ten inputs, the same system prompt, no tools or history, one independent request per case, **max_tokens=2000**, and no automatic retries or fallbacks. Temperature/seed/reasoning settings are omitted for every model because parameter support differs; provider defaults may differ. Shared visible output budget does not imply equal internal reasoning compute. A prepaid dedicated key is capped at $5 for the launch run; no billing/reload endpoint is called. Running the command uses your own API credits.

Every receipt records the source Git commit, cases hash, complete synthetic prompt/response, reported model/provider, generation ID, usage/cost, finish reason and latency. Re-running the same output directory skips completed cases. An outstanding `.intent` file fences an uncertain request: reconcile it against provider records before any retry. A paid call is never silently replayed.

## Metric and its limits

The existing restraint-v1 manifest labels **all ten cases `pass`** (do not send). Rubric exact action accuracy is a synthetic decision-agreement score. **Always-pass scores 10/10 by construction.** This suite is a basic regression/smoke test, not a discriminating general model ranking. It has no positive-intervention cases and does not establish human behavioral calibration or comedy quality.

Strict JSON is required: exactly `id`, `action`, and `p_intervene`, matching the input ID, action `pass` or `intervene`, and a finite numeric probability in [0,1] that sending now is appropriate. Synthetic Brier is mean((p_intervene − 0)²); a full-frame score requires ten valid outputs. Report valid-only descriptive loss separately if incomplete. Always-pass with p=0 has Brier 0. Blank output, malformed/duplicate-key JSON, truncation, or transport errors remain explicit statuses. Reports show valid coverage and correct/all-10 separately; missing outputs are not assigned invented human outcome scores. `observed_value`, `observed_unwanted_intervention_cost` and `observed_causal_effect` remain null. API dollar cost is a separate measured quantity.

## Historical results — separate conditions

The frozen baseline is **offline_receipt_replay**, not a new inference run. Its actual row families are moblab (194), big_five (37), humor (14), economics (8), and demographic (7); the source card describes more families than the delivered snapshot actually contains. Its tasks, arms, denominators and conditions differ; do not average the 260 rows into a leaderboard or compare them to ten-case restraint accuracy. Each row retains its own `family`, `condition`, `task`, `arm`, `n`, metrics and source.

Selected actual rows from the frozen JSON (different tasks/conditions, **not a ranking**):

| Family / condition / task | Arm | Metric | Recorded value |
|---|---|---|---:|
| humor / v1-actions-24 / pair_choice | befm15-4b | strict_accuracy (18 non-tied of 24) | 0.5555556 |
| demographic / behaviorbench-final / demo_pred_age | befm15-4b | MAE (n=1000) | 9.102 |
| economics / behaviorbench-final / ieo_economics | befm15-4b | accuracy_multi_choice (n=124) | 0.5 |

Manager v0's supplied [historical model card](baseline/manager-v0-model-card.md) reports MG-06 Qini 0.0041 versus T-learner 0.1017 and a **failed promotion gate** (lower CI −0.0839 versus random p95 0.0715). These are historical card claims, not this comparison's results. The card still contains a placeholder `ANICCA/manager-v0` namespace; no actual runnable pinned checkpoint is supplied by this package. **Manager v0 is unmeasured in the new comparison**, not zero and not the population prior.

A separate internal notification wording evaluation recorded 26/32 contract-valid generations and 20/103 unacceptable potentially sendable texts, with 0 real intervention cases. It used Pollinations-reported gpt-oss-20b and max_tokens=700, so it is context for limitations, not a same-condition result. The private report and its synthetic profiles are not copied into the public package.

## How cases will be added

Keep this suite frozen and version future additions. Add only permission-cleared synthetic/derived cases with source, license, expected behavior and scorer. Balance send/no-send cases before using the suite for model selection. Real randomized decision points require actual assignment probability, availability, pre-assignment context, delivery receipt and a prespecified observed outcome window. Raw records stay private; publication needs rights/privacy review and a separate de-identified/aggregate release. Until those exist, the real intervention count remains **0**. Missing outcomes are never inferred from a model answer.

## Provenance, presentation and licensing

- Reuses `anicca-ops/files/eval/restraint/cases-v1.json` byte-for-byte; no 192-case dataset is invented from the receipt ledger.
- The pre-existing receipt aggregation's card declares CC BY 4.0 for aggregation only. Underlying BehaviorBench data is CC BY-NC-ND 4.0, Be.FM is research-evaluation-only, and the original harness uses only the CC BY 4.0 MaMe-Re columns. Their raw inputs/labels are **not included** and retain their own rights. Code and our synthetic situations follow the repository [license](../LICENSE); the historical model card retains its Apache-2.0 declaration for the model, not third-party data.
- Presentation follows [Andon Labs Vending-Bench 2](https://andonlabs.com/evals/vending-bench-2): define the task, show a readable results table, state conditions. It does not claim their scale or methodology.
- Follows [Horizon Labs](https://horizon-labs.ai) and its [public repository](https://github.com/horizon-ai-labs/agent-io-guards): quick start, provenance, reproducibility, negative results and limitations alongside the results. No endorsement implied.
- [Launch specification and ordered status](SPEC.md). Comparison receipts/results are added after the public commit is verified; no placeholder results are presented as measurements.

## Preregistered comparison frame (#301 / #302)
Every model receives ALL ten publishable cases in cases.json, in its fixed order. This is a census of this small synthetic frame; no random sampling or seed applies. The private result file freezes IDs and SHA256 before inference. No inference applies to other cases or human populations. The older models/manager/api/bench/run_bench.py first-four-positive / first-four-negative selection from 12,808 held-out people is a known outcome-conditioned non-probability sampling defect; this package never calls that runner or loads that data. Its historical Brier must not be presented as population performance.
