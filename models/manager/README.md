# Manager — a behavior foundation model (in training)

Manager is Anicca's model of human state transitions: given a person's
history and a candidate intervention (a notification, a message, a piece
of content), it predicts how that person's state and behavior change —
so the intervention that actually helps can be chosen, delivered,
measured, and learned from. The loop is: **predict → choose → deliver →
measure → learn**.

- **One model**: Manager.
- **One eval**: ManagerBench — cases in one common shape
  (situation → stimulus → *measured* response), scored by whether the
  model's ranking of interventions beats simple priors under the same
  harness. Ground truth is measured behavior (opened, continued, paid,
  rated, returned), never impressions.
- **One product**: Anicca, whose deliveries and measured responses are
  the training data this model learns from.

## Status

- **v0 (2026-11-14)** — the first post-training run that actually
  executes end to end: a small open-weight model post-trained on
  randomized intervention data (Hillstrom), scored with the MG-06
  uplift protocol against prior / random / classical baselines, and a
  product-side case format that lets Anicca deliveries flow into the
  same eval and training shape. See [`v0/`](v0/README.md).
- **v1 (2026-11-17)** — measured on ManagerBench's first same-conditions
  run. An honest negative result: intervention-prediction Brier 0.3827
  (prior 0.3869, best frontier model 0.3547) and comedy 1.92 / 10. The
  bottleneck is training data, not the harness. Full tables:
  [`benchmarks/managerbench/RESULTS.md`](../../benchmarks/managerbench/RESULTS.md).
- **ManagerBench (2026-11-25)** — the benchmark is now public in this
  repository: frozen harness, receipts, integrity tests and results,
  runnable offline. See [`benchmarks/managerbench/`](../../benchmarks/managerbench/).

## Feedback welcome

We publish available code, data cards and results, and intend to release cleared weights, so that
people who know more than us can tell us what is wrong. Issues and pull
requests on this repository are the feedback channel; every result file
ships with the exact commands needed to reproduce its numbers.

## License

Code and documentation in this directory: MIT (repository license).
Model weights derived from `HuggingFaceTB/SmolLM2-135M-Instruct`
(Apache-2.0) are intended for release under Apache-2.0, subject to training-data terms and verified artifact availability. Training data terms are in
`v0/DATA_CARD.md`. Be.FM weights are **not** redistributed or loaded
commercially anywhere in this project (rights not yet clear).

## Research release status (2026-11-25)

Manager is an experimental behavior model; ManagerBench is its evaluation program. GitHub entry points:

- [Manager v0 reproduction instructions](v0/README.md), [model card](v0/MODEL_CARD.md), and [data card](v0/DATA_CARD.md).
- [ManagerBench evaluation code](../../products/manager/evals/managerbench_v1.py) and [four-track aggregate evidence](../../docs/research/manager/verification/MANAGERBENCH_V1_FOUR_REAL_TRACKS_20261107.json). The latter is an aggregate evidence replay, not a leaderboard of fresh model inference.
- [Research articles](https://aniccaai.com/blog/c/research).

Manager v0 is a 135M research baseline, not a production intervention policy. On the preregistered 1,000-case Hillstrom evaluation, Qini was 0.0041 for v0 versus 0.1017 for the logistic T-learner; v0 failed its promotion gate. Do not deploy it to choose interventions. The full frozen training split and the subsample used for optimization are distinct. No claim of real-user benefit follows from these results.

**Hugging Face status:** anonymous Hub API check on November 25 found no public models under `anicca-agent`; `anicca-agent/manager-v0` returned HTTP 401. The public [BehaviorBench pilot aggregate results](https://huggingface.co/datasets/anicca-agent/behaviorbench-first-run-results) are a separate artifact, not the ManagerBench dataset. Public Manager weights and a ManagerBench Hub dataset are unverified. Publish only cleared artifacts, with version/hash, model and dataset cards, reproducible commands, failed results, and independently readable public URLs. Do not redistribute restricted third-party source records or serialized derivatives without permission.

Our planned comparison separates observed individual response prediction, population fidelity, and causal intervention ranking; compare only matched cases, protocols and baselines. Chiron (Ye et al., arXiv:2611.24830) is a reference for joint psychological measurement, prediction, and population alignment. No Chiron end-to-end comparison has yet been completed by Anicca. Psychological scores are uncertain research outputs, not diagnoses or a basis for manipulating users.
