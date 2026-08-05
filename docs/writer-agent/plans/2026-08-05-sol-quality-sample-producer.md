# Sol quality-sample receipt producer

## Goal

`done="the first 30 distinct review-eligible runs deterministically produce exactly six quality_sample receipts, alternately JA/EN, and only those receipts can cross the existing one-use Sol boundary"`

## Contract

- Count the first observation of each distinct `run_id`; retries never advance the ordinal.
- Sample ordinals `5, 10, 15, 20, 25, 30` only.
- Expected languages are `ja, en, ja, en, ja, en` in ordinal order.
- A sampled ordinal presented with the wrong language remains pending for that same run; it does not spend or transfer the sample slot.
- Receipt fields exactly match the fail-closed model-runner contract: schema version, trigger, run, artifact, article hash, and medium effort.
- State and receipt writes are lock-protected, atomic, replay-safe, and recoverable after interruption.
- Ordinals above 30 create no calibration receipt unless a later receipted strategy changes the contract.

## TDD slices

1. RED: ordinary runs produce no receipt; six exact ordinals do; retries remain idempotent; wrong language cannot consume a slot.
2. GREEN: implement a deterministic Python control with an exclusive state lock and atomic JSON writes.
3. Boundary: feed one produced receipt to the model runner and prove Sol is selected once; prove an ordinary run has no usable receipt.
4. Regression: run focused Writer tests and compare the full repository failure set with the measured baseline.
5. Promotion: push the feature commit, cherry-pick it into the live checkout, rerun focused contracts there, then record exact receipts in the Writer SSOT.
