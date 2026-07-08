# Proof harnesses — anicca-agent-lending Phase 5

- **Tier-1 property-based tests** (`fast-check`, 10 tests) live alongside the existing suite in
  `~/anicca/skills/economy/lending/lib/__tests__/lending-gate.property.test.mjs` — NOT copied into this
  directory, since this feature's existing test convention already keeps all tests colocated under
  `~/anicca/skills/economy/lending/lib/__tests__/`, and duplicating the file here would create two
  divergent copies over time. Run with `cd ~/anicca && node --test
  skills/economy/lending/lib/__tests__/lending-gate.property.test.mjs`.
- **Tier-3 live E2E harness** for PROP-025/PROP-108a: `prop-108a-live-mainnet-e2e.mjs` (this directory) +
  its captured `prop-108a-live-mainnet-e2e.output.log`. This one DOES live here (not in `~/anicca`)
  since it is a one-shot verification script, not part of the feature's own ongoing test suite.
- **Sprint-2 orchestrator residual-obligation harness**: `sprint2-orchestrator-residual-props.mjs` (this
  directory) + its captured `sprint2-orchestrator-residual-props.output.log`. Closes the 12 (of 19)
  sprint-2-targeted proof obligations that `~/anicca/skills/economy/lending/lib/__tests__/
  lending-orchestrator.test.mjs`'s own 30 pre-existing tests did not yet directly cover (see
  `verification/verification-report.md`'s own Sprint-2 Addendum for the full per-obligation citation).
  13 scenarios, each driving the REAL, unmodified `executeLoanIssuanceAttempt`/`executeRepaymentClaim`
  from `lending-orchestrator.mjs` via its own already-designed `deps` injection seam — never a
  re-implementation or mock of the orchestrator itself. Lives here (not in `~/anicca`) for the same
  reason as the Tier-3 harness above: a one-shot Phase-5 verification script, not part of the feature's
  own ongoing test suite (which remains exclusively `lending-orchestrator.test.mjs` in `~/anicca`). Run
  with `cd ~/anicca && node
  /Users/anicca/anicca-project/.vcsdd/features/anicca-agent-lending/verification/proof-harnesses/sprint2-orchestrator-residual-props.mjs`.
