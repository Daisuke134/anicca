# WebMCP Money Printer Submission Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Life Manager as a deployed WebMCP-enabled general entrepreneur agent that discovers opportunities anywhere, proves one fenced Lancers application with official readback, exposes minimal-human collaboration, and reaches a verified Devpost submission before September 4, 2026 05:00 JST.

**Architecture:** Start from current `origin/main`. Reuse `general-agent-work-adapter`, `marketplace-application-job/effect/adapter`, runtime/browser job stores, loop adapter registry, Panel auth/API/UI, Lancers application code, Mercor receipt contracts, ask/reply patterns, and money ledgers. Add one Money Printer projection, one durable human-task contract, and one Panel/WebMCP surface. The model judges opportunities and tool use; deterministic code owns identity, arithmetic, authorization, idempotency, effects, receipts, and tenant isolation.

**Tech Stack:** Node.js CommonJS and `node:test`, Python 3.14-compatible standard library and pytest, PostgreSQL/Supabase RPCs, Railway, Netlify `/money-printer`, imperative WebMCP, ChatGPT in-app browser, Chrome 149+.

## Global Constraints

- Execute from a locked worktree created from fresh `origin/main`, never this older docs checkout.
- Merge spec, plan, submission draft, and mockup into current main before production implementation.
- Require at least 8 GiB free before install, browser E2E, screenshot, or video work. Never remove credentials, profiles, state, receipts, customer projects, immutable releases, or memory.
- Capability is general: X, Web, GitHub, mail, search, arbitrary URLs, Lancers, Mercor, and unknown marketplaces use the same goal/job/tool loop.
- Provider names never select judgment logic. Provider code handles only auth, observation, selectors, typed effects, and official readback.
- Missing Skill/provider history never blocks feasible work. Missing effect/auth/readback blocks only the external effect.
- Coconala is absent from source, UI, demo, and story. Only provider-neutral shared primitives remain reusable.
- Existing Workday owners remain paused. Mercor stops at the provider-required human interview boundary.
- Application requires authorization → immutable intent → presend reconcile → at most one effect → official readback → canonical receipt → replay zero.
- Unknown effect is never retried. Guest and owner share code, never tenant, credentials, state, or effect authority.
- Applications, offers, pending balances, agent completion, and historical rows are not verified money.
- No fake/mock/dry-run effect can support a working-product claim.
- Internal submit target: September 3 12:00 JST. Official deadline: September 4 05:00 JST.
- One active task at a time. Every task ends with focused verification, spec update, commit, and push.

## Uncertainty Closure Order

| Gate | Closed by | Pass evidence | Failure action |
|---|---|---|---|
| Disk/current main | Preflight | >=8 GiB; execution HEAD descends from current origin/main | Stop before build |
| Eligibility/rules | Preflight + Task 9 | current official rules/form readback; ownership/conflict fields pass | Do not rely on cached draft |
| Deploy provenance | Tasks 4 and 8 | Netlify source fixed; deployed SHA = public repo SHA; required headers | Do not record live URL |
| Lancers runtime truth | Task 1 | loaded argv/release/CDP/login inventory, effect 0 | Repair root cause or create auth human task |
| Board truth | Task 2 | exact-key tenant/money projection tests | Never expose raw provider state |
| UI/API | Task 3 | authenticated API and responsive board tests | Never deploy mockup as product |
| WebMCP | Task 4 | discovered tools, real invocation, visible state change | Chrome protects Stage One if ChatGPT unavailable |
| Minimal human | Task 5 | one deduped task, answer ref, same job resumed | Fail if agent-capable work is handed off |
| External proof | Task 6 | Lancers proposal ID, effect 1, readback 1, replay 0 | Unknown enters reconciliation |
| Generality | Task 7 | Mercor boundary plus arbitrary URL without provider route | Effect stays blocked without adapter |
| Product liveness | Task 8 | three natural cycles, restart recovery, concurrent workrooms | Do not claim 24/7 |
| Submission | Task 9 | Devpost non-null `submitted_at` readback | Use website fallback before deadline |

## Execution Preflight

- [x] Read the winning spec, this plan, `.devpost-hackathon-state.json`, and `devpost-submission.md`.
- [x] Run `df -h /Users/anicca`; current free space is 11 GiB.
- [x] Run `git fetch origin`; create and lock `feat/webmcp-money-printer` from current `origin/main`.
- [x] Integrate the WebMCP docs commits, including `01c63546c`, into the implementation branch.
- [x] Re-read current official rules and draft form through the Devpost plugin; required fields, four criteria, deadline, free judging access, and video constraints match the spec.
- [x] Identify the Netlify source: `anicca-products`, site ID `d67537f0-21bd-477e-ac1a-323f7ec6d5cd`. Preserve `/lm`; `/money-printer` headers and deployed SHA remain Task 8 evidence.
- [ ] Run `~/loops/current/bin/lm-loop doctor` and `~/loops/current/bin/lm-loop status all`.
- [ ] Run baseline tests:

```bash
node --test \
  apps/life-manager/lib/general-agent-work-adapter.test.js \
  apps/life-manager/lib/hosted-goal-ingress.test.js \
  apps/life-manager/lib/marketplace-application-adapter.test.js \
  apps/life-manager/lib/marketplace-application-effect.test.js \
  apps/life-manager/lib/loop-adapter-registry.test.js
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q \
  apps/lancers-revenue/tests/test_lancers_adapter.py \
  apps/lancers-revenue/tests/test_lancers_status.py
```

Expected: all pass. Any failure becomes Task 1 evidence and is not waived.

Measured preflight: general-agent Node baseline is 27/27 pass using an existing locked dependency runtime. Clean `npm ci` is pending network recovery. Lancers baseline is 2 pass / 1 fail from a budget-enrichment expectation drift and remains Task 1 evidence. `lm-loop` launchctl readback is unavailable from the isolated Codex app-server, so no live owner status is inferred from that failure.

---

### Task 1: Restore Fresh Lancers Read-Only Truth

**Files:**
- Inspect: `skills/earn/lancers/scripts/status.py`
- Inspect: `skills/earn/lancers/scripts/application_tick.py`
- Inspect: `skills/earn/lancers/scripts/application_loop.py`
- Modify only the measured root-cause file above
- Test with its matching existing file under `apps/lancers-revenue/tests/`
- Update: `docs/superpowers/specs/2026-08-28-webmcp-challenge-winning-contract.md`

**Interfaces:**
- Consumes: installed Lancers label/argv/release, retained private browser profile, public search, exact CDP owner.
- Produces: authenticated read-only inventory with `observed_at`, opportunities, applications, identity hash, `source_complete`, `effect_count=0`, and evidence hash.

- [ ] Reconcile installed runtime before editing:

```bash
~/loops/current/bin/lm-loop status all | jq '.[] | select(.loop_id|test("lancers"))'
launchctl print "gui/$(id -u)/ai.anicca.lancers-revenue-browser"
launchctl print "gui/$(id -u)/ai.anicca.lancers-revenue-application"
```

- [ ] Run exact read-only entrypoint and focused tests:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q \
  apps/lancers-revenue/tests/test_lancers_status.py \
  apps/lancers-revenue/tests/test_lancers_adapter.py \
  apps/lancers-revenue/tests/test_application_loop_hol.py
python3 -m compileall -q skills/earn/lancers/scripts
```

- [ ] Add one failing regression for the measured code root cause. For stale auth, use:

```python
def test_discovery_reports_auth_required_with_zero_effect():
    result = run_discovery(query="software", limit=20, timeout=20, fetch_html=lambda **_: LOGIN_HTML)
    assert result["source_complete"] is False
    assert result["marketplace_effect_count"] == 0
    assert result["blocker"] == "authentication_required"
```

If root cause is release/argv drift, change no provider code; cut/apply current pushed main through `lm-loop`.

- [ ] Obtain two stable inventories: authenticated, source complete, effect 0, stable identity hash, opportunity count >0, owned tabs cleaned, no raw PII/cookie/credential.
- [ ] Run `git diff --check`, focused tests, compileall, update measured spec, commit `fix(lancers): restore read-only market truth`, and push.

---

### Task 2: Add the Provider-Neutral Money Printer Projection

**Files:**
- Create: `apps/life-manager/lib/money-printer-projection.js`
- Create: `apps/life-manager/lib/money-printer-projection.test.js`

**Interfaces:**

```js
projectMoneyPrinter({
  tenantId, observedAt, opportunities, runtimeJobs,
  generalReceipts, applicationReceipts, humanTasks, earnings,
}) -> {
  observed_at,
  metrics: { agents_working, needs_you, opportunity_value, paid_verified },
  columns: { found, working, needs_you, waiting, done, paid },
  activity,
}
```

- [x] Write RED tests:

```js
test("projection separates opportunity value from verified cash", () => {
  const view = projectMoneyPrinter(fixture());
  assert.equal(view.metrics.opportunity_value, "50000");
  assert.equal(view.metrics.paid_verified, "0");
});
test("projection rejects cross-tenant and unverified money", () => {
  assert.throws(() => projectMoneyPrinter(fixture({ foreignTenant: true })), /tenant/);
  assert.throws(() => projectMoneyPrinter(fixture({ unverifiedCash: true })), /verified/);
});
```

- [x] Run `node --test apps/life-manager/lib/money-printer-projection.test.js`; observed module-not-found RED.
- [x] Implement only a pure immutable exact-key adapter over existing runtime and earnings ledgers. Reuse their arithmetic and receipt validation; do not create a second ledger. Use reference-only IDs, integer money strings, HTTPS receipt links, and no provider-name branches.

```js
function projectMoneyPrinter(input = {}) {
  if (!input.tenantId || !Number.isFinite(Date.parse(input.observedAt))) {
    throw new Error("money printer scope invalid");
  }
  const scoped = rows => Object.freeze((rows || []).map(row => {
    if (!row || row.tenant_id !== input.tenantId) throw new Error("money printer tenant mismatch");
    return Object.freeze({ ...row });
  }));
  const rows = {
    opportunities: scoped(input.opportunities), runtimeJobs: scoped(input.runtimeJobs),
    humanTasks: scoped(input.humanTasks), earnings: scoped(input.earnings),
  };
  if (rows.earnings.some(row => row.verified !== true || !/^\d+$/.test(row.amount_minor))) {
    throw new Error("money printer earnings must be verified exact money");
  }
  return Object.freeze(buildMoneyPrinterView(rows, input.observedAt));
}
```

`buildMoneyPrinterView` is private to this file and maps canonical statuses only; it never reads provider names.
- [x] Run the focused test 2/2, commit `ec321cd1b` as `feat(life-manager): project money work`, and push.

---

### Task 3: Expose the Money Printer Through the Existing Panel

**Files:**
- Modify: `apps/life-manager/lib/panel-api.js`
- Modify: `apps/life-manager/lib/panel-api.test.js`
- Modify: `apps/life-manager/lib/panel-ui.js`
- Modify: `apps/life-manager/lib/panel-ui.test.js`
- Modify: `apps/life-manager/server.js`

**Interfaces:**
- Consumes: `projectMoneyPrinter()` and injected tenant-bound `moneyPrinterSource(scope)`.
- Produces: `GET /api/panel/money-printer` and `data-panel-section="money-printer"`.

- [x] Add focused API coverage for session scope, ignored request UID, tenant-bound source, POST 405, and no raw private fields.
- [x] Add UI tests:

```js
test("panel renders the Money Printer board", () => {
  const html = renderPanelPage({ csrf: "csrf-value" });
  assert.match(html, /data-panel-section="money-printer"/);
  assert.match(html, /Needs You/);
  assert.match(html, /Paid & verified/);
});
```

- [x] Run focused Panel tests and observe RED: API 404 and missing UI section.
- [x] Add the smallest API/UI section, reuse auth/session/CSRF, validate exact keys before rendering, and never copy static mock values.

```js
async function moneyPrinter(scope, opts = {}) {
  if (!scope || !scope.uid || typeof opts.moneyPrinterSource !== "function") {
    throw new Error("money printer source unavailable");
  }
  const input = await opts.moneyPrinterSource(scope);
  if (!input || input.tenantId !== scope.uid) throw new Error("scope mismatch");
  return projectMoneyPrinter(input);
}
```

Route `GET /api/panel/money-printer` through the same `sessionScope` and `sendPanelSection` boundary used by the existing sections.
- [x] Run projection and changed Panel tests 58/58; commit `7b82045eb` as `feat(life-manager): show Money Printer`; push.

Measured ruling: do not wire `server.js` to an empty fixture-like source. Task 5/7 must inject the real durable human-task/opportunity/runtime/receipt source before live deployment.

---

### Task 4: Register Focused WebMCP Site Tools

**Files:**
- Create: `apps/life-manager/lib/money-printer-webmcp.js`
- Create: `apps/life-manager/lib/money-printer-webmcp.test.js`
- Modify: `apps/life-manager/lib/panel-ui.js`
- Modify: `apps/life-manager/lib/panel-ui.test.js`

**Interfaces:**
- Produces `renderMoneyPrinterWebMcpScript({ csrf }) -> string`.
- Registers only `inspect_money_printer` in this task. Task 5 adds the two human-task tools; Task 7 adds opportunity/workroom/receipt tools after their server actions exist.

- [x] Add one focused test proving top-level imperative registration, exact `inspect_money_printer`, empty narrow schema, `readOnlyHint: true`, same-origin GET, and no credential-shaped strings.
- [x] Run `node --test apps/life-manager/lib/money-printer-webmcp.test.js`; observed module-not-found RED.
- [x] Implement generated browser script using `document.modelContext.registerTool()`, the same-origin Panel API, and structured results.

```js
const TOOL_SPECS = Object.freeze([
  ["inspect_money_printer", "GET", "/api/panel/money-printer", true],
]);

async function registerMoneyPrinterTools(modelContext, request) {
  for (const [name, method, endpoint, readOnly] of TOOL_SPECS) {
    await modelContext.registerTool({
      name,
      description: toolDescription(name),
      inputSchema: toolInputSchema(name),
      annotations: { readOnlyHint: readOnly },
      execute: input => request(method, endpoint, input),
    });
  }
}
```

`toolDescription` and `toolInputSchema` use an exact object keyed by the registered names; unknown names throw. Never register a tool before its same-origin endpoint and server domain action exist.
- [x] Run WebMCP and Panel UI tests 27/27; commit `9a68c5f9d` as `feat(webmcp): expose Money Printer tools`; push.

---

### Task 5: Make Needs You Durable and Resume the Same Work

**Files:**
- Create: `apps/life-manager/migrations/2026-08-29-lm-money-printer-human-tasks.sql`
- Create: `apps/life-manager/lib/money-printer-human-task.js`
- Create: `apps/life-manager/lib/money-printer-human-task.test.js`
- Modify: `apps/life-manager/lib/panel-api.js`
- Modify: `apps/life-manager/lib/panel-api.test.js`

**Interfaces:**
- `buildHumanTask({ tenantId, jobId, reasonCode, question, requiredFormat, resumeRef, contextRefs, humanBoundaryRef })` returns a stable SHA-256 task ID. `humanBoundaryRef` is the reference-only output of the model/policy judgment; deterministic code never classifies human-only work with keywords.
- `answerHumanTask({ scope, taskId, version, answerRef }, store)` atomically closes one task and returns the original `resume_ref`.
- Private answers live in the vault; the table stores only references.

- [x] Write focused Task 5A contract tests:

```js
test("one logical blocker creates one task and resumes one job", async () => {
  const first = buildHumanTask(input());
  const second = buildHumanTask(input());
  assert.equal(first.task_id, second.task_id);
  const result = await answerHumanTask({
    scope: tenantScope(), taskId: first.task_id, version: 1,
    answerRef: "vault-answer://tenant-1/answer-1",
  }, store());
  assert.equal(result.resume_ref, first.resume_ref);
});
```

Also test cross-tenant refusal, stale version conflict, replay no-op, secret rejection, and missing/noncanonical `humanBoundaryRef`. The model decides whether work is human-only; code requires the bound judgment receipt and performs only bookkeeping.

- [x] **Task 5A:** Add the domain module and migration constraints: `(uid, task_id)` primary key, status enum, version check, unique open `(uid, job_id, reason_code)`, RLS/service-role boundary, `waiting_human` runtime state, and atomic create/answer RPCs. Answer requeues the same `(uid, job_id)` and never creates another runtime job.
- [x] Run human-task test for module-not-found RED, then GREEN 4/4; commit `3f4ef9bdb`; DB apply remains Task 8 deployment work.
- [x] **Task 5B:** Implement task/answer functions, authenticated endpoints, and the two state-dependent WebMCP tools:

```text
GET  /api/panel/money-printer/human-task/next
POST /api/panel/money-printer/human-task/answer
```

POST requires session scope, CSRF, task ID, version, idempotency key, and vault answer reference. Success re-enqueues the original job reference; it never creates a second workroom.

```js
function buildHumanTask(input = {}) {
  const canonical = canonicalHumanTaskInput(input);
  const taskId = createHash("sha256").update(JSON.stringify(canonical)).digest("hex");
  return Object.freeze({ ...canonical, task_id: taskId, status: "open", version: 1 });
}

async function answerHumanTask(input, store) {
  const answer = validateHumanAnswer(input);
  const closed = await store.answerOnce(answer);
  if (!closed || closed.status !== "answered" || closed.answer_ref !== answer.answerRef) {
    throw new Error("human task answer not read back");
  }
  return Object.freeze({ task_id: closed.task_id, resume_ref: closed.resume_ref });
}
```

- [x] Run human-task, WebMCP, Panel API/UI focused tests 65/65 after fixing the registration Promise race; commits `4f01d717d` and `78b03fe56`; push. Migration apply/live resume remain Task 8.

---

### Task 6: Close One Real Lancers Application Receipt

**Files:**
- Reuse: `skills/earn/lancers/scripts/status.py`
- Reuse: `skills/earn/lancers/scripts/application_loop.py`
- Reuse: `skills/earn/lancers/scripts/application_tick.py`
- Reuse: `apps/life-manager/lib/marketplace-application-job.js`
- Reuse: `apps/life-manager/lib/marketplace-application-effect.js`
- Update: `docs/superpowers/specs/2026-08-28-webmcp-challenge-winning-contract.md`

**Interfaces:**
- Consumes: fresh inventory, model decision, `application-intent://sha256/...`, `authorization-receipt://sha256/...`.
- Produces: verified `application_receipt` with platform, opportunity identity, provider proposal ID, observed time, intent hash, and effect key.

- [ ] Give the model complete candidate evidence: listing, buyer evidence, budget, deadline, outcome, fees, execution cost, competition, profile proof, and risks. Add no price/keyword rule.
- [ ] If authority/private input is required, create one prepared Needs You task showing proposal, amount, due date, destination, and risks.
- [ ] Execute through the existing application effect kernel.

Acceptance:

```text
presend state=absent
immutable intent hash present
authorization bound to the same candidate
external effects=1
official proposal ID non-empty
post-readback state=present
canonical application receipt=1
same-intent replay external effects=0
```

- [ ] If submit/readback is unknown, use reconciliation. Never use another account, browser, agent, or click.
- [ ] Run all `apps/lancers-revenue/tests`, planner focus tests, and marketplace effect tests.
- [ ] Record only IDs/hashes/status in the spec. Commit `docs(webmcp): record Lancers application proof`; push.

---

### Task 7: Prove Mercor and Unknown-Market Generality Without New Brains

**Files:**
- Modify only if a measured gap exists: `apps/life-manager/lib/general-agent-work-adapter.js`
- Test: `apps/life-manager/lib/general-agent-work-adapter.test.js`
- Reuse: `apps/life-manager/lib/hosted-goal-ingress.js`
- Reuse: `skills/_shared/marketplace-core/tests/fixtures/mercor-full-chain.json`

**Interfaces:**
- Consumes: explicit goal containing a public opportunity URL and existing `general-agent.work` capability.
- Produces: `planned|completed|blocked` specialist receipt and reference-only next jobs, without provider routing.

- [ ] Add a generality test:

```js
test("unknown marketplace plans work instead of provider rejection", async () => {
  const adapter = createGeneralAgentWorkLoopAdapter({
    runBoundedSpecialist: async expected => ({
      tenant_id: expected.tenant_id, job_id: expected.job_id,
      goal_ref: expected.goal_ref, kind: "general_agent_work",
      execution_id: "execution-unknown-market-1", status: "planned",
      next_job_refs: ["runtime-job://tenant-1/adapter-required-1"],
    }),
  });
  const result = await adapter.execute(unknownMarketplaceJob());
  assert.equal(result.receipt.status, "planned");
});
```

Add a Mercor case producing a provider interview human task, and a URL case where research/artifact work continues while external effect remains blocked.

- [ ] Run general-agent and hosted-goal tests.
- [ ] Reuse current adapter if receipts already express the behavior. Never add `if provider === "mercor"` or a marketplace switch.
- [ ] Show one Dashboard with Lancers receipt, Mercor role→Needs You interview, and unknown URL→work plan→adapter required.
- [ ] Run general-agent, marketplace adapter, and registry tests. Commit only measured code/evidence; push.

---

### Task 8: Deploy and Prove a Complete Product

**Files:**
- Modify deployment config only if current config requires it
- Update: `README.md`
- Create: `docs/webmcp-judge-guide.md`
- Update: `docs/superpowers/specs/2026-08-28-webmcp-challenge-winning-contract.md`

**Interfaces:**
- Produces free judge URL, immutable deploy SHA, ChatGPT/Chrome evidence, three natural cycles, restart recovery, and resettable guest state.

- [ ] Deploy `/money-printer` and Railway from one pushed main SHA while preserving existing `/lm`. Preserve origin isolation and `tools` Permissions Policy; register tools at top level.
- [ ] Run clean-browser normal UI E2E: zero-login guest, no owner state, one Needs You flow, reset, mobile layout.
- [ ] Run ChatGPT in-app browser E2E with Sol/Terra: tool list, read call, write call, visible state change, recent activity, answer, same-work continuation, receipt.
- [ ] Run Chrome 149+ E2E with WebMCP testing enabled: schema parse, discovery, structured output, no iframe/declarative dependency.
- [ ] Keep one release running for 24 hours with three natural scout cycles, multiple opportunities, dedupe, two concurrent workrooms, restart recovery, and duplicate effect zero.
- [ ] Write `docs/webmcp-judge-guide.md` with one URL, one prompt, a 60-second path, Chrome fallback, reset, and limitations.
- [ ] Update README with architecture/tool table and exact post-August-25 changes.
- [ ] Run Money Printer, Panel, privacy, WebMCP, runtime adapter, and Lancers tests. Commit `docs(webmcp): add judge evidence`; push.

---

### Task 9: Freeze the Submission Packet and Submit

**Files:**
- Update: `devpost-submission.md`
- Update: `.devpost-hackathon-state.json`
- Create final Git tag after verification

**Interfaces:**
- Consumes final deploy/repo SHAs, Site tools evidence, screenshots, public YouTube URL, Lancers receipt, and liveness evidence.
- Produces Devpost project `1404362` with every required field and live `submitted_at` readback.

- [ ] Capture five real screenshots: full Dashboard, Site tools, selected workroom, Needs You, receipt/verified money. Never use the static mockup as proof.
- [ ] Record a public YouTube video under three minutes. Show working product in 15 seconds, tool call, real work, human task, continuation, Lancers receipt, multiple sources, and money truth. Add English audio/captions and no unlicensed media.
- [ ] Reconcile every sentence in `devpost-submission.md` to final evidence; delete unsupported claims.
- [ ] Fill tested clients, AI tools, existing-project changes, live URL, testing instructions, repo, video, learning, and career-value fields.
- [ ] Run final clean clone, license, live URL, video, secret/PII, and post-August-25 diff checks.
- [ ] Sync Devpost project `1404362` and read back `submitted_at: null` before confirmation.
- [ ] Present title, four answers, links, custom fields, video, and screenshots. Only exact `yes, submit` authorizes submission.
- [ ] Read back non-null `submitted_at` and public Hackathon URL.
- [ ] Commit the frozen packet, tag `webmcp-submission-2026`, push the tag, record deploy/Devpost receipts, and freeze through judging.

## Final Self-Review

- [ ] Every spec requirement maps to Tasks 1–9.
- [ ] No provider keyword decides feasibility, work, or quality.
- [ ] Every effect has authorization, intent, readback, and replay-zero.
- [ ] Every human task is genuinely human-only, deduped, and resumable.
- [ ] Guest and owner share code but not credentials/state/authority.
- [ ] Video shows live WebMCP, not the mockup.
- [ ] Lancers receipt is real; Mercor and unknown-market claims stop at measured states.
- [ ] Devpost stays unsubmitted until explicit final confirmation.
