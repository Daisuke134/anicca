# Steel Real Cloud E2E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove with a reusable command that production `life-call` can drive the private Railway `steel-browser` through a real CDP session, read a real page, and release the session.

**Architecture:** Add one dependency-injected smoke runner beside the existing Life Manager scripts. Unit tests pin orchestration and cleanup; the production verification runs the same script inside the deployed `life-call` container so `steel-browser.railway.internal` is reached over Railway private networking.

**Tech Stack:** Node.js 20+, built-in `node:test`, existing `makeSteelCdpClient`, Railway CLI/SSH.

## Global Constraints

- Do not stop, restart, unload, or replace any Mac Mini launchd loop.
- Do not expose Steel publicly; the measured default is `http://steel-browser.railway.internal:8080`.
- A passing unit test is not E2E proof. Completion requires a real session, navigation, DOM readback, and successful release from production `life-call`.
- The smoke target is read-only and configurable through `STEEL_SMOKE_URL`; default `https://example.com/`.
- Never print page content or credentials. Emit bounded structural evidence only.
- Follow strict TDD: observe the new test fail before adding the runner.

---

### Task 1: Reusable Steel cloud smoke runner

**Files:**
- Create: `apps/life-manager/scripts/steel-cloud-smoke.js`
- Create: `apps/life-manager/scripts/steel-cloud-smoke.test.js`
- Modify: `apps/life-manager/package.json`
- Modify: `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`
- Create: `docs/superpowers/evidence/2026-07-28-steel-real-cloud-e2e.md`

**Interfaces:**
- Consumes: `makeSteelCdpClient()` with `health()`, `createSession()`, `navigate()`, `readConfirmation()`, and `releaseSession()`.
- Produces: `runSteelCloudSmoke({ client, targetUrl, marker, now }) -> Promise<evidence>`.
- CLI: `npm run smoke:steel-cloud`, exit `0` only when health, real readback, marker match, and release all succeed.

- [x] **Step 1: Write the failing orchestration tests**

Create tests that use a deterministic client double to assert:

```javascript
assert.deepEqual(client.calls.map(([kind]) => kind), [
  "health", "createSession", "navigate", "readConfirmation", "releaseSession",
]);
assert.equal(result.ok, true);
assert.equal(result.readback.marker_present, true);
assert.equal(result.released, true);
assert.equal("text" in result.readback, false);
```

Add a failure-path test where `readConfirmation()` throws and assert that `releaseSession()` still runs exactly once and the result is not successful.

- [x] **Step 2: Run the new test and verify RED**

Run:

```bash
cd apps/life-manager
node --test scripts/steel-cloud-smoke.test.js
```

Expected: FAIL because `./steel-cloud-smoke.js` does not exist.

- [x] **Step 3: Add the minimal runner and package command**

Implement `runSteelCloudSmoke` with:

```javascript
const healthy = await client.health();
if (!healthy) throw new Error("steel health check failed");
session = await client.createSession({ timezone: "Asia/Tokyo", dimensions: { width: 1280, height: 800 } });
await client.navigate(session.id, targetUrl);
const page = await client.readConfirmation(session.id);
```

Return structural evidence containing timestamps, target/final URL, session id, websocket scheme, marker presence, `ok`, and `released`; do not include page text. Release in `finally`. Add `"smoke:steel-cloud": "node scripts/steel-cloud-smoke.js"` to `package.json`.

- [x] **Step 4: Run focused verification**

Run:

```bash
cd apps/life-manager
node --test scripts/steel-cloud-smoke.test.js lib/steel-cdp-client.test.js lib/cdp-connection.test.js lib/care-booking-executor.test.js lib/care-booking-wiring.test.js lib/care-daily-runtime.test.js
```

Expected: all tests PASS.

- [x] **Step 5: Run the real production E2E**

Copy the committed runner to a temporary path inside the production `life-call` container and execute it with `NODE_PATH=/app/node_modules`, requiring the deployed `/app/lib/steel-cdp-client.js`. The JSON result must prove:

```json
{
  "ok": true,
  "health": true,
  "readback": {
    "final_url": "https://example.com/",
    "marker_present": true
  },
  "released": true
}
```

Read back `steel-browser` logs for the matching session creation/navigation/release and store the bounded command output in the evidence document.

- [x] **Step 6: Advance the SSOT and commit**

Update the live `11c+11d` row and the detailed `11c` row to distinguish:

- Steel infrastructure/CDP smoke: verified.
- Real provider booking receipt: still event-gated until an actionable care detection exists.

Run the full Life Manager test suite, inspect the final diff, commit, push to `canonical`, merge through the repository's normal PR path, verify Railway production SHA/status, and rerun `npm run smoke:steel-cloud` inside production.
