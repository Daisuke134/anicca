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
