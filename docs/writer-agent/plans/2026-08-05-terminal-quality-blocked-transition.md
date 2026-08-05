# Terminal quality-blocked transition

## Goal

`done="a rerouted unpublished artifact whose editorial/reader evaluation budgets are structurally exhausted becomes a deterministic terminal rejection instead of evaluate_reroute or unclassified forever"`

## Contract

- Never fabricate editorial/reader PASS and never publish the rejected artifact.
- Require current JA/EN draft hashes, exact high-editorial exhaustion evidence, reader terminal attempt cap, no publication state, and no delivery ledger row.
- Bind the terminal receipt to the quality blocker, repair state, prior quality decision, and current drafts by SHA-256.
- A terminal receipt closes this run to further model spend. If the one same-day replacement budget remains, start control may create it; otherwise it records the daily quality miss without poisoning tomorrow.
- Model return code cannot make a valid no-publication terminal receipt unclassifiable.

## Adversarial evidence

A fresh GPT adversarial reviewer rejected advisory publication because the live FAILs include unsupported quantitative and Unicode claims. It confirmed that another repair attempt cannot create a current editorial receipt: a prior high FAIL plus changed bytes exits 77 before a provider call.
