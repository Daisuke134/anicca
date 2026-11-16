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

**The current serving Manager is the population prior.** It remains the
chooser until the v1 handoff lands and the serving integration is switched
explicitly. The prior arm is implemented in
[`v0/eval_uplift.py`](v0/eval_uplift.py) as a constant uplift score
(`np.zeros`); it provides no personalized ranking. This is the current
model designation, not evidence that iOS notifications already call it.
No runtime model selector for these checkpoints exists under
`models/manager/`; the intervention spec records that app delivery still
uses catalog/rule logic. That product wiring is a separate integration.

**v1 (2026-11-16)** starts immediately under the founder decision. The
MG-06 pre-training prerequisite was withdrawn. Historical confidence-interval
checks are retained as diagnostics, not permission to start training. See
[`v1/`](v1/README.md) for measured training/evaluation and handoff status.

- **v0 (2026-11-14)** — the first post-training run that actually
  executes end to end: a small open-weight model post-trained on
  randomized intervention data (Hillstrom), scored with the MG-06
  uplift protocol against prior / random / classical baselines, and a
  product-side case format that lets Anicca deliveries flow into the
  same eval and training shape. See [`v0/`](v0/README.md).

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
