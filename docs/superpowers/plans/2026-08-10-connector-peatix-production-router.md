# Connector Peatix Production Router Implementation Plan

> **For Luna:** Use Superpowers test-driven-development. Commit only the two owned production-router files.

**Goal:** Install the reviewed Peatix workflow in the official production dependency factory/router while keeping the native provider order unchanged until evidence support is ready.

**Architecture:** Add Peatix as the third route in the existing provider router, with its own workflow version and existing common cache/direct/readback methods. The production factory constructs one Peatix workflow, wires the new durable aggregate audit, and supplies an injected in-memory attendee profile lazily. The Browser Harness may fail closed for Peatix; this slice adds no generic fallback.

**Tech Stack:** Node.js CommonJS, `node:test`, existing minimal production factory.

## Ponytail gate

- Reuse `createProductionProviderRouter`, common action cache, `createPeatixDiscoveryWorkflow`, and `recordPeatixDiscoveryAudit`.
- Add no new factory, registry, state file, provider cursor, or browser target.
- Do not modify `skills/connector/native-pass.js`, `DEFAULT_PROVIDERS`, evidence, schedule, auth, or external state.
- Plan size: modify two files; production target under 55 LOC, tests under 80 LOC.

## Contract

- Router accepts exactly `luma`, `connpass`, and `peatix`; unknown providers still fail closed.
- Peatix uses `peatix_registration_v1`, one supplied page, common cache contract, reviewed direct action, and independent readback.
- Default factory creates Peatix workflow once and wires `operations.recordPeatixDiscoveryAudit`.
- `peatixAttendeeProfile` remains in memory, is read only by direct action, and never appears in cache/audit/output.
- Discovery alone never requires or reads attendee profile.
- Existing Luma/Connpass behavior and Browser Harness contract remain unchanged.

### Task 1: Wire Peatix into the production factory/router

**Files:**
- Modify: `apps/mr-bot/lib/connector-minimal-production.js`
- Modify: `apps/mr-bot/lib/connector-minimal-production.test.js`

- [ ] Write RED tests for Peatix default discovery/audit and same-page cache/direct/readback routing with `peatix_registration_v1`.
- [ ] Assert discovery never reads the attendee profile; direct action reads it exactly once; private values do not enter cache/audit results.
- [ ] Assert Luma/Connpass router tests remain unchanged and unknown provider still rejects.
- [ ] Run RED: `node --test apps/mr-bot/lib/connector-minimal-production.test.js`.
- [ ] Import/create one Peatix workflow, add the third selected route/version, and wire the Peatix audit/profile callbacks with the minimum diff.
- [ ] Run GREEN:

```bash
node --test \
  apps/mr-bot/lib/connector-minimal-production.test.js \
  apps/mr-bot/lib/connector-minimal-operations.test.js \
  apps/mr-bot/lib/connector-peatix-workflow.test.js \
  apps/mr-bot/lib/peatix-browser-provider.test.js \
  apps/mr-bot/lib/connector-minimal-runner.test.js
```

- [ ] Run `node --check` and `git diff --check`.
- [ ] Commit `feat(connector): route Peatix in production factory` and push `feature/connector-native-completion`.

After Luna reports RED/GREEN, fresh Sol review verifies the route. Peatix remains absent from the native provider order until the provider-neutral evidence bundle can complete after a real registration.
