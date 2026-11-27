# ManagerBench

**One eval for behavior models.** ManagerBench scores models that claim to
predict — and change — human behavior, on one common case shape:

```
situation → stimulus → *measured* response
```

Ground truth is measured behavior (opened, continued, paid, rated,
returned), never impressions. Every arm — our model, frontier LLMs,
classical baselines, and a plain population prior — runs under the same
harness, the same frozen data, and the same scoring code. If a number
cannot be reproduced from the files in this repository, we do not publish
it as a result.

- **One model**: [Manager](../../models/manager/) — Anicca's behavior
  foundation model (in training).
- **One eval**: ManagerBench (this directory).
- **One product**: Anicca, whose deliveries and measured responses are
  the training data the model learns from.

## Surfaces

| Surface | What it measures | Harness |
|---|---|---|
| Behavior prediction | Predict a person's measured response (survey answers, personality scores, game/economic behavior) | Frozen MaMe-Re protocol + [BehaviorBench](https://github.com/umich-foreseer/behaviorbench_eval) (UMich Foreseer, adopted as-is) |
| Behavior intervention | Predict the *effect* of an intervention (uplift), and score intervention decisions | MG-06 uplift protocol ([`models/manager/v0/`](../../models/manager/v0/)) + intervention-case contract (below) |
| Comedy | Generate and judge humor (Ōgiri) on a 0–10 scale | In-house arm under eval-coach / Rubric discipline |

## Run it

Everything below runs offline, with no API keys, against the frozen
receipts shipped in this repository.

```bash
# 1. Replay the frozen benchmark aggregation (260 family/task/condition rows)
python3 files/eval/managerbench/run.py --root . \
  --output /tmp/managerbench-replay.json

# 2. Verify the replay reproduces the frozen baseline byte-for-byte
#    (exits non-zero with REPRODUCTION_CONDITION_DIFFERENCE on any drift)
python3 files/eval/managerbench/run.py --root . \
  --check files/eval/managerbench/baseline-2026-11-15.json

# 3. Run the integrity test suite (150 tests)
python3 -m unittest discover -s files/eval/managerbench -t files/eval/managerbench

# 4. Validate intervention cases against the v1 contract
python3 files/eval/managerbench/check_intervention_cases.py <cases.json>
```

The MG-06 uplift evaluation (prior / random / T-learner / base model /
Manager v0, Qini AUC with bootstrap CIs, scoring dtype pinned to fp32)
lives in [`models/manager/v0/eval_uplift.py`](../../models/manager/v0/eval_uplift.py);
see the [v0 write-up](../../models/manager/v0/README.md) for its exact
reproduction commands.

External frames we also run, unchanged, under their own licenses:
[BehaviorBench](https://arxiv.org/abs/2606.24162) (code MIT, data
CC BY-NC-ND 4.0) and the Centaur Psych-101 / Psych-201 frames. We
reference those datasets; we do not redistribute them.


## Unified capability release candidate (v0.2 scope, not a released version)

The existing offline replay remains the canonical aggregation. Its 260 rows
and 10 historical incomplete arms retain the frozen SHA-256
`688f0c564965c809cdc113d1cb61ca5ab553fb18d78f0f6980bb3b1bc44d3d42`.
The optional capability view does not replace it or define a global rank.

```bash
python3 files/eval/managerbench/run.py --root . \
  --check files/eval/managerbench/baseline-2026-11-15.json \
  --output /tmp/managerbench-replay.json \
  --capability-scorecard /tmp/managerbench-capabilities.json
python3 -m unittest discover -s files/eval/managerbench -t files/eval/managerbench
```

Optional flags `--gemma-receipt` and `--anomaly-receipt` accept the exact
published bytes pinned by [capability_scorecard.py](../../files/eval/managerbench/capability_scorecard.py).
Use the [Gemma release evaluation asset](https://github.com/Daisuke134/anicca/releases/download/manager-gemma4-e2b-hillstrom-2026-11-26/eval_adapter.json)
and [Run35 synthetic receipt at its pinned commit](https://github.com/Daisuke134/anicca-ops/blob/45e7efff65849f277ab62082a884936696755a44/files/research-artifacts/behavior-anomaly-2026-11-26/receipt.json).
They are references, not bundled external datasets. Absent optional receipts
are explicitly unmeasured. The Gemma BFM02 metrics are recomputed from the
24 recorded contexts; Hillstrom metrics are aggregate-only. Synthetic
defensive anomalies are not real-world security evidence.

### Release contract

* Each matched result identifies model and dataset revision, split and
  unit, prompt/scorer version, inference stack/settings, attempted/valid/
  invalid counts, source and checksum, and uncertainty where available.
  Missing metadata is null and disqualifies unsupported comparisons.
* BehaviorBench final-68 receipt coverage is 68/68, but explicit valid
  counts exist for 48/68 arms; 20 are unknown (18 game-distribution arms
  and 2 multiround arms). The known valid-count sum 33,018 is **not** the
  full valid count. The optional view audits this from pinned source bytes.
* No pooled cross-task accuracy, no unknown-to-zero conversion, no
  comparison across incompatible inference stacks or denominators.
* The candidate must preserve baseline bytes and pass tests in normal and
  optimized Python; verify artifact hashes, rights and CI before tagging.
  The complete unified release also needs the remaining external tracks,
  independent matched evaluations and explicit missing product evidence.
* Actual model promotion, measured human benefit, and app deployment
  require separate acceptance gates. See [product intake #9513](https://github.com/Daisuke134/anicca/issues/9513).
  This candidate is not a production or efficacy claim.

## Results

See [RESULTS.md](RESULTS.md). Headline, stated plainly: **our own model
does not win yet.** Manager v1 is an honest negative result, and Be.FM —
which we evaluate but do not ship — scores *below* a plain prior on the
frozen frame. We publish the losses with the wins because a benchmark
that only flatters its owner is not a benchmark.

## Known gaps (read this before citing our numbers)

1. **Real intervention cases: 0.** The Anicca app does not yet log, at
   each notification decision point, which words were chosen and with
   what probability (`delivery_id` + `assigned_probability`). Without
   that log, no real intervention case can enter ManagerBench and no
   uplift can be computed from product data. The contract
   ([`intervention-case-schema-v1.json`](../../files/eval/managerbench/intervention-case-schema-v1.json)),
   a reference converter and a validator are published
   ([`models/manager/v0/product/`](../../models/manager/v0/product/));
   the app-side implementation is tracked in
   [Daisuke134/anicca#9395](https://github.com/Daisuke134/anicca/issues/9395).
2. **The frozen v1 denominator is small** (18 non-tied cases; one case
   moves the score by 0.0556). A v2 expansion (50 contexts → ~200 cases)
   is planned and not yet measured. Treat v1 differences accordingly.
3. **Manager v0 shows no measurable uplift skill** (Qini CI crosses
   zero; see RESULTS.md). Manager v1 trails frontier models on
   intervention Brier and comedy. The current bottleneck is training
   data, not the harness.
4. **Be.FM weights are not redistributed** (rights unresolved), and
   Be.FM is not loaded in the product.

## Feedback

Issues and pull requests on this repository are the feedback channel.
Disagree with a number? The reproduction commands above are the fastest
way to prove us wrong, and we will update RESULTS.md when you do.

## License

Code and documentation in this directory and in `files/eval/`:
MIT (repository license). External benchmarks keep their own licenses
(BehaviorBench data: CC BY-NC-ND 4.0). Training-data terms for the
MG-06 frame are in
[`models/manager/v0/DATA_CARD.md`](../../models/manager/v0/DATA_CARD.md).

### Matched binary comparisons (HA06)
The optional Gemma pilot view now reports paired outcomes on all non-tied
BFM-02 cases. Its published receipt is pinned by SHA-256. The prior is a
deterministic baseline, not another identically configured model run.
`files/eval/managerbench/paired_binary.py` also exposes
`compare_matched_runs` for declared matching external model protocols:
dataset/split, manifest, evaluator, prompt and inference-protocol digests
must match, and all expected IDs must occur in both outcome maps.
Invalid and abstained answers count against strict accuracy. Exact two-sided
McNemar p-values assume independent pairs; do not interpret as clustered,
multiplicity-adjusted or causal evidence. Independent runner must verify
metadata and actual model checkpoint identities. No promotion from this view.

Mac M4 replay (2026-11-27): Gemma adapter vs prior on 16 non-tied cases,
10 vs 7 correct, 6 improvements and 3 regressions, exact p=.5078125.
This is historical receipt replay, not new inference, training or human benefit.
16/16 focused tests normal and optimized Python; frozen 260-row replay
and 10 incomplete arms unchanged.
