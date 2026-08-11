"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { createBrowserHarnessAdapter } = require("./connector-browser-harness-adapter.js");
const { createConnectorActionCache } = require("./connector-action-cache.js");
const { runMinimalConnectorWake } = require("./connector-minimal-runner.js");
const {
  createProductionBrowserRail,
  createProductionCalendarReader,
  createMinimalProductionDependencies,
  createProductionProviderRouter,
} = require("./connector-minimal-production.js");

test("official production factory exposes the complete minimal wake dependency contract", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-production-deps-"));
  try {
    const browserRail = Object.freeze({ open() {}, navigate() {}, close() {} });
    const calendarReader = Object.freeze({ async readCalendarGaps() { return []; } });
    const providerRouter = Object.freeze({
      discoverCandidates() {}, runCachedAction() {}, runDirectAction() {}, runAgentFallback() {},
      readProviderState() {}, saveRepairedActions() {},
    });
    const evidenceChain = Object.freeze({ completeEvidence() {} });
    const operations = Object.freeze({ reportWake() {}, recordAction() {} });
    const dependencies = createMinimalProductionDependencies({
      repoRoot: "/private/repo",
      stateDir,
      wakeId: "wake-production-deps-1",
      calendarAccount: "private-account",
      gogKeyring: "private-keyring",
      telegramTarget: "private-target",
      tenantId: "dais-local",
      calendarId: "primary",
      lumaFormProfilePath: "/private/form-profile.json",
      lunaEvidenceDir: "/private/luna-evidence",
      browserRail,
      calendarReader,
      providerRouter,
      evidenceChain,
      operations,
      now: () => new Date("2026-08-07T08:30:00.000Z"),
    });

    assert.equal(dependencies.browserRail, browserRail);
    assert.deepEqual(Object.keys(dependencies).sort(), [
      "browserRail", "completeEvidence", "discoverCandidates", "now", "readCalendarGaps",
      "readProviderState", "recordAction", "reportWake", "runAgentFallback", "runCachedAction",
      "runDirectAction", "saveRepairedActions",
    ]);
    assert.deepEqual(await dependencies.readCalendarGaps(), await calendarReader.readCalendarGaps());
    assert.equal(dependencies.discoverCandidates, providerRouter.discoverCandidates);
    assert.equal(dependencies.completeEvidence, evidenceChain.completeEvidence);
    assert.equal(dependencies.reportWake, operations.reportWake);
    assert.equal(dependencies.now(), "2026-08-07T08:30:00.000Z");
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});

test("official production factory installs the Connpass workflow into the default router", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-production-connpass-"));
  const candidate = { provider: "connpass", event_ref: "connpass-event://event/401001", canonical_url: "https://tokyo.connpass.com/event/401001/" };
  const emptyWorkflow = { async discoverCandidates() { return []; }, async runDirectAction() {}, async readProviderState() { return { status: "absent" }; } };
  const connpassWorkflow = { ...emptyWorkflow, async discoverCandidates() { return [candidate]; } };
  try {
    const dependencies = createMinimalProductionDependencies({
      repoRoot: "/private/repo", stateDir, wakeId: "wake-production-connpass-1",
      calendarAccount: "private-account", gogKeyring: "private-keyring", telegramTarget: "private-target",
      lumaFormProfilePath: "/private/form-profile.json", lunaEvidenceDir: "/private/luna-evidence",
      browserRail: { open() {}, navigate() {}, close() {} },
      calendarReader: { async readCalendarGaps() { return []; } },
      lumaWorkflow: emptyWorkflow, connpassWorkflow,
      actionCache: { async replay() {}, saveVerifiedRepair() {} },
      browserHarness: { async runFallback() {}, async performAction() {} },
      evidenceChain: { async completeEvidence() {} },
      operations: { async reportWake() {}, async recordAction() {} },
    });
    assert.deepEqual(await dependencies.discoverCandidates("connpass", [], {}), [candidate]);
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});

test("official production factory persists the Connpass discovery audit from its default workflow", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-production-connpass-audit-"));
  const audits = [];
  const emptyWorkflow = {
    async discoverCandidates() { return []; },
    async runDirectAction() {},
    async readProviderState() { return { status: "absent" }; },
  };
  const operations = {
    async recordConnpassDiscoveryAudit(value) { audits.push(value); },
    async reportWake() {},
    async recordAction() {},
  };
  try {
    const dependencies = createMinimalProductionDependencies({
      repoRoot: "/private/repo", stateDir, wakeId: "wake-production-connpass-audit-1",
      calendarAccount: "private-account", gogKeyring: "private-keyring", telegramTarget: "private-target",
      lumaFormProfilePath: "/private/form-profile.json", lunaEvidenceDir: "/private/luna-evidence",
      browserRail: { open() {}, navigate() {}, close() {} },
      calendar: { ready() { return true; } },
      calendarReader: { async readCalendarGaps() { return []; } },
      lumaWorkflow: emptyWorkflow,
      actionCache: { async replay() {}, saveVerifiedRepair() {} },
      browserHarness: { async runFallback() {}, async performAction() {} },
      evidenceChain: { async completeEvidence() {} },
      operations,
      now: () => new Date("2026-08-10T08:30:00.000Z"),
    });
    const page = {
      current: "",
      async goto(url) { this.current = url; },
      async evaluate() { return []; },
    };

    assert.deepEqual(await dependencies.discoverCandidates("connpass", [], page), []);
    assert.deepEqual(audits, [{
      observed_count: 0,
      normalized_count: 0,
      window_count: 0,
      free_open_count: 0,
      calendar_free_count: 0,
    }]);
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});

test("official production factory installs Peatix audit and keeps attendee profile lazy", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-production-peatix-audit-"));
  const audits = [], profile = { name: "Private Name", email: "private@example.test", accept_organizer_privacy: true };
  let profileReads = 0;
  const emptyWorkflow = { async discoverCandidates() { return []; }, async runDirectAction() {}, async readProviderState() { return { status: "absent" }; } };
  try {
    const dependencies = createMinimalProductionDependencies({
      repoRoot: "/private/repo", stateDir, wakeId: "wake-production-peatix-1",
      calendarAccount: "private-account", gogKeyring: "private-keyring", telegramTarget: "private-target",
      lumaFormProfilePath: "/private/form-profile.json", lunaEvidenceDir: "/private/luna-evidence",
      browserRail: { open() {}, navigate() {}, close() {} }, calendar: { ready() { return true; } },
      calendarReader: { async readCalendarGaps() { return []; } }, lumaWorkflow: emptyWorkflow,
      connpassWorkflow: emptyWorkflow, browserHarness: { async runFallback() {}, async performAction() {} },
      actionCache: { async replay() {}, saveVerifiedRepair() {} }, evidenceChain: { async completeEvidence() {} },
      operations: { async recordPeatixDiscoveryAudit(value) { audits.push(value); }, async reportWake() {}, async recordAction() {} },
      get peatixAttendeeProfile() { profileReads += 1; return profile; },
      now: () => new Date("2026-08-10T08:30:00.000Z"),
    });
    const page = {
      waitForResponse() {
        return Promise.resolve({
          url() { return "https://peatix.com/search/events?p=1&size=20"; },
          ok() { return true; }, async json() { return { json_data: { page: 1, events: [] } }; },
        });
      },
      async goto() {},
    };
    assert.deepEqual(await dependencies.discoverCandidates("peatix", [], page), []);
    assert.deepEqual(audits, [{ observed_count: 0, normalized_count: 0, window_count: 0, free_open_count: 0, calendar_free_count: 0 }]);
    const candidate = {
      provider: "peatix", event_ref: "peatix-event://event/1", canonical_url: "https://peatix.com/event/1",
      title: "Public Event", starts_at: "2026-08-10T01:00:00.000Z", ends_at: "2026-08-10T02:00:00.000Z",
      registration_status: "available", ticket_price_status: "free", ticket_price_minor: 0, ticket_id: "9",
    };
    const direct = await dependencies.runDirectAction({ provider: "peatix", candidate, page: {} });
    assert.equal(direct.status, "failed");
    assert.equal(profileReads, 1);
    assert.doesNotMatch(JSON.stringify({ audits, direct }), /Private Name|private@example\.test/);
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});

test("official factory composes the default Peatix Harness with the attendee profile", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-production-peatix-harness-")); let filled = null; let reads = 0;
  const profile = { name: "Private Name", email: "private@example.test", family_name_kana: "サクラ", given_name_kana: "テスト", accept_organizer_privacy: true };
  const emptyWorkflow = { async discoverCandidates() { return []; }, async runDirectAction() { return { status: "failed" }; }, async readProviderState() { return { status: filled ? "pending" : "absent" }; } };
  const element = { tagName: "INPUT", type: "text", required: true, dataset: {}, labels: [{ innerText: "Name" }], innerText: "", getAttribute() { return ""; } };
  const page = { locator(selector) {
    if (selector === "input, textarea, select, button, a[role=button], a#confirm-button") return { async evaluateAll(callback) { return callback([element]); } };
    return { async count() { return 1; }, async fill(value) { filled = value; } };
  } };
  try {
    const dependencies = createMinimalProductionDependencies({ repoRoot: "/private/repo", stateDir, wakeId: "wake-production-peatix-harness-1", calendarAccount: "private-account", gogKeyring: "private-keyring", telegramTarget: "private-target", lumaFormProfilePath: "/private/form-profile.json", lunaEvidenceDir: "/private/luna-evidence", calendar: { ready() { return true; } }, calendarReader: { async readCalendarGaps() { return []; } }, lumaWorkflow: emptyWorkflow, connpassWorkflow: emptyWorkflow, peatixWorkflow: emptyWorkflow, peatixAttendeeProfile: profile, proposeAction: async () => ({ purpose: "fill", method: "ax_fill", control: "control_1" }), actionCache: { async replay() { return { status: "cache_miss" }; }, saveVerifiedRepair() {} }, evidenceChain: { async completeEvidence() {} }, operations: { async reportWake() {}, async recordAction() {} }, now: () => new Date("2026-08-10T08:30:00.000Z") });
    const result = await dependencies.runAgentFallback({ provider: "peatix", candidate: { event_ref: "peatix-event://event/1" }, page, pageWebsocket: "ws://127.0.0.1:9222/devtools/page/OWNEDTARGET1", maxSteps: 1, expectedState: "registered_or_pending" });
    assert.equal(result.status, "completed"); assert.equal(filled, profile.name); assert.equal(JSON.stringify(result).includes(profile.email), false); reads += 1;
  } finally { fs.rmSync(stateDir, { recursive: true, force: true }); }
  assert.equal(reads, 1);
});

test("production provider router keeps Luma cache direct fallback and readback on one page", async () => {
  const calls = [];
  const page = Object.freeze({ page_id: "owned-page-1" });
  const candidate = Object.freeze({
    provider: "luma",
    event_ref: "luma-event://event/one",
    canonical_url: "https://luma.com/one",
  });
  const calendar = Object.freeze([{ kind: "timed", start_at: "2026-08-10T10:00:00.000Z", end_at: "2026-08-10T11:00:00.000Z" }]);
  const lumaWorkflow = {
    async discoverCandidates(input) { calls.push(["discover", input]); return [candidate]; },
    async runDirectAction(input) { calls.push(["direct", input]); return { status: "completed" }; },
    async readProviderState(input) { calls.push(["readback", input]); return { status: "registered" }; },
  };
  const actionCache = {
    async replay(input) {
      calls.push(["cache-replay", input]);
      return { status: "cache_miss" };
    },
    saveVerifiedRepair(input) {
      calls.push(["cache-save", input]);
      return { status: "saved", cache_entry_id: "cache-entry-1" };
    },
  };
  const browserHarness = {
    async runFallback(input) { calls.push(["fallback", input]); return { status: "failed" }; },
  };
  let performed; const performAction = async (input) => { performed = input; return { status: "success" }; };
  const router = createProductionProviderRouter({
    lumaWorkflow,
    connpassWorkflow: {
      async discoverCandidates() { return []; },
      async runDirectAction() { return { status: "failed" }; },
      async readProviderState() { return { status: "unavailable" }; },
    },
    actionCache,
    browserHarness,
    performAction,
    now: () => new Date("2026-08-07T08:30:00.000Z"),
  });

  assert.deepEqual(await router.discoverCandidates("luma", calendar, page), [candidate]);
  assert.deepEqual(await router.discoverCandidates("connpass", calendar, page), []);
  assert.deepEqual(await router.runCachedAction({ provider: "luma", candidate, page }), { status: "cache_miss" });
  assert.deepEqual(await router.runDirectAction({ provider: "luma", candidate, page }), { status: "completed" });
  assert.deepEqual(await router.runAgentFallback({
    provider: "luma",
    candidate,
    page,
    pageWebsocket: "ws://127.0.0.1:9222/devtools/page/OWNEDTARGET1",
    maxSteps: 10,
    expectedState: "registered_or_pending",
  }), { status: "failed" });
  assert.deepEqual(await router.readProviderState({ provider: "luma", candidate, page }), { status: "registered" });
  assert.deepEqual(await router.saveRepairedActions({
    provider: "luma",
    candidate,
    page,
    providerState: { status: "registered" },
    repairedActions: [{ purpose: "submit", method: "ax_click", control: "register_button" }],
  }), { status: "saved", cache_entry_id: "cache-entry-1" });

  const replay = calls.find(([name]) => name === "cache-replay")[1];
  assert.equal(replay.provider, "luma");
  assert.equal(replay.workflowVersion, "luma_registration_v1");
  assert.equal(replay.pageState, "registration_page_v1");
  assert.equal(replay.expectedEffect, "registered_or_pending");
  assert.equal(replay.page, page);
  await replay.performAction({ purpose: "fill", method: "ax_fill", control: "control_1" }); assert.equal(performed.provider, "luma");
  assert.equal(typeof replay.readExpectedState, "function");
  assert.equal(calls.find(([name]) => name === "discover")[1].calendar, calendar);
  assert.equal(calls.find(([name]) => name === "fallback")[1].page, page);
  assert.equal(calls.find(([name]) => name === "fallback")[1].candidate, candidate);
  assert.equal(calls.find(([name]) => name === "cache-save")[1].observedAt, "2026-08-07T08:30:00.000Z");
});

test("production provider router continues from Luma to Connpass on the same page", async () => {
  const calls = []; let performed;
  const page = Object.freeze({ page_id: "owned-page-1" });
  const candidate = Object.freeze({
    provider: "connpass",
    event_ref: "connpass-event://event/401001",
    canonical_url: "https://tokyo-builders.connpass.com/event/401001/",
  });
  const workflow = {
    async discoverCandidates(input) { calls.push(["discover", input]); return [candidate]; },
    async runDirectAction(input) { calls.push(["direct", input]); return { status: "completed" }; },
    async readProviderState(input) { calls.push(["readback", input]); return { status: "pending" }; },
  };
  const actionCache = {
    async replay(input) { calls.push(["cache", input]); return { status: "cache_miss" }; },
    saveVerifiedRepair(input) { calls.push(["save", input]); return { status: "saved" }; },
  };
  const browserHarness = {
    async runFallback(input) { calls.push(["fallback", input]); return { status: "failed" }; },
  };
  const router = createProductionProviderRouter({
    lumaWorkflow: workflow,
    connpassWorkflow: workflow,
    actionCache,
    browserHarness,
    async performAction(input) { performed = input; return { status: "success" }; },
    now: () => new Date("2026-08-07T08:30:00.000Z"),
  });

  assert.deepEqual(await router.discoverCandidates("connpass", [], page), [candidate]);
  await router.runCachedAction({ provider: "connpass", candidate, page });
  await router.runDirectAction({ provider: "connpass", candidate, page });
  await router.readProviderState({ provider: "connpass", candidate, page });

  const cached = calls.find(([name]) => name === "cache")[1];
  assert.equal(cached.provider, "connpass");
  assert.equal(cached.workflowVersion, "connpass_registration_v1");
  assert.equal(cached.pageState, "registration_page_v1");
  assert.equal(cached.page, page);
  await cached.performAction({ purpose: "fill", method: "ax_fill", control: "control_1" }); assert.equal(performed.provider, "connpass");
  assert.equal(calls.filter(([name]) => name === "discover")[0][1].page, page);
});

test("production provider router routes Peatix cache direct and readback on one page", async () => {
  const calls = [];
  const page = Object.freeze({ page_id: "owned-page-peatix" });
  const candidate = Object.freeze({ provider: "peatix", event_ref: "peatix-event://event/1", canonical_url: "https://peatix.com/event/1" });
  const workflow = {
    async discoverCandidates(input) { calls.push(["discover", input]); return [candidate]; },
    async runDirectAction(input) { calls.push(["direct", input]); return { status: "completed" }; },
    async readProviderState(input) { calls.push(["readback", input]); return { status: "registered" }; },
  };
  const actionCache = {
    async replay(input) { calls.push(["cache", input]); return { status: "cache_miss" }; },
    saveVerifiedRepair(input) { calls.push(["save", input]); return { status: "saved" }; },
  };
  const router = createProductionProviderRouter({
    lumaWorkflow: workflow, connpassWorkflow: workflow, peatixWorkflow: workflow, actionCache,
    browserHarness: { async runFallback() { return { status: "failed" }; } },
    async performAction() { return { status: "success" }; }, now: () => new Date("2026-08-10T08:30:00.000Z"),
  });

  assert.deepEqual(await router.discoverCandidates("peatix", [], page), [candidate]);
  await router.runCachedAction({ provider: "peatix", candidate, page });
  await router.runDirectAction({ provider: "peatix", candidate, page });
  await router.readProviderState({ provider: "peatix", candidate, page });
  assert.throws(() => router.discoverCandidates("meetup", [], page));

  const cached = calls.find(([name]) => name === "cache")[1];
  assert.equal(cached.provider, "peatix");
  assert.equal(cached.workflowVersion, "peatix_registration_v1");
  assert.equal(cached.pageState, "registration_page_v1");
  assert.equal(cached.page, page);
  assert.equal(calls.find(([name]) => name === "direct")[1].page, page);
  assert.equal(calls.find(([name]) => name === "readback")[1].page, page);
  assert.doesNotMatch(JSON.stringify(cached), /Private Name|private@example\.test/);
});

test("official production factory routes Meetup after Peatix on the same page", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-production-meetup-"));
  const page = Object.freeze({ page_id: "owned-page-meetup" });
  const candidate = Object.freeze({
    provider: "meetup", event_ref: "meetup-event://event/315756352",
    canonical_url: "https://www.meetup.com/tokyo-builders/events/315756352/",
  });
  const emptyWorkflow = { async discoverCandidates() { return []; }, async runDirectAction() { return { status: "failed" }; }, async readProviderState() { return { status: "absent" }; } };
  const meetupWorkflow = {
    async discoverCandidates(input) { assert.equal(input.page, page); return [candidate]; },
    async runDirectAction(input) { assert.equal(input.page, page); return { status: "failed", safe_reason: "meetup_direct_requires_harness" }; },
    async readProviderState(input) { assert.equal(input.page, page); return { status: "registered" }; },
  };
  try {
    const dependencies = createMinimalProductionDependencies({
      repoRoot: "/private/repo", stateDir, wakeId: "wake-production-meetup-1",
      calendarAccount: "private-account", gogKeyring: "private-keyring", telegramTarget: "private-target",
      lumaFormProfilePath: "/private/form-profile.json", lunaEvidenceDir: "/private/luna-evidence",
      browserRail: { open() {}, navigate() {}, close() {} }, calendar: { ready() { return true; } },
      calendarReader: { async readCalendarGaps() { return []; } }, lumaWorkflow: emptyWorkflow,
      connpassWorkflow: emptyWorkflow, peatixWorkflow: emptyWorkflow, meetupWorkflow,
      browserHarness: { async runFallback(input) { assert.equal(input.page, page); return { status: "completed" }; }, async performAction() {} },
      actionCache: { async replay() { return { status: "cache_miss" }; }, saveVerifiedRepair() {} },
      evidenceChain: { async completeEvidence() {} }, operations: { async reportWake() {}, async recordAction() {} },
    });
    assert.deepEqual(await dependencies.discoverCandidates("meetup", [], page), [candidate]);
    assert.deepEqual(await dependencies.runDirectAction({ provider: "meetup", candidate, page }), { status: "failed", safe_reason: "meetup_direct_requires_harness" });
    assert.deepEqual(await dependencies.runAgentFallback({ provider: "meetup", candidate, page }), { status: "completed" });
    assert.deepEqual(await dependencies.readProviderState({ provider: "meetup", candidate, page }), { status: "registered" });
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});

test("production provider router routes Doorkeeper through every action path without private cache metadata", async () => {
  const calls = [], page = Object.freeze({ page_id: "owned-page-doorkeeper" });
  const calendar = Object.freeze([{ kind: "timed", start_at: "2026-08-11T10:00:00.000Z", end_at: "2026-08-11T11:00:00.000Z" }]);
  const candidate = Object.freeze({ provider: "doorkeeper", event_ref: "doorkeeper-event://event/1001", canonical_url: "https://tokyo-builders.doorkeeper.jp/events/1001", attendee_name: "Private Name", attendee_email: "private@example.test" });
  const workflow = {
    async discoverCandidates(input) { calls.push(["discover", input]); return [candidate]; },
    async runDirectAction(input) { calls.push(["direct", input]); return { status: "failed", safe_reason: "doorkeeper_direct_requires_harness" }; },
    async readProviderState(input) { calls.push(["readback", input]); return { status: "registered" }; },
  };
  const actionCache = { async replay(input) { calls.push(["cache", input]); return { status: "cache_miss" }; }, saveVerifiedRepair(input) { calls.push(["save", input]); return { status: "saved" }; } };
  let performed;
  const router = createProductionProviderRouter({
    lumaWorkflow: workflow, connpassWorkflow: workflow, doorkeeperWorkflow: workflow, actionCache,
    browserHarness: { async runFallback(input) { calls.push(["fallback", input]); return { status: "failed" }; } },
    async performAction(input) { performed = input; return { status: "success" }; },
    now: () => new Date("2026-08-11T08:30:00.000Z"),
  });

  assert.deepEqual(await router.discoverCandidates("doorkeeper", calendar, page), [candidate]);
  assert.deepEqual(await router.runCachedAction({ provider: "doorkeeper", candidate, page }), { status: "cache_miss" });
  assert.deepEqual(await router.runDirectAction({ provider: "doorkeeper", candidate, page }), { status: "failed", safe_reason: "doorkeeper_direct_requires_harness" });
  assert.deepEqual(await router.runAgentFallback({ provider: "doorkeeper", candidate, page, pageWebsocket: "ws://page", maxSteps: 1, expectedState: "registered_or_pending" }), { status: "failed" });
  assert.deepEqual(await router.readProviderState({ provider: "doorkeeper", candidate, page }), { status: "registered" });
  assert.deepEqual(await router.saveRepairedActions({ provider: "doorkeeper", candidate, page, providerState: { status: "registered" }, repairedActions: [{ purpose: "submit", method: "ax_click", control: "register" }] }), { status: "saved" });

  const replay = calls.find(([name]) => name === "cache")[1];
  assert.deepEqual(Object.keys(replay).sort(), ["expectedEffect", "page", "performAction", "provider", "readExpectedState", "workflowVersion", "pageState"].sort());
  assert.deepEqual({ provider: replay.provider, version: replay.workflowVersion, pageState: replay.pageState, effect: replay.expectedEffect, page: replay.page }, { provider: "doorkeeper", version: "doorkeeper_registration_v1", pageState: "registration_page_v1", effect: "registered_or_pending", page });
  await replay.performAction({ purpose: "fill", method: "ax_fill", control: "field" }); assert.equal(performed.provider, "doorkeeper");
  assert.deepEqual(await replay.readExpectedState({ page }), { status: "registered" });
  assert.deepEqual({ discoverPage: calls.find(([name]) => name === "discover")[1].page, discoverCalendar: calls.find(([name]) => name === "discover")[1].calendar, directPage: calls.find(([name]) => name === "direct")[1].page, readbackPage: calls.find(([name]) => name === "readback")[1].page, fallbackPage: calls.find(([name]) => name === "fallback")[1].page, fallbackCandidate: calls.find(([name]) => name === "fallback")[1].candidate }, { discoverPage: page, discoverCalendar: calendar, directPage: page, readbackPage: page, fallbackPage: page, fallbackCandidate: candidate });
  const saved = calls.find(([name]) => name === "save")[1];
  assert.deepEqual(Object.keys(saved).sort(), ["actions", "expectedEffect", "observedAt", "pageState", "provider", "providerState", "workflowVersion"].sort());
  assert.deepEqual({ provider: saved.provider, version: saved.workflowVersion, pageState: saved.pageState, effect: saved.expectedEffect }, { provider: "doorkeeper", version: "doorkeeper_registration_v1", pageState: "registration_page_v1", effect: "registered_or_pending" });
  assert.doesNotMatch(JSON.stringify({ replay, saved }), /Private Name|private@example\.test/);
});

test("official production factory routes an injected Doorkeeper workflow without opening a browser rail", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-production-doorkeeper-"));
  const page = Object.freeze({ page_id: "injected-doorkeeper-page" }), calendar = Object.freeze([]);
  const candidate = Object.freeze({ provider: "doorkeeper", event_ref: "doorkeeper-event://event/1002", canonical_url: "https://tokyo-builders.doorkeeper.jp/events/1002" });
  const emptyWorkflow = { async discoverCandidates() { return []; }, async runDirectAction() { return { status: "failed" }; }, async readProviderState() { return { status: "absent" }; } };
  let discoveryInput; const doorkeeperWorkflow = { ...emptyWorkflow, async discoverCandidates(input) { discoveryInput = input; return [candidate]; } }; const railCalls = [];
  try {
    const dependencies = createMinimalProductionDependencies({
      repoRoot: "/private/repo", stateDir, wakeId: "wake-production-doorkeeper-1", calendarAccount: "private-account", gogKeyring: "private-keyring", telegramTarget: "private-target",
      lumaFormProfilePath: "/private/form-profile.json", lunaEvidenceDir: "/private/luna-evidence", calendar: { ready() { return true; } }, calendarReader: { async readCalendarGaps() { return []; } },
      browserRail: { open() { railCalls.push("open"); }, navigate() { railCalls.push("navigate"); }, close() { railCalls.push("close"); } },
      lumaWorkflow: emptyWorkflow, connpassWorkflow: emptyWorkflow, peatixWorkflow: emptyWorkflow, meetupWorkflow: emptyWorkflow, doorkeeperWorkflow,
      actionCache: { async replay() {}, saveVerifiedRepair() {} }, browserHarness: { async runFallback() {}, async performAction() {} }, evidenceChain: { async completeEvidence() {} }, operations: { async reportWake() {}, async recordAction() {} },
    });
    assert.deepEqual(await dependencies.discoverCandidates("doorkeeper", calendar, page), [candidate]);
    assert.equal(discoveryInput.page, page); assert.equal(discoveryInput.calendar, calendar); assert.deepEqual(railCalls, []);
  } finally { fs.rmSync(stateDir, { recursive: true, force: true }); }
});

test("official production factory wires the default Doorkeeper Harness readback without browser effects", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-production-doorkeeper-default-harness-")); let reads = 0; let railCalls = 0; let clicks = 0;
  const candidate = { provider: "doorkeeper", event_ref: "doorkeeper-event://event/1003", canonical_url: "https://tokyo-builders.doorkeeper.jp/events/1003" };
  const form = { id: "new_event_registration" };
  const element = (overrides) => ({ tagName: "A", type: "", id: "", name: "", value: "", innerText: "", textContent: "", labels: [], required: false, disabled: false, hidden: false, isConnected: true, style: {}, rect: { width: 120, height: 32 }, dataset: {}, form: null, parentElement: null, getAttribute(name) { return this[name] ?? null; }, getBoundingClientRect() { return this.rect; }, closest() { return null; }, ...overrides });
  const elements = [element({ href: "#new_registration_modal", innerText: "申し込む", textContent: "申し込む" }), element({ tagName: "INPUT", type: "email", id: "event_registration_email", name: "event_registration[email]", value: "private@example.test", required: true, form }), element({ tagName: "INPUT", type: "submit", name: "commit", value: "申し込む", form })];
  const page = { url() { return candidate.canonical_url; }, locator(selector) { return selector.startsWith("input, textarea") ? { async evaluateAll(callback, context) { return callback(elements, context); } } : { async count() { return 0; }, async click() { clicks += 1; } }; } };
  const emptyWorkflow = { async discoverCandidates() { return []; }, async runDirectAction() { return { status: "failed" }; }, async readProviderState() { return { status: "absent" }; } };
  const doorkeeperWorkflow = { ...emptyWorkflow, async readProviderState() { reads += 1; return { status: "registered" }; } };
  try {
    const dependencies = createMinimalProductionDependencies({
      repoRoot: "/private/repo", stateDir, wakeId: "wake-production-doorkeeper-default-1", calendarAccount: "private-account", gogKeyring: "private-keyring", telegramTarget: "private-target",
      lumaFormProfilePath: "/private/form-profile.json", lunaEvidenceDir: "/private/luna-evidence", calendar: { ready() { return true; } }, calendarReader: { async readCalendarGaps() { return []; } },
      browserRail: { open() { railCalls += 1; }, navigate() { railCalls += 1; }, close() { railCalls += 1; } }, lumaWorkflow: emptyWorkflow, connpassWorkflow: emptyWorkflow, peatixWorkflow: emptyWorkflow, meetupWorkflow: emptyWorkflow, doorkeeperWorkflow,
      proposeAction: async ({ observation }) => ({ control: observation.controls[observation.controls.length - 1].control }), actionCache: { async replay() {}, saveVerifiedRepair() {} }, evidenceChain: { async completeEvidence() {} }, operations: { async reportWake() {}, async recordAction() {} },
    });
    const result = await dependencies.runAgentFallback({ provider: "doorkeeper", candidate, page, pageWebsocket: "ws://127.0.0.1:9222/devtools/page/DOORKEEPERFACTORY1", maxSteps: 1, expectedState: "registered_or_pending" });
    assert.equal(result.status, "completed"); assert.deepEqual(result.provider_state, { status: "registered" }); assert.equal(reads, 1); assert.equal(railCalls, 0); assert.equal(clicks, 0);
  } finally { fs.rmSync(stateDir, { recursive: true, force: true }); }
});

test("production calendar reader uses gog for exactly fourteen Tokyo calendar days", async () => {
  const calls = [];
  const calendar = Object.freeze({ kind: "gog", ready: () => true });
  const verifiedInventory = Object.freeze({
    busy_inventory_id: "google-calendar-busy-inventory:test",
    busy_intervals: Object.freeze([
      Object.freeze({
        kind: "timed",
        start_at: "2026-08-10T10:00:00.000Z",
        end_at: "2026-08-10T11:00:00.000Z",
      }),
    ]),
  });
  const reader = createProductionCalendarReader({
    gogBin: "/usr/local/bin/gog",
    account: "private-account",
    keyring: "private-keyring",
    now: () => new Date("2026-08-07T08:30:00.000Z"),
    makeCalendar(input) {
      calls.push(["make-calendar", input]);
      return calendar;
    },
    async inspectBusyInventory(input) {
      calls.push(["inspect", input]);
      return verifiedInventory;
    },
    isVerifiedBusyInventory(value) { return value === verifiedInventory; },
  });

  const intervals = await reader.readCalendarGaps();

  assert.deepEqual(intervals, verifiedInventory.busy_intervals);
  assert.equal(calls[0][0], "make-calendar");
  assert.deepEqual(calls[0][1], {
    bin: "/usr/local/bin/gog",
    account: "private-account",
    keyring: "private-keyring",
  });
  assert.equal(calls[1][0], "inspect");
  assert.equal(calls[1][1].calendar, calendar);
  assert.equal(calls[1][1].timeZone, "Asia/Tokyo");
  assert.equal(calls[1][1].timeMin, "2026-08-06T15:00:00.000Z");
  assert.equal(calls[1][1].timeMax, "2026-08-20T15:00:00.000Z");
  assert.equal(calls[1][1].now, "2026-08-07T08:30:00.000Z");
});

test("production browser rail owns exactly one :9222 target without closing the browser", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-production-rail-"));
  const calls = [];
  const page = {
    async goto(url, options) { calls.push(["goto", url, options]); },
  };
  const browser = {
    close() { calls.push(["browser-close"]); },
  };
  const controller = {
    async create() {
      calls.push(["target-create"]);
      return Object.freeze({
        target_id: "OWNEDTARGET1",
        page_websocket: "ws://127.0.0.1:9222/devtools/page/OWNEDTARGET1",
        page,
      });
    },
    async close(targetId) { calls.push(["target-close", targetId]); return true; },
    async probe() { return true; },
  };
  const owner = {
    async claimExact(input) {
      calls.push(["claim", input]);
      return Object.freeze({
        schema_version: 1,
        owner_token: "owner-token-production-rail",
        generation: 1,
        target_id: input.targetId,
        page_websocket: input.pageWebsocket,
        canonical_url: "https://luma.com/tokyo?k=p",
        claimed_at: "2026-08-07T02:00:00.000Z",
      });
    },
    async probe() { calls.push(["probe"]); return true; },
    async heartbeat() { calls.push(["heartbeat"]); return true; },
    async release(receipt) { calls.push(["release", receipt.target_id]); return true; },
  };

  try {
    const rail = createProductionBrowserRail({
      stateDir,
      connectOverCDP: async (endpoint) => {
        calls.push(["connect", endpoint]);
        return browser;
      },
      createTargetController: (input) => {
        assert.equal(input.browser, browser);
        return controller;
      },
      createTargetOwnership: ({ ownerToken }) => {
        assert.equal(ownerToken, "owner-token-production-rail");
        return owner;
      },
      makeSessionId: () => "session-production-rail-1",
    });

    const owned = await rail.open({ ownerToken: "owner-token-production-rail" });
    await rail.navigate(owned, "https://luma.com/event-one");
    await rail.close(owned);

    assert.equal(owned.page, page);
    assert.equal(owned.target_id, "OWNEDTARGET1");
    assert.equal(calls.filter(([name]) => name === "connect").length, 1);
    assert.equal(calls.filter(([name]) => name === "target-create").length, 1);
    assert.equal(calls.filter(([name]) => name === "claim").length, 1);
    assert.equal(calls.filter(([name]) => name === "goto").length, 1);
    assert.equal(calls.filter(([name]) => name === "release").length, 1);
    assert.equal(calls.filter(([name]) => name === "target-close").length, 0);
    assert.equal(calls.filter(([name]) => name === "browser-close").length, 0);
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});

test("composed cached action self-heal repairs one stale submit and replays it on the next wake", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-production-self-heal-"));
  const cachePath = path.join(stateDir, "action-cache.json");
  const observedAt = "2026-08-11T08:30:00.000Z";
  const cacheKey = {
    provider: "luma", workflowVersion: "luma_registration_v1", pageState: "registration_page_v1", expectedEffect: "registered_or_pending",
  };
  const staleAction = { purpose: "submit", method: "ax_click", control: "stale_register_button" };
  const replacementAction = { purpose: "submit", method: "ax_click", control: "replacement_register_button" };
  const seededCache = createConnectorActionCache({ path: cachePath });
  const page = { registrationState: "absent" };
  const candidate = Object.freeze({ provider: "luma", event_ref: "luma-event://event/self-heal", canonical_url: "https://luma.com/self-heal" });
  const events = [], touchedPages = [], cacheAttempts = [], reports = [];
  let directCalls = 0; let fallbackCalls = 0; let proposerCalls = 0; let harnessActionCalls = 0; let harnessReadbackCalls = 0; let saveCalls = 0; let evidenceCalls = 0; let openCalls = 0; let closeCalls = 0;
  await seededCache.saveVerifiedRepair({ ...cacheKey, providerState: { status: "registered" }, actions: [staleAction], observedAt });
  assert.deepEqual(seededCache.read(cacheKey).actions, [staleAction]);
  assert.equal(fs.statSync(cachePath).mode & 0o777, 0o600);

  const touch = (suppliedPage) => { touchedPages.push(suppliedPage); assert.equal(suppliedPage, page); };
  const applyAction = async (source, input) => {
    touch(input.page);
    const control = input.action.control;
    cacheAttempts.push(`${source}:${control}`);
    events.push(`${source}:${control}`);
    if (control === staleAction.control) return { status: "failed" };
    if (control === replacementAction.control) { page.registrationState = "registered"; return { status: "success" }; }
    return { status: "failed" };
  };
  const workflow = {
    async discoverCandidates({ page: suppliedPage }) { touch(suppliedPage); return [candidate]; },
    async runDirectAction({ page: suppliedPage }) { touch(suppliedPage); directCalls += 1; events.push("direct"); return { status: "failed", safe_reason: "direct_action_failed" }; },
    async readProviderState({ page: suppliedPage }) { touch(suppliedPage); const status = page.registrationState; events.push(`parent:${status}`); return { status }; },
  };
  const browserHarness = createBrowserHarnessAdapter({
    async observePage({ page: suppliedPage, target_id }) { touch(suppliedPage); assert.equal(target_id, "SELFHEALTHTARGET"); return { controls: [staleAction.control, replacementAction.control] }; },
    async proposeAction({ step, target_id }) { proposerCalls += 1; assert.equal(step, 1); assert.equal(target_id, "SELFHEALTHTARGET"); return replacementAction; },
    async performAction(input) { harnessActionCalls += 1; return applyAction("harness", input); },
    async readExpectedState({ page: suppliedPage }) { touch(suppliedPage); harnessReadbackCalls += 1; events.push(`harness:${page.registrationState}`); return { status: page.registrationState }; },
  });
  const realCache = createConnectorActionCache({ path: cachePath });
  const actionCache = {
    replay: realCache.replay,
    saveVerifiedRepair(input) { saveCalls += 1; assert.equal(page.registrationState, "registered"); assert.deepEqual(input.actions, [replacementAction]); events.push("cache-save"); return realCache.saveVerifiedRepair(input); },
  };
  const router = createProductionProviderRouter({
    lumaWorkflow: workflow,
    connpassWorkflow: { async discoverCandidates() { return []; }, async runDirectAction() { return { status: "failed" }; }, async readProviderState() { return { status: "absent" }; } },
    actionCache,
    browserHarness,
    async performAction(input) { return applyAction("cache", input); },
    now: () => new Date(observedAt),
  });
  const dependencies = {
    now: () => observedAt,
    browserRail: {
      async open() { openCalls += 1; return { session_id: "session-self-heal", target_id: "SELFHEALTHTARGET", page_websocket: "ws://127.0.0.1:9222/devtools/page/SELFHEALTHTARGET", page }; },
      async navigate(owned, url) { touch(owned.page); events.push(`navigate:${url}`); },
      async close(owned) { touch(owned.page); closeCalls += 1; },
    },
    async readCalendarGaps() { return []; },
    discoverCandidates: router.discoverCandidates,
    runCachedAction: router.runCachedAction,
    runDirectAction: router.runDirectAction,
    runAgentFallback(input) { fallbackCalls += 1; return router.runAgentFallback(input); },
    readProviderState: router.readProviderState,
    saveRepairedActions: router.saveRepairedActions,
    async completeEvidence({ page: suppliedPage, providerState }) { touch(suppliedPage); assert.equal(providerState.status, "registered"); evidenceCalls += 1; events.push("evidence"); return { status: "applied_bundle", bundle_id: `self-heal-bundle-${evidenceCalls}`, completion_disposition: "created" }; },
    async reportWake(report) { reports.push(report); events.push(`report:${report.status}`); return { telegram_provider_id: `self-heal-${reports.length}` }; },
    async recordAction() {},
  };
  const runWake = () => runMinimalConnectorWake({ ownerToken: "owner-token-connector-self-heal", providers: ["luma"] }, dependencies);
  try {
    const first = await runWake();
    assert.deepEqual(first, { status: "applied_bundle", bundle_id: "self-heal-bundle-1", telegram_provider_id: "self-heal-1" });
    assert.deepEqual(realCache.read(cacheKey).actions, [replacementAction]);
    assert.equal(JSON.stringify(realCache.read(cacheKey)).includes(staleAction.control), false);
    assert.ok(events.indexOf("parent:registered") < events.indexOf("cache-save"));
    const cacheAfterRepair = fs.readFileSync(cachePath);
    page.registrationState = "absent";
    const directAfterFirst = directCalls; const fallbackAfterFirst = fallbackCalls; const proposerAfterFirst = proposerCalls;
    const second = await runWake();
    assert.deepEqual(second, { status: "applied_bundle", bundle_id: "self-heal-bundle-2", telegram_provider_id: "self-heal-2" });
    assert.deepEqual(realCache.read(cacheKey).actions, [replacementAction]);
    assert.deepEqual(fs.readFileSync(cachePath), cacheAfterRepair);
    assert.equal(directCalls, directAfterFirst); assert.equal(fallbackCalls, fallbackAfterFirst); assert.equal(proposerCalls, proposerAfterFirst);
    assert.deepEqual(cacheAttempts, ["cache:stale_register_button", "harness:replacement_register_button", "cache:replacement_register_button"]);
    assert.deepEqual([directCalls, fallbackCalls, proposerCalls, harnessActionCalls, harnessReadbackCalls, saveCalls, evidenceCalls, reports.length, openCalls, closeCalls], [1, 1, 1, 1, 1, 1, 2, 2, 2, 2]);
    assert.equal(new Set(touchedPages).size, 1);
    assert.equal(fs.statSync(cachePath).mode & 0o777, 0o600);
    assert.deepEqual(reports.map(({ status, safe_reason }) => [status, safe_reason]), [["applied_bundle", "applied_bundle"], ["applied_bundle", "applied_bundle"]]);
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});
