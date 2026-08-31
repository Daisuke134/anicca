# Connector KokuchPro production factory 20F2 implementation plan

> **Execution:** Ponytail `full` limits this slice to the existing production dependency factory/router. Use Superpowers TDD. Sol plans/verifies/updates SSOT/commits/pushes; Luna owns production/tests; fresh Sol reviews Critical/Important.

**Goal:** Make `createMinimalProductionDependencies` construct and route KokuchPro through the existing one configured extension proposer/Harness seam with durable audit.

**Architecture:** Import/create the existing KokuchPro workflow with `recordKokuchProDiscoveryAudit`. Add exact `kokuchpro` route/version validation to the existing provider router. Configure the bounded proposer with `extensionProvider:"kokuchpro"`, and the default Harness with the exact workflow pair. Route discovery/direct/readback/fallback through the same page. Cache save/replay remains available structurally but an auth safe failure saves nothing. No new registry/service/module or browser/native/evidence/schedule change.

**Ponytail size gate:**

- Modify `apps/mr-bot/lib/connector-minimal-production.js` — about 25–45 production LOC.
- Modify `apps/mr-bot/lib/connector-minimal-production.test.js` — about 90–140 focused LOC.
- Exact two files. If production exceeds 60 LOC, reduce scope before continuing.

## Task 1 — TDD default factory routing

RED proves injected KokuchPro discovery/direct/readback/fallback is unsupported and default factory lacks the audit/extension pair. GREEN proves: exact provider only; supplied page preserved; discovery audit callback invoked; direct safe failure; canonical/detail readback routed; configured Harness auth preflight returns `auth_required` with proposer/operate/private resolution zero; invalid partial workflow rejected; existing providers unchanged. Run minimal-production, KokuchPro workflow, Harness extension-adjacent tests, syntax/diff, fresh review.
