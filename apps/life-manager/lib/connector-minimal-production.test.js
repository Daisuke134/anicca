"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

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
