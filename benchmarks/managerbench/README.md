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
