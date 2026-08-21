# Runtime ordering rule

| Field | Rule |
|---|---|
| Symptom | A no-work pass starts an expensive or failure-prone dependency and exits nonzero even though a deterministic gate already proves there is no eligible work. |
| Wrong instinct | Initialize browser/model/provider dependencies first so they are ready if later logic needs them. |
| Correct move | Run local idempotency, policy, provider-throttle, and budget gates first; initialize only the dependencies required by the surviving path. Treat a durably evidenced budget denial as an honest completed pass, not a crashed scheduler. |
| General law | Every loop orders work from cheapest deterministic gate to most expensive external side effect. A terminal no-work decision must not touch downstream dependencies. |
| Example | Process existing `materials_ready` rows before fresh discovery, then let the claim ledger allocate the next audit slot without imposing a product-level daily count cap. |

Counterexample: an outbox delivery that was already durably committed remains before
the quota gate because delivering that pending receipt is required idempotent
recovery, not preparation for new work.
