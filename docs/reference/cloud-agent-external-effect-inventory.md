# Cloud-agent external-effect inventory

This TODO #4 inventory separates reusable effect objects from opaque loop-to-effect edges. It is revision-bound to the ordered 334-row parent loop inventory and covers exactly five required categories for every loop: `call`, `post`, `mail`, `render`, and `wallet`.

The tracked inventory contains 1,670 category-coverage edges plus seven evidence-backed bindings, for 1,677 edges and 12 reusable objects. Coverage resolution is one of `discovered`, `none`, or `unverified`; absence of evidence remains `unverified`. Targets are classes, never recipient identifiers, account handles, phone numbers, wallet addresses, provider payloads, prompt bodies, or message bodies.

## Evidence-backed effects

| Category | Object behavior | Binding status | Policy |
|---|---|---|---|
| call | configured guidance voice call | one opaque loop | allowed classification |
| post | managed social carousel publish | one shared object, two opaque loops | allowed classification |
| post | Zenn retry source-control publish | one opaque loop | allowed classification |
| post | Orca finalizer source-control publish | one opaque loop | allowed classification |
| mail | subscribed-recipient newsletter send | one opaque loop | allowed classification |
| render | generated vertical-media render | one opaque loop | allowed classification |
| wallet | on-chain stake mutation | catalog-only, no loop binding | blocked |

The wallet entry proves that mutation behavior exists in a reviewed source. It does not prove a parent-loop mapping and therefore remains unbound. Wallet mutation cannot be marked allowed by the validator.

The Zenn retry worker and Orca finalizer are bound only to their reviewed, revision-pinned `git push` mutations. The new article D7D8 finalizer and HF gig-pass loop have no verified external mutation binding; all five category-coverage rows for each remain `unverified`. Internal state or artifact writes remain part of TODO #3 and are not counted here.

## Review boundary

`cloud-agent-external-effect-discovery-manifest.json` is the builder-authored manifest and remains `review_required / pending_independent_external_effect_review`. `cloud-agent-external-effect-discovery-review.json` is the separate approved artifact with exact basis `todo4_independent_candidate_review_approved_v1` and reviewer role `independent_fresh_sol_review`. The review binds manifest digest `sha256:f4b4a382:b31cd39e:6a1a2b80:8512af15:56bcbf59:617ec6f5:3a470241:9631dbf7`, the current parent digest, and the exact seven source revisions. Normal mode accepts only this coherent tuple. An approved review with a pending basis, placeholder reviewer role, stale parent, stale manifest, or stale source revision fails closed.

Approved regeneration:

```sh
python3 scripts/collect-cloud-agent-external-effect-metadata.py
python3 scripts/generate-cloud-agent-external-effect-inventory.py
```

Synthetic pending reviews remain candidate-only: normal mode exits nonzero without stdout or output, while explicit `--candidate` produces isolated `candidate_pending_review` artifacts. Approval validates this metadata inventory; it does not authorize execution of any listed effect.
