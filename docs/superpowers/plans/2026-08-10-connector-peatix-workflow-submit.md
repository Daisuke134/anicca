# Connector Peatix Workflow Submit Integration Plan

> **For Luna:** Use Superpowers test-driven-development. Execute every checkbox, preserve exact RED/GREEN evidence, and commit only the two owned Peatix workflow files.

**Goal:** Carry the exact usable free Peatix ticket identity from public discovery into each eligible candidate and expose the same script-first `runDirectAction` / `readProviderState` contract already used by Luma and Connpass.

**Architecture:** Extend the existing Peatix discovery workflow; do not create another workflow. Public detail normalization selects the first source-ordered ticket that already passes the measured free/open/inventory/deadline gate and stores only its numeric ticket ID. Direct action delegates to the reviewed browser provider with an injected in-memory attendee profile. Parent readback delegates independently and normalizes only registered/absent/unavailable.

**Tech Stack:** Node.js CommonJS, `node:test`, existing `peatix-browser-provider.js`.

## Ponytail gate

- **Reuse:** `createPeatixDiscoveryWorkflow`, existing detail ticket gate, existing provider candidate schema, and reviewed browser-provider exports.
- **Remove:** no existing behavior.
- **Do not build:** production router, Browser Harness fallback, auth, evidence, Calendar write, Telegram, registry, schedule, retry, or new module.
- **Plan size:** modify two existing files; production target under 60 LOC and tests under 80 LOC.

## Contract

- A returned eligible candidate contains `ticket_id` as a decimal string matching the first public ticket with exact `price=0`, `status=10`, positive inventory, and unexpired sales deadline.
- A closed/noneligible normalized detail may omit ticket identity internally; it must never be returned as a submit candidate.
- Invalid/missing/duplicate-safe ticket identity on an otherwise claimed available candidate fails closed at candidate validation.
- `runDirectAction` validates the full candidate, reads the attendee profile only in memory, and calls `submitPeatixOnPage(page, candidate, profile)` on the supplied page.
- Provider `registered` maps to `{status:"completed", method:"peatix_direct_submit"}`. Every other/ambiguous result maps to a frozen failed result with a safe fixed reason.
- `readProviderState` calls `readPeatixRegistrationStateOnPage` independently and exposes only `registered`, `absent`, or `unavailable`; raw provider reasons/private values are not forwarded.
- Existing discovery counts, ordering, 100-event cap, Calendar gate, safe stage codes, and page reuse remain unchanged.

---

### Task 1: Extend the Peatix workflow with exact ticket/action/readback

**Files:**
- Modify: `apps/mr-bot/lib/connector-peatix-workflow.js`
- Modify: `apps/mr-bot/lib/connector-peatix-workflow.test.js`

- [ ] **Step 1: Write failing ticket identity tests**

Add public ticket IDs to compact fixtures. Assert the first source-ordered usable free ticket becomes candidate `ticket_id`; closed, sold-out, and expired tickets cannot supply it. Assert an available candidate without exact positive ticket ID is rejected before provider action.

- [ ] **Step 2: Write failing direct action/readback tests**

Inject `submitOnPage`, `readStateOnPage`, and `readAttendeeProfile`. Assert the same supplied page/candidate/profile reaches submit, registered maps to completed/method, ambiguous maps to failed fixed reason, and independent readback normalizes registered/absent/unavailable without leaking raw reason or profile values.

- [ ] **Step 3: Run focused RED**

```bash
node --test apps/mr-bot/lib/connector-peatix-workflow.test.js
```

Expected: new assertions fail because candidates omit ticket identity and the workflow exposes discovery only.

- [ ] **Step 4: Implement the minimal extension**

Import the two reviewed provider functions, retain the existing factory/export name, select one exact usable ticket during detail normalization, and add the two workflow methods. Keep profile lookup lazy so discovery never reads private identity.

- [ ] **Step 5: Run focused and provider regression GREEN**

```bash
node --test apps/mr-bot/lib/connector-peatix-workflow.test.js

node --test \
  apps/mr-bot/lib/peatix-browser-provider.test.js \
  apps/mr-bot/lib/connector-peatix-workflow.test.js \
  apps/mr-bot/lib/connector-connpass-workflow.test.js \
  apps/mr-bot/lib/connector-luma-workflow.test.js \
  apps/mr-bot/lib/connector-minimal-runner.test.js
```

Expected: all pass, zero failures, no external access.

- [ ] **Step 6: Commit and push Luna-owned files**

```bash
git add apps/mr-bot/lib/connector-peatix-workflow.js \
  apps/mr-bot/lib/connector-peatix-workflow.test.js
git commit -m "feat(connector): connect Peatix submit workflow"
git push origin feature/connector-native-completion
```

After Luna reports RED/GREEN, a fresh Sol reviewer inspects the exact diff. Sol then plans production router/native entrypoint wiring as a separate external-effect slice.
