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

We publish code, data cards, weights and results specifically so that
people who know more than us can tell us what is wrong. Issues and pull
requests on this repository are the feedback channel; every result file
ships with the exact commands needed to reproduce its numbers.

## License

Code and documentation in this directory: MIT (repository license).
Model weights derived from `HuggingFaceTB/SmolLM2-135M-Instruct`
(Apache-2.0) are published under Apache-2.0. Training data terms are in
`v0/DATA_CARD.md`. Be.FM weights are **not** redistributed or loaded
commercially anywhere in this project (rights not yet clear).
