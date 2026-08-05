# Runtime ordering rule

| Field | Rule |
|---|---|
| Symptom | A no-work pass starts an expensive or failure-prone dependency and exits nonzero even though a deterministic gate already proves there is no eligible work. |
| Wrong instinct | Initialize browser/model/provider dependencies first so they are ready if later logic needs them. |
| Correct move | Run local idempotency, quota, policy, and budget gates first; initialize only the dependencies required by the surviving path. Treat a durably evidenced budget denial as an honest completed pass, not a crashed scheduler. |
| General law | Every loop orders work from cheapest deterministic gate to most expensive external side effect. A terminal no-work decision must not touch downstream dependencies. |
| Example | When two daily application slots are already consumed, write `daily_quota_reached` and exit zero before checking Chrome CDP or invoking a model. |

Counterexample: an outbox delivery that was already durably committed remains before
the quota gate because delivering that pending receipt is required idempotent
recovery, not preparation for new work.

## Private-profile boundary

| Field | Rule |
|---|---|
| Symptom | A model or shell command renders private profile values into a provider transcript while preparing a browser form. |
| Wrong instinct | Read the profile through a general-purpose shell command because the next browser action needs one field. |
| Correct move | Load private values only inside non-logging automation code and pass them directly to browser `fill()` calls. Scan every provider stdout transcript before accepting the run as successful. |
| General law | A private input may cross only into the exact side-effect sink that needs it; intermediate prompts, stdout, snapshots, receipts, and reports are fail-closed boundaries. |
| Example | The application email moves from the mode-0600 profile parser directly to an email input; a transcript match records only the leaked field name and forces a nonzero run result. |

Counterexample: a public job title or official posting URL may appear in evidence
because it is application provenance rather than a private profile value.
