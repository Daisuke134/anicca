# Manager-review corrective RED rescue

- Base/source HEAD: `05da7b34f685089b4402ef01f28ef40a1bc0eb2e`
- Phase: `2b`
- Sprint count: `0`
- Provider/network/TG/email/call/L3/final production report/deploy/merge: `NOT USED`
- Production/verifier/test-support implementation diff from the base: `0 paths`
- Global active feature: `fable5-config-slimdown` (unchanged)

## Grounding

- Source: [Node.js child process documentation](https://github.com/nodejs/node/blob/main/doc/api/child_process.md) / Core quote: “`signal` {AbortSignal} allows aborting the child process using an AbortSignal.”
- Source: [Node.js test runner documentation](https://github.com/nodejs/node/blob/main/doc/api/test.md) / Core quote: “files can be explicitly included via the `--test-coverage-include` flag.”
- Source: [JSON Schema validation specification](https://github.com/json-schema-org/json-schema-spec/blob/main/specs/jsonschema-validation.md) / Core quote: “JSON Schema validation asserts constraints on the structure of instance data.”

The required `crwl` fetches failed because the installed Playwright Chromium executable was absent. The same primary-source documents were read through the official GitHub repositories with `gh api`.

## Exact observations

Entry bundle before audit:

```text
cd apps/life-call && node --test --test-concurrency=1 lib/daily-preflight-final-schema.test.js lib/daily-preflight-poll-boundaries.test.js lib/daily-preflight-provenance.test.js lib/daily-preflight-purity-contract.test.js lib/transport/mail-gog-receipt.test.js lib/daily-preflight-abort-lineage.test.js
112 tests = 97 PASS / 15 FAIL
```

The audit removed one test that demanded cancellation of an arbitrary non-cooperative JavaScript timer. That assertion violated the order's explicit cancellation boundary. Actual provider/process/poll/wait lineage tests remain RED.

Audited application RED bundle:

```text
cd apps/life-call && node --test --test-concurrency=1 lib/daily-preflight-final-schema.test.js lib/daily-preflight-poll-boundaries.test.js lib/daily-preflight-provenance.test.js lib/daily-preflight-purity-contract.test.js lib/transport/mail-gog-receipt.test.js lib/daily-preflight-abort-lineage.test.js
111 tests = 97 PASS / 14 FAIL
```

Verifier-contract RED bundle:

```text
node --test --test-concurrency=1 .vcsdd/features/life-manager-daily-preflight/tests/verifier-contracts.test.mjs
26 tests = 14 PASS / 12 FAIL
```

Full intended manager-review RED bundle:

```text
node --test --test-concurrency=1 apps/life-call/lib/daily-preflight-final-schema.test.js apps/life-call/lib/daily-preflight-poll-boundaries.test.js apps/life-call/lib/daily-preflight-provenance.test.js apps/life-call/lib/daily-preflight-purity-contract.test.js apps/life-call/lib/transport/mail-gog-receipt.test.js apps/life-call/lib/daily-preflight-abort-lineage.test.js .vcsdd/features/life-manager-daily-preflight/tests/verifier-contracts.test.mjs
137 tests = 111 PASS / 26 FAIL
```

Fresh proof for the pre-existing test beads:

```text
node --test --test-concurrency=1 '--test-name-pattern=^(schema|checkedAt|dependency|failure|security|poll|timeout|deadline|purity|verify-)' apps/life-call/lib/daily-preflight-poll-boundaries.test.js apps/life-call/lib/daily-preflight-final-schema.test.js apps/life-call/lib/daily-preflight-purity-contract.test.js .vcsdd/features/life-manager-daily-preflight/tests/verifier-contracts.test.mjs
75 tests = 75 PASS / 0 FAIL
```

## RED ledger

- New RED assertions/beads: `26`
- Beads: `BEAD-129..BEAD-154`
- External test IDs: `TEST-076..TEST-101`
- Pre-existing beads: `75 GREEN`
- Reopened findings: `FIND-001..FIND-011` (`11 OPEN`)

The 26 failures cover zero-argument caller purity, actual abort lineage, abort-capable gog process execution, actual observation/current-run binding, one-millisecond stale receipt preservation, complete changed-module coverage, mandatory changed CLI coverage, production-JavaScript safe scan, graph reachability, installed-schema application, changed-path/historical/root-spec scope, and controlled-L3 module evidence closure.

Two new manager audit assertions are already GREEN and therefore do not receive RED beads: below-90 module data is rejected, and the stored `f9a35c8d2` controlled-L3 snapshot is rejected against current `05da7b34f` HEAD/tree.

## VCSDD validation

```text
node /Users/anicca/.codex/plugins/cache/vcsdd-claude-code/vcsdd/1.0.0/scripts/verify-vcsdd-state.js
verify-vcsdd-state: OK

node /Users/anicca/.codex/plugins/cache/vcsdd-claude-code/vcsdd/1.0.0/scripts/verify-vcsdd-runtime.js
verify-vcsdd-runtime: OK

installed schema validation: state + sprint verdict + FIND-001..FIND-011 = OK
```

No validator incompatibility was observed. No phase transition or sprint increment was performed.
