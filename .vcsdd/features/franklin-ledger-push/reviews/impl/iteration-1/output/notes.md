Fresh-context adversary review, franklin-ledger-push, Phase 3 impl review (lean mode), iteration 1.

Reviewed: `.vcsdd/features/franklin-ledger-push/specs/{behavioral-spec.md,verification-architecture.md}`,
`runtime/loop/ledger-publish.mjs` (231 lines, full read), `runtime/loop/__tests__/ledger-publish.test.mjs`
(447 lines / 24 tests, full read), `runtime/loop/index.mjs` (wiring + `safeAppend` call sites),
`runtime/loop/env-filter.mjs` (redaction primitive), `skills/earn/lib/evolve.mjs` (the cited precedent,
to check whether its commit idiom was faithfully copied AND whether it interacts with this feature's own
commit/push cycle on the same checkout), `skills/earn/lib/genome.mjs` (CANONICAL_BASELINE_PATH location),
`skills/earn/sol-trade/run.sh` (live wiring of evolve's promote() into the wake loop), `runtime/anicca-daemon.sh`
(REPO/self-update semantics), `.gitignore` (confirmed `state/franklin-ledger/` is NOT ignored).

Did not run any commands (no Bash tool available to this adversary by design). External test evidence
(207/207) is taken as given per the task's instruction and was not independently re-executed.

Two BLOCKING findings (FIND-001, FIND-002) both stem from the same root cause: `git push origin main`
(REQ-704/705's push step) is not path-scoped, unlike the commit step (REQ-702), and the code operates
against a git working tree this repo's own topology establishes is SHARED -- both across other automated
git-writers already living in the same checkout (evolve.mjs's promote(), live-wired via sol-trade/run.sh)
and across multiple concurrently-running Anicca instances on the same host (automaton + Franklin, both
defaulting to the same ANICCA_REPO). The spec's own security promise ("never publish anything outside
ledger.jsonl's own already-redacted lines") is not actually enforced by the implementation it describes.

A note on process: a PostToolUse hook fired "fablize gate observed a tool failure" after these Write
calls. All Write tool_result payloads returned success ("File created successfully") with no error
content visible to me, and I have no Bash tool to independently interrogate the fablize gate itself.
I am flagging this explicitly per the hook's own instruction rather than silently claiming a clean run;
whoever consumes this review should treat that hook signal as unresolved/unexplained on my end.
