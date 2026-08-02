# Connector Native Local Implementation Plan

> **For agentic workers:** Execute this plan as one bounded vertical slice at a time. Each production behavior starts with an observed failing test and ends with the focused test green. This delegated slice does not commit or push; the primary agent performs acceptance.

**Goal:** Deliver only the lifecycle scaffold for a future native, bounded Connector pass that launchd can invoke directly on the Mac mini without making a bridge, container worker, or runtime queue its execution owner. Tasks 1–3 do not execute Luma search or registration, receipt verification, Calendar synchronization, or Telegram delivery; this slice is not Connector completion.

**Architecture:** `skills/connector/run.sh` owns process lifecycle only: resolve the canonical repository, load an existing secret environment without echoing it, acquire a process-scoped stale-safe lock, update private heartbeat state, run one bounded Connector worker, and release only its own lock. The worker contract keeps event relevance and candidate choice in a natural-language agent loop while reusing existing local Luma, `gog`, receipt, Calendar, and Telegram modules; deterministic helpers own locking, timestamps, state, health, and rendering only. launchd templates are render-only contracts whose rendered paths remain under the canonical repository.

**Tech Stack:** Bash 3.2-compatible entrypoints; Node.js built-ins for atomic state and testable lifecycle logic; existing `apps/life-manager/lib/*` Connector modules; launchd XML templates; `node --test`.

## Global Constraints

- Canonical execution owner is Life Manager local; an agent runner is a bounded worker/tool compatibility layer only.
- The daily-driver endpoint is `http://127.0.0.1:9222`; do not start, kill, or sweep its browser process or pre-existing tabs.
- The worker may close only pages it created under the Connector owner lease.
- Calendar inventory uses installed `gog` across all calendars; a static availability file is not an input.
- The rolling horizon is exactly 21 days and only `open=0` is complete. A failed source, candidate, or date records continuation rather than success.
- Deterministic code never selects an event. Candidate relevance, serendipity, and ordering remain in the right-altitude worker prompt and model loop.
- Do not add package dependencies, a queue, a bridge, a container path, or a new browser process.
- Do not send Telegram, register for an event, write a Calendar event, mutate launchd, or stop an existing runtime in this code/test slice.
- Keep secret values out of stdout, logs, source control, template values, and test fixtures.

## File Structure

- `skills/connector/run.sh` — canonical bounded-pass entrypoint and lifecycle owner.
- `skills/connector/healthcheck.sh` — read-only freshness, dependency, and daily-driver health contract.
- `skills/connector/render-launchd.sh` — render native templates to an explicitly supplied non-live output directory; never loads them.
- `skills/connector/lib/native-state.js` — atomic lock, owner token, heartbeat, and health snapshot helper.
- `skills/connector/native-pass.js` — validates the local worker handoff and invokes the bounded worker executable supplied by the lifecycle owner.
- `skills/connector/WORKER-CONTRACT.md` — tool/prompt contract for direct use of existing Luma, receipt, Calendar, and Telegram modules.
- `skills/connector/test/native-state.test.js` — lifecycle behavior tests using an isolated temporary state directory.
- `skills/connector/test/native-entrypoint.test.js` — shell entrypoint, worker handoff, heartbeat, and template-rendering contract tests.
- `apps/life-manager/launchd/ai.anicca.life-manager-connector-native.plist.template` — canonical native scheduled pass template.
- `apps/life-manager/launchd/ai.anicca.life-manager-connector-native-healthcheck.plist.template` — canonical native healthcheck template.

---

### Task 1: Lock and heartbeat state helper

**Files:**

- Create: `skills/connector/lib/native-state.js`
- Test: `skills/connector/test/native-state.test.js`

**Interfaces:**

- Consumes: `stateDir`, owner `token`, process `pid`, and a clock supplied only in tests.
- Produces: `acquireLock({ stateDir, token, pid, now, staleMs })`, `heartbeat({ stateDir, token, stage, now })`, `releaseLock({ stateDir, token })`, and `readHealth({ stateDir, now, staleMs })`.
- Lock metadata contains no environment values and is released only when the supplied token matches the holder.

- [x] **Step 1: Write failing lock tests**

```js
test("a live owner blocks a concurrent native pass", () => {
  const first = acquireLock({ stateDir, token: "owner-a", pid: process.pid, now, staleMs: 60_000 });
  assert.equal(first.status, "acquired");
  assert.equal(acquireLock({ stateDir, token: "owner-b", pid: process.pid, now, staleMs: 60_000 }).status, "busy");
});

test("only a dead stale owner can be reaped", () => {
  writeLock({ pid: 999999, token: "dead", heartbeat_at: oldNow });
  assert.equal(acquireLock({ stateDir, token: "next", pid: process.pid, now, staleMs: 1 }).status, "acquired");
});
```

- [x] **Step 2: Run RED**

Run: `node --test skills/connector/test/native-state.test.js`

Expected: failure because `native-state.js` does not exist or does not export the requested lifecycle behavior.

- [x] **Step 3: Implement the minimum atomic helper**

Use `fs.mkdirSync(lockDir)` for acquisition, write owner metadata with mode `0600`, require both stale heartbeat and a failed `process.kill(pid, 0)` probe before reaping, and use token matching for heartbeat/release.

- [x] **Step 4: Run GREEN**

Run: `node --test skills/connector/test/native-state.test.js`

Expected: all lock, stale-reap, heartbeat, and non-owner release tests pass.

### Task 2: Native bounded-pass entrypoint and worker contract

**Files:**

- Create: `skills/connector/run.sh`
- Create: `skills/connector/native-pass.js`
- Create: `skills/connector/WORKER-CONTRACT.md`
- Test: `skills/connector/test/native-entrypoint.test.js`

**Interfaces:**

- Consumes: an optional existing env file, `LM_CONNECTOR_STATE_DIR`, `CONNECTOR_NATIVE_WORKER_BIN`, and the canonical repository path computed from `run.sh` itself.
- Produces: one bounded child invocation or a truthful `busy` exit; a heartbeat before and after the child; no printed secret value.
- The worker receives only non-secret paths and an owner token. Its contract names existing local module seams for Luma, `gog`, receipt validation, Calendar synchronization, and Telegram delivery.

- [x] **Step 1: Write failing entrypoint tests**

```js
test("run.sh resolves its repository, runs exactly one injected bounded worker, and releases its own lock", () => {
  const result = runEntrypoint({ stateDir, worker: fixtureWorker });
  assert.equal(result.status, 0);
  assert.equal(readFixtureInvocations(), 1);
  assert.equal(readHealth({ stateDir, now, staleMs: 60_000 }).lock.status, "idle");
});

test("a held live lock skips the worker without declaring coverage complete", () => {
  acquireLock({ stateDir, token: "other", pid: process.pid, now, staleMs: 60_000 });
  assert.equal(runEntrypoint({ stateDir, worker: fixtureWorker }).status, 75);
  assert.equal(readFixtureInvocations(), 0);
});
```

- [x] **Step 2: Run RED**

Run: `node --test skills/connector/test/native-entrypoint.test.js`

Expected: failure because the canonical entrypoint and worker handoff do not exist.

- [x] **Step 3: Implement the minimum lifecycle path**

`run.sh` uses `set -eu`, `umask 077`, a dynamically resolved repository root, the existing guarded env loader, and an EXIT trap. It calls `native-pass.js` once with the acquired owner token. `native-pass.js` requires a bounded executable and preserves its nonzero exit as a failure/continuation signal; it does not convert a missing candidate, failed child, or `open>0` into success. `WORKER-CONTRACT.md` defines the 21-day direct-local work loop, the shared daily-driver ownership rule, and the existing module interfaces without hardcoding event-selection judgment.

- [x] **Step 4: Run GREEN**

Run: `node --test skills/connector/test/native-entrypoint.test.js`

Expected: the fixture-isolated lifecycle tests pass; no live browser, Calendar, event, Telegram, or launchd action runs.

### Task 3: Render-only launchd and read-only healthcheck contracts

**Files:**

- Create: `skills/connector/healthcheck.sh`
- Create: `skills/connector/render-launchd.sh`
- Create: `apps/life-manager/launchd/ai.anicca.life-manager-connector-native.plist.template`
- Create: `apps/life-manager/launchd/ai.anicca.life-manager-connector-native-healthcheck.plist.template`
- Test: `skills/connector/test/native-entrypoint.test.js`

**Interfaces:**

- Consumes: `--output-dir`, `--repo-root`, and `--life-manager-home` for template rendering; healthcheck consumes the state directory and a read-only `:9222` probe.
- Produces: two plists whose program and working-directory paths are canonical after rendering; a health exit status based on state freshness, `gog` availability, and browser endpoint reachability.
- Neither script invokes `launchctl` or changes browser state.

- [x] **Step 1: Write failing template and health tests**

```js
test("rendered native templates contain canonical paths and no legacy runtime dependency", () => {
  renderTemplates({ outputDir, repoRoot, lifeManagerHome });
  assert.match(readNativeTemplate(), /\/Users\/anicca\/Projects\/life-manager-main\/skills\/connector\/run\.sh/);
  assert.doesNotMatch(readNativeTemplate(), forbiddenRuntimePattern);
});

test("healthcheck rejects stale heartbeat without running a recovery command", () => {
  const result = runHealthcheck({ stateDir: staleState, probe: healthyBrowserProbe });
  assert.notEqual(result.status, 0);
  assert.equal(result.stdout.includes("launchctl"), false);
});
```

- [x] **Step 2: Run RED**

Run: `node --test skills/connector/test/native-entrypoint.test.js`

Expected: failure because no render-only templates or healthcheck exist.

- [x] **Step 3: Implement the smallest contract**

Render placeholders using exact path values and refuse the live LaunchAgents directory as a renderer output. Use `StartInterval`, `ThrottleInterval`, canonical `WorkingDirectory`, and separate logs in both templates. The healthcheck probes `http://127.0.0.1:9222/json/version` read-only and never starts/kills a process.

- [x] **Step 4: Run GREEN and static constraints**

Run: `node --test skills/connector/test/native-entrypoint.test.js`

Run: `rg -n 'docker|host\.docker\.internal|connector-host-bridge|profitable-claude' skills/connector apps/life-manager/launchd/ai.anicca.life-manager-connector-native*.plist.template`

Expected: tests pass; the static scan finds no runtime dependency in the new native path.

### Task 4: Direct existing-module worker integration (next bounded slice)

**Files:**

- Create: `apps/life-manager/lib/connector-native-runtime.js`
- Test: `apps/life-manager/lib/connector-native-runtime.test.js`
- Modify: `skills/connector/native-pass.js`

**Interfaces:**

- Consumes: `createCloakBrowserDailyDriver`, `makeGogCalendar`, `createConnectorEventsPack`, existing Luma evidence/receipt helpers, Calendar sync, and coverage Telegram composer/delivery.
- Produces: a single direct-local pass result that records the next continuation on failure and exposes no raw provider/secret payload.

- [ ] **Step 1: Write failing direct-composition tests**

```js
test("a direct native pass reads all calendars and keeps open coverage open after a candidate failure", async () => {
  const result = await runNativeConnectorPass(dependenciesWithCandidateFailure);
  assert.equal(result.coverage.counts.open > 0, true);
  assert.equal(result.continuation.complete, false);
});
```

- [ ] **Step 2: Run RED**

Run: `node --test apps/life-manager/lib/connector-native-runtime.test.js`

Expected: failure because the direct composition does not exist.

- [ ] **Step 3: Implement composition only from existing modules**

Construct the daily-driver with the fixed loopback endpoint; attach and close only a page created by that driver; invoke `makeGogCalendar` for all-calendar inventory; use existing Luma, receipt, Calendar, and Telegram modules rather than copied logic. Persist a continuation record for every non-complete result.

- [ ] **Step 4: Run GREEN**

Run: `node --test apps/life-manager/lib/connector-native-runtime.test.js`

Expected: deterministic integration contracts pass without an external write.

## Plan Self-Review

- Coverage boundary: Tasks 1–3 deliver only the native boot/launchd lifecycle scaffold: lock, heartbeat, healthcheck, dynamic canonical path, and bounded worker handoff. Actual Luma search/registration, receipt verification, Calendar synchronization, and Telegram delivery remain Task 4; until that task is implemented and verified, this slice must not be called Connector completion.
- Judgment boundary: no task encodes relevance, preference, or candidate selection in deterministic code; `WORKER-CONTRACT.md` carries that guidance to the model loop.
- Safety: every action in Tasks 1–3 is local state, template rendering to an explicit test directory, or read-only health probing. Real registration, Calendar write, Telegram send, launchd loading, and legacy retirement remain outside this slice.
- Scope: all planned production files are within the delegated ownership set; no master specification, runtime queue, bridge, package manifest, or lockfile changes are included.
