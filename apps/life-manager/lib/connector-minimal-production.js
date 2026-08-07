"use strict";

const crypto = require("node:crypto");
const path = require("node:path");

const {
  CONNECTOR_CDP_ENDPOINT,
  createConnectorBrowserTargetController,
} = require("./connector-browser-target-controller.js");
const { createConnectorTabOwner } = require("./connector-tab-owner.js");
const { createConnectorTargetLease } = require("./connector-target-lease.js");
const { createConnectorActionCache } = require("./connector-action-cache.js");
const { createMinimalEvidenceChain } = require("./connector-minimal-evidence.js");
const { createMinimalProductionOperations } = require("./connector-minimal-operations.js");
const { createLumaScriptFirstWorkflow } = require("./connector-luma-workflow.js");
const { readLumaFormProfile } = require("./luma-form-profile.js");
const {
  createBoundedActionProposer,
  createLumaPrivateValueResolver,
  createProductionBrowserHarness,
  inspectPageControls,
  operatePageControl,
} = require("./connector-production-browser-harness.js");
const {
  inspectGoogleCalendarBusyInventory,
  isVerifiedGoogleCalendarBusyInventory,
} = require("./google-calendar-busy-inventory.js");
const { zonedSlotInstant } = require("./honne-ja-shadow-schedule.js");
const { makeGogCalendar } = require("./transport/calendar-gog.js");

const LUMA_DISCOVERY_URL = "https://luma.com/tokyo?k=p";
const PRODUCTION_TIME_ZONE = "Asia/Tokyo";
const LUMA_WORKFLOW_VERSION = "luma_registration_v1";
const LUMA_PAGE_STATE = "registration_page_v1";
const EXPECTED_REGISTRATION_EFFECT = "registered_or_pending";

function invalid() {
  throw new Error("Connector minimal production unavailable");
}

function absoluteDirectory(value) {
  const directory = path.resolve(String(value || ""));
  if (!path.isAbsolute(directory) || directory === path.parse(directory).root) invalid();
  return directory;
}

function ownerToken(value) {
  const token = String(value || "").trim();
  if (!/^[A-Za-z0-9._-]{16,200}$/.test(token)) invalid();
  return token;
}

function requiredText(value, max = 2_000) {
  const result = String(value == null ? "" : value).trim();
  if (!result || result.length > max || /[\x00-\x1f\x7f]/.test(result)) invalid();
  return result;
}

function exactNow(value) {
  const date = value instanceof Date ? value : new Date(value);
  if (!Number.isFinite(date.getTime())) invalid();
  return date;
}

function localDay(date, timeZone) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date).filter((part) => part.type !== "literal")
    .map((part) => [part.type, Number(part.value)]));
  if (![parts.year, parts.month, parts.day].every(Number.isInteger)) invalid();
  return Object.freeze({ year: parts.year, month: parts.month, day: parts.day });
}

function addCalendarDays(day, count) {
  const shifted = new Date(Date.UTC(day.year, day.month - 1, day.day + count));
  return Object.freeze({
    year: shifted.getUTCFullYear(),
    month: shifted.getUTCMonth() + 1,
    day: shifted.getUTCDate(),
  });
}

function createProductionCalendarReader(options = {}) {
  const timeZone = String(options.timeZone || PRODUCTION_TIME_ZONE);
  if (timeZone !== PRODUCTION_TIME_ZONE) invalid();
  const now = options.now || (() => new Date());
  const makeCalendar = options.makeCalendar || makeGogCalendar;
  const inspectBusyInventory = options.inspectBusyInventory || inspectGoogleCalendarBusyInventory;
  const isVerifiedBusyInventory = options.isVerifiedBusyInventory || isVerifiedGoogleCalendarBusyInventory;
  if (
    typeof now !== "function" || typeof makeCalendar !== "function"
    || typeof inspectBusyInventory !== "function" || typeof isVerifiedBusyInventory !== "function"
  ) invalid();
  const calendar = makeCalendar({
    bin: options.gogBin,
    account: options.account,
    keyring: options.keyring,
  });
  if (!calendar || typeof calendar.ready !== "function" || calendar.ready() !== true) invalid();

  return Object.freeze({
    async readCalendarGaps() {
      const observed = exactNow(now());
      const firstDay = localDay(observed, timeZone);
      const inventory = await inspectBusyInventory({
        calendar,
        timeMin: zonedSlotInstant(firstDay, "00:00", timeZone),
        timeMax: zonedSlotInstant(addCalendarDays(firstDay, 14), "00:00", timeZone),
        now: observed.toISOString(),
        timeZone,
      });
      if (!isVerifiedBusyInventory(inventory) || !Array.isArray(inventory.busy_intervals)) invalid();
      return inventory.busy_intervals;
    },
  });
}

function createProductionProviderRouter(options = {}) {
  const lumaWorkflow = options.lumaWorkflow;
  const actionCache = options.actionCache;
  const browserHarness = options.browserHarness;
  const performAction = options.performAction;
  const now = options.now || (() => new Date());
  if (
    !lumaWorkflow || typeof lumaWorkflow.discoverCandidates !== "function"
    || typeof lumaWorkflow.runDirectAction !== "function"
    || typeof lumaWorkflow.readProviderState !== "function"
    || !actionCache || typeof actionCache.replay !== "function"
    || typeof actionCache.saveVerifiedRepair !== "function"
    || !browserHarness || typeof browserHarness.runFallback !== "function"
    || typeof performAction !== "function" || typeof now !== "function"
  ) invalid();

  function luma(input) {
    if (!input || input.provider !== "luma") invalid();
    return input;
  }

  return Object.freeze({
    discoverCandidates(provider, calendar, page) {
      if (provider === "connpass") return Promise.resolve(Object.freeze([]));
      if (provider !== "luma") invalid();
      return lumaWorkflow.discoverCandidates({ page, calendar });
    },

    runCachedAction(input) {
      const selected = luma(input);
      return actionCache.replay({
        provider: "luma",
        workflowVersion: LUMA_WORKFLOW_VERSION,
        pageState: LUMA_PAGE_STATE,
        expectedEffect: EXPECTED_REGISTRATION_EFFECT,
        page: selected.page,
        performAction,
        readExpectedState: ({ page }) => lumaWorkflow.readProviderState({
          page,
          candidate: selected.candidate,
        }),
      });
    },

    runDirectAction(input) {
      const selected = luma(input);
      return lumaWorkflow.runDirectAction({ page: selected.page, candidate: selected.candidate });
    },

    runAgentFallback(input) {
      const selected = luma(input);
      return browserHarness.runFallback({
        provider: "luma",
        candidate: selected.candidate,
        page: selected.page,
        pageWebsocket: selected.pageWebsocket,
        maxSteps: selected.maxSteps,
        expectedState: selected.expectedState,
      });
    },

    readProviderState(input) {
      const selected = luma(input);
      return lumaWorkflow.readProviderState({ page: selected.page, candidate: selected.candidate });
    },

    saveRepairedActions(input) {
      const selected = luma(input);
      return actionCache.saveVerifiedRepair({
        provider: "luma",
        workflowVersion: LUMA_WORKFLOW_VERSION,
        pageState: LUMA_PAGE_STATE,
        expectedEffect: EXPECTED_REGISTRATION_EFFECT,
        providerState: selected.providerState,
        actions: selected.repairedActions,
        observedAt: exactNow(now()).toISOString(),
      });
    },
  });
}

function createMinimalProductionDependencies(options = {}) {
  const repoRoot = absoluteDirectory(options.repoRoot);
  const stateDir = absoluteDirectory(options.stateDir);
  const wakeId = requiredText(options.wakeId, 160);
  const calendarAccount = requiredText(options.calendarAccount, 1_024);
  const gogKeyring = requiredText(options.gogKeyring, 2_000);
  const telegramTarget = requiredText(options.telegramTarget, 200);
  const tenantId = requiredText(options.tenantId || "dais-local", 128);
  const calendarId = requiredText(options.calendarId || "primary", 1_024);
  const lumaFormProfilePath = path.resolve(requiredText(options.lumaFormProfilePath, 2_000));
  const lunaEvidenceDir = absoluteDirectory(options.lunaEvidenceDir);
  const now = options.now || (() => new Date());
  if (typeof now !== "function") invalid();
  const nowIso = () => exactNow(now()).toISOString();

  const calendar = options.calendar || makeGogCalendar({
    bin: options.gogBin,
    account: calendarAccount,
    keyring: gogKeyring,
  });
  const calendarReader = options.calendarReader || createProductionCalendarReader({
    gogBin: options.gogBin,
    account: calendarAccount,
    keyring: gogKeyring,
    now,
    makeCalendar: () => calendar,
  });
  const browserRail = options.browserRail || createProductionBrowserRail({ stateDir });
  const operations = options.operations || createMinimalProductionOperations({
    stateDir,
    wakeId,
    telegramTarget,
    now,
  });
  const lumaWorkflow = options.lumaWorkflow || createLumaScriptFirstWorkflow({
    now,
    onDiscoveryAudit: operations.recordDiscoveryAudit || (() => {}),
    readLumaFormProfile: () => readLumaFormProfile({ path: lumaFormProfilePath }),
  });
  const actionCache = options.actionCache || createConnectorActionCache({
    path: path.join(stateDir, "action-cache.json"),
  });
  const proposeAction = options.proposeAction || createBoundedActionProposer({
    repoRoot,
    evidenceDir: lunaEvidenceDir,
  });
  const resolveValue = options.resolveValue || createLumaPrivateValueResolver({
    readProfile: () => readLumaFormProfile({ path: lumaFormProfilePath }),
  });
  const browserHarness = options.browserHarness || createProductionBrowserHarness({
    lumaWorkflow,
    inspectControls: inspectPageControls,
    proposeAction,
    operateControl: operatePageControl,
    resolveValue,
  });
  const providerRouter = options.providerRouter || createProductionProviderRouter({
    lumaWorkflow,
    actionCache,
    browserHarness,
    performAction: browserHarness.performAction,
    now,
  });
  const evidenceChain = options.evidenceChain || createMinimalEvidenceChain({
    stateDir,
    tenantId,
    calendar,
    calendarId,
    telegramTarget,
    now,
  });
  return Object.freeze({
    now: nowIso,
    browserRail,
    readCalendarGaps: calendarReader.readCalendarGaps,
    discoverCandidates: providerRouter.discoverCandidates,
    runCachedAction: providerRouter.runCachedAction,
    runDirectAction: providerRouter.runDirectAction,
    runAgentFallback: providerRouter.runAgentFallback,
    readProviderState: providerRouter.readProviderState,
    saveRepairedActions: providerRouter.saveRepairedActions,
    completeEvidence: evidenceChain.completeEvidence,
    reportWake: operations.reportWake,
    recordAction: operations.recordAction,
  });
}

function createProductionBrowserRail(options = {}) {
  const stateDir = absoluteDirectory(options.stateDir);
  const connectOverCDP = options.connectOverCDP || ((endpoint) => {
    const { chromium } = require("playwright-core");
    return chromium.connectOverCDP(endpoint);
  });
  const createTargetController = options.createTargetController
    || ((input) => createConnectorBrowserTargetController(input));
  const createTargetOwnership = options.createTargetOwnership || ((input) => {
    const targetLease = createConnectorTargetLease({
      ledgerPath: path.join(stateDir, "evidence", "target-leases.json"),
      ownerToken: () => input.ownerToken,
      probeTarget: (pageWebsocket) => input.controller.probe(pageWebsocket),
      closeTarget: (targetId) => input.controller.close(targetId),
    });
    return createConnectorTabOwner({
      endpoint: CONNECTOR_CDP_ENDPOINT,
      targetLease,
    });
  });
  const makeSessionId = options.makeSessionId || (() => crypto.randomUUID());
  if (
    typeof connectOverCDP !== "function"
    || typeof createTargetController !== "function"
    || typeof createTargetOwnership !== "function"
    || typeof makeSessionId !== "function"
  ) invalid();

  return Object.freeze({
    async open(input = {}) {
      const exactOwnerToken = ownerToken(input.ownerToken);
      const browser = await connectOverCDP(CONNECTOR_CDP_ENDPOINT);
      const controller = createTargetController({ browser, endpoint: CONNECTOR_CDP_ENDPOINT });
      if (!controller || typeof controller.create !== "function" || typeof controller.close !== "function") invalid();
      const target = await controller.create();
      let ownership = null;
      let receipt = null;
      try {
        ownership = createTargetOwnership({
          controller,
          ownerToken: exactOwnerToken,
          stateDir,
        });
        if (
          !ownership || typeof ownership.claimExact !== "function"
          || typeof ownership.probe !== "function" || typeof ownership.heartbeat !== "function"
          || typeof ownership.release !== "function"
        ) invalid();
        receipt = await ownership.claimExact({
          canonicalUrl: LUMA_DISCOVERY_URL,
          targetId: target.target_id,
          pageWebsocket: target.page_websocket,
          receiptPath: path.join(stateDir, "evidence", "tab-owner.json"),
        });
        if (await ownership.probe(receipt) !== true) invalid();
        await ownership.heartbeat(receipt);
        const sessionId = String(makeSessionId());
        if (!/^[A-Za-z0-9._-]{3,128}$/.test(sessionId)) invalid();
        return Object.freeze({
          session_id: sessionId,
          target_id: target.target_id,
          page_websocket: target.page_websocket,
          page: target.page,
          ownership,
          receipt,
        });
      } catch (error) {
        if (receipt && ownership) {
          try { await ownership.release(receipt); } catch {}
        } else {
          try { await controller.close(target.target_id); } catch {}
        }
        throw error;
      }
    },

    async navigate(owned, url) {
      if (!owned || !owned.page || !owned.ownership || !owned.receipt) invalid();
      await owned.ownership.heartbeat(owned.receipt);
      await owned.page.goto(String(url), { waitUntil: "domcontentloaded", timeout: 30_000 });
      await owned.ownership.heartbeat(owned.receipt);
    },

    async close(owned) {
      if (!owned || !owned.ownership || !owned.receipt) invalid();
      return owned.ownership.release(owned.receipt);
    },
  });
}

module.exports = {
  createProductionBrowserRail,
  createProductionCalendarReader,
  createMinimalProductionDependencies,
  createProductionProviderRouter,
};
