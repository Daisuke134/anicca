# Mutation testing — anicca-agent-lending Phase 5

Not run this session. Stryker Mutator's JS/TS runner integrates with vitest/Jest/Mocha test runners, not
plain `node:test` — installing and wiring a mutation-testing harness for a toolchain this repo does not
otherwise use would be a net-new tooling decision outside this phase's scope (and outside what
`contracts/sprint-1.md`'s own acceptance criteria require). Property-based testing via `fast-check`
(`verification/fuzz-results/`, `~/anicca/skills/economy/lending/lib/__tests__/lending-gate.property.test.mjs`)
was used instead this session to get equivalent-in-spirit coverage against a wide input space for the
pure core, which is directly achievable with this repo's real toolchain (`node:test`).
