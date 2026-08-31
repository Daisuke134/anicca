# Connector Native Local Implementation Plan

> **For delegated implementers:** Execute this plan as one bounded vertical slice at a time. Each production behavior starts with an observed failing test and ends with the focused test green. This delegated slice does not commit or push; the primary agent performs acceptance.

**Goal:** Deliver only the lifecycle scaffold for a future native, bounded Connector pass that launchd can invoke directly on the Mac mini without making a bridge, container worker, or runtime queue its execution owner. Tasks 1–3 do not execute Luma search or registration, receipt verification, Calendar synchronization, or Telegram delivery; this slice is not Connector completion.

**Architecture:** `skills/connector/run.sh` owns process lifecycle only: resolve the canonical repository, load an existing secret environment without echoing it, acquire a process-scoped stale-safe lock, update private heartbeat state, invoke one direct `runNativeConnectorPass`, and release only its own lock. `WORKER-CONTRACT.md` is documentation-only; the runtime reuses existing local Luma and `gog` modules while deterministic helpers own locking, timestamps, state, health, and rendering. launchd templates are render-only contracts whose rendered paths remain under the canonical repository.

**Tech Stack:** Bash 3.2-compatible entrypoints; Node.js built-ins for atomic state and testable lifecycle logic; existing `apps/mr-bot/lib/*` Connector modules; launchd XML templates; `node --test`.

## Global Constraints

- Canonical execution owner is Mr.bot local; no external agent runner or executable override participates in the pass.
- The daily-driver endpoint is `http://127.0.0.1:9222`; do not start, kill, or sweep its browser process or pre-existing tabs.
- The direct runtime may close only pages it created under the Connector owner lease.
- Calendar inventory uses installed `gog` across all calendars; a static availability file is not an input.
- The rolling horizon is exactly 21 days and only `open=0` is complete. A failed source, candidate, or date records continuation rather than success.
- Deterministic code never selects an event. Candidate relevance, serendipity, and ordering remain outside this read-only composition slice.
- Do not add package dependencies, a queue, a bridge, a container path, or a new browser process.
- Do not send Telegram, register for an event, write a Calendar event, mutate launchd, or stop an existing runtime in this code/test slice.
- Keep secret values out of stdout, logs, source control, template values, and test fixtures.

## File Structure

- `skills/connector/run.sh` — canonical bounded-pass entrypoint and lifecycle owner.
- `skills/connector/healthcheck.sh` — read-only freshness, dependency, and daily-driver health contract.
- `skills/connector/render-launchd.sh` — render native templates to an explicitly supplied non-live output directory; never loads them.
- `skills/connector/lib/native-state.js` — atomic lock, owner token, heartbeat, and health snapshot helper.
- `skills/connector/native-pass.js` — validates and invokes the direct local runtime; no executable override is accepted.
- `skills/connector/WORKER-CONTRACT.md` — documentation-only reference for existing local module boundaries; it is not loaded or executed by native-pass.
- `skills/connector/test/native-state.test.js` — lifecycle behavior tests using an isolated temporary state directory.
- `skills/connector/test/native-entrypoint.test.js` — direct-runtime result, continuation, healthcheck, and template-rendering contract tests.
- `apps/mr-bot/launchd/ai.anicca.mr-bot-connector-native.plist.template` — canonical native scheduled pass template.
- `apps/mr-bot/launchd/ai.anicca.mr-bot-connector-native-healthcheck.plist.template` — canonical native healthcheck template.

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

### Task 2: Native bounded-pass entrypoint and direct-runtime contract

**Files:**

- Create: `skills/connector/run.sh`
- Create: `skills/connector/native-pass.js`
- Create: `skills/connector/WORKER-CONTRACT.md`
- Test: `skills/connector/test/native-entrypoint.test.js`

**Interfaces:**

- Consumes: an optional existing env file, `LM_CONNECTOR_STATE_DIR`, and the canonical repository path computed from `run.sh` itself. No environment variable selects an executable or bypasses the direct runtime.
- Produces: one direct `runNativeConnectorPass` invocation or a truthful `busy` exit; a heartbeat before and after the pass; no printed secret value.
- The local contract documents existing module seams for Luma and `gog`; it is not an executable handoff or a public worker override.

- [x] **Step 1: Write failing entrypoint tests**

```js
test("native-pass invokes the direct runtime even when a legacy worker env value exists", async () => {
  const result = await runNativePass({ stateDir, env: { CONNECTOR_NATIVE_WORKER_BIN: "/tmp/ignored" }, runRuntime });
  assert.equal(result.exitCode, 1);
});

test("open coverage stays incomplete and writes a continuation", async () => {
  const result = await runNativePass({ stateDir, runRuntime: incompleteRuntime });
  assert.equal(result.exitCode, 1);
});
```

- [x] **Step 2: Run RED**

Run: `node --test skills/connector/test/native-entrypoint.test.js`

Expected: failure because native-pass still accepted a public executable worker override.

- [x] **Step 3: Implement the minimum lifecycle path**

`run.sh` uses `set -eu`, `umask 077`, a dynamically resolved repository root, the existing guarded env loader, and an EXIT trap. It calls `native-pass.js` once with the acquired owner token. `native-pass.js` always invokes the direct runtime (except a programmatic `runRuntime` test function), validates the bounded result, and preserves nonzero continuation semantics; it does not convert a failed source or `open>0` into success. The local contract names the shared daily-driver ownership rule and existing module interfaces without adding an executable selection path.

- [x] **Step 4: Run GREEN**

Run: `node --test skills/connector/test/native-entrypoint.test.js`

Expected: direct-runtime and lifecycle-state tests pass; no live browser, Calendar, event, Telegram, or launchd action runs.

### Task 3: Render-only launchd and read-only healthcheck contracts

**Files:**

- Create: `skills/connector/healthcheck.sh`
- Create: `skills/connector/render-launchd.sh`
- Create: `apps/mr-bot/launchd/ai.anicca.mr-bot-connector-native.plist.template`
- Create: `apps/mr-bot/launchd/ai.anicca.mr-bot-connector-native-healthcheck.plist.template`
- Test: `skills/connector/test/native-entrypoint.test.js`

**Interfaces:**

- Consumes: `--output-dir`, `--repo-root`, and `--mr-bot-home` for template rendering; healthcheck consumes the state directory and a read-only `:9222` probe.
- Produces: two plists whose program and working-directory paths are canonical after rendering; a health exit status based on state freshness, `gog` availability, and browser endpoint reachability.
- Neither script invokes `launchctl` or changes browser state.

- [x] **Step 1: Write failing template and health tests**

```js
test("rendered native templates contain canonical paths and no legacy runtime dependency", () => {
  renderTemplates({ outputDir, repoRoot, mrBotHome });
  assert.match(readNativeTemplate(), /\/Users\/anicca\/Projects\/mr-bot-main\/skills\/connector\/run\.sh/);
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

Run: `rg -n 'docker|host\.docker\.internal|connector-host-bridge|profitable-claude' skills/connector apps/mr-bot/launchd/ai.anicca.mr-bot-connector-native*.plist.template`

Expected: tests pass; the static scan finds no runtime dependency in the new native path.

### Task 4: Direct existing-module runtime integration (bounded read-only slice)

**Files:**

- Create: `apps/mr-bot/lib/connector-native-runtime.js`
- Test: `apps/mr-bot/lib/connector-native-runtime.test.js`
- Modify: `skills/connector/native-pass.js`

**Interfaces:**

- Consumes: `createCloakBrowserDailyDriver`, `createReadOnlyLumaSessionAuth`, `createConnectorEventsPack`, `makeGogCalendar`, and `buildRollingEventCoverage`.
- Produces: a single direct-local read result with Luma inventory, all-calendar busy inventory, and the next 21-day coverage continuation; it exposes no raw provider/secret payload.

- [x] **Step 1: Write failing direct-composition tests**

```js
test("a direct native pass reads all calendars and keeps open coverage open", async () => {
  const result = await runNativeConnectorPass(dependenciesWithCandidateFailure);
  assert.equal(result.coverage.counts.open > 0, true);
  assert.equal(result.continuation.status, "continue");
});
```

Evidence: `apps/mr-bot/lib/connector-native-runtime.test.js` covers shared daily-driver construction,
read-only auth, complete Luma inventory, all-calendar `gog` busy inventory, coverage continuation, and a
secret-free projection. Registration, receipt verification, Calendar write/sync, and Telegram delivery are not
consumed by this slice and remain the next live boundary.

- [x] **Step 2: Run RED**

Run: `node --test apps/mr-bot/lib/connector-native-runtime.test.js`

Observed RED: the busy-calendar assertion addressed the calendar slot instead of its `(calendar, options)` test
double argument, and the native-pass regression showed that a public executable env override bypassed direct
runtime composition. Both failures were corrected by fixing the test seam and removing the executable path.

- [x] **Step 3: Implement composition only from existing modules**

Construct the daily-driver with the fixed loopback endpoint; attach and close only a page created by that driver;
use read-only auth, `createConnectorEventsPack`, and `makeGogCalendar` for Luma/all-calendar reads; reuse the
existing coverage and continuation modules. Registration, receipt verification, Calendar write/sync, and Telegram
delivery remain deferred and are never called here. `native-pass.js` invokes this runtime directly in production;
only a programmatic `runRuntime` function is injectable in tests. Non-complete runtime results persist a
continuation and exit nonzero.

- [x] **Step 4: Run GREEN**

Run: `node --test apps/mr-bot/lib/connector-native-runtime.test.js`

Evidence: `node --test apps/mr-bot/lib/connector-native-runtime.test.js` passes 2/2; focused native-pass
tests pass with env-override regression coverage; no external write boundary is invoked and `open=21` remains
`incomplete` with `refresh_inventory` continuation.

### Task 5: Explicit native write pipeline (bounded registration, Calendar, coverage, Telegram)

**Files:**

- Create: `apps/mr-bot/lib/connector-native-write-pipeline.js`
- Test: `apps/mr-bot/lib/connector-native-write-pipeline.test.js`
- Modify: `apps/mr-bot/lib/connector-coverage-telegram.js`
- Test: `apps/mr-bot/lib/connector-coverage-telegram.test.js`

**Interfaces:**

- Consumes a chosen application, verified date inventory, rolling coverage, Google busy inventory, Calendar write context, and Telegram target.
- Runs the trusted chain in order: application job → Luma RSVP → verified receipt → Calendar sync → coverage rebuild → Telegram delivery.
- Produces only secret-free status and opaque references. Unknown external effects stop at reconciliation and never advance to Calendar or Telegram.

- [x] **Step 1: Write failing pipeline tests**

  The tests cover unknown RSVP effects, receipt and Calendar gates, coverage-before-Telegram ordering, exact Telegram receipt binding, and incomplete coverage.

- [x] **Step 2: Run RED**

  `node --test lib/connector-native-write-pipeline.test.js` failed with `MODULE_NOT_FOUND` because the orchestrator did not exist. The Telegram copy test separately failed because production claimed confirmation-mail verification that Task 5 does not perform.

- [x] **Step 3: Implement the minimum verified chain**

  `runNativeConnectorWrite` reuses existing production modules and accepts dependency overrides only at trusted test seams. The Telegram copy now claims only registration evidence and Calendar registration. Gmail confirmation, guest binding, and ticket/QR remain Task 6.

- [x] **Step 4: Run GREEN**

  `node --test lib/connector-native-write-pipeline.test.js lib/connector-coverage-telegram.test.js lib/connector-native-runtime.test.js` passes 24/24. The default native runtime still remains read-only; connecting candidate judgment and this write pipeline is the next task.

## Plan Self-Review

- Coverage boundary: Tasks 1–3 deliver the native boot/launchd lifecycle scaffold. Task 4 completes shared browser auth, Luma inventory, all-calendar `gog` reads, and coverage continuation. Task 5 provides a production-capable write orchestrator behind an explicit chosen-candidate boundary, but the default runtime does not invoke it and no live side effect is claimed.
- Judgment boundary: no task encodes relevance, preference, or candidate selection in deterministic code; the local contract documents that boundary without becoming an executable override.
- Safety: Tasks 1–4 remain local or read-only. Task 5 adds verified write composition without invoking it live. Real registration, Gmail/ticket verification, Calendar write/readback, Telegram send, and launchd loading remain later explicit gates.
- Scope: all planned production files are within the delegated ownership set; no master specification, runtime queue, bridge, package manifest, or lockfile changes are included.
