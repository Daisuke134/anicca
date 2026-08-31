"use strict";

const dns = require("node:dns");
const path = require("node:path");

function unavailable() { throw new Error("Connector coverage runtime unavailable"); }

function required(env, name) {
  const value = String(env[name] == null ? "" : env[name]).trim();
  if (!value) unavailable();
  return value;
}

function productionFactories() {
  const { chromium } = require("playwright-core");
  const { createCloakBrowserDailyDriver } = require("./cloakbrowser-daily-driver.js");
  const { createReadOnlyLumaSessionAuth } = require("./luma-daily-driver-auth.js");
  const { createConnectorEventsPack } = require("./connector-events-pack.js");
  const { createConnectorHostBridgeClient } = require("./connector-host-bridge.js");
  const { createConnectorCoverageRefreshService } = require("./connector-coverage-refresh-service.js");
  const { createLumaEvidenceStore } = require("./luma-evidence-store.js");
  const { createRollingEventCoverageStore } = require("./rolling-event-coverage-store.js");
  const { createVerifiedOutboundReceiptReader } = require("./verified-outbound-receipt-reader.js");
  const { readConnectorProfile } = require("./connector-profile.js");
  const {
    createConnectorOpenDateApplicationPlanner,
    rebindUnavailableConnectorOpenDatePlan,
    unavailableEvidenceForConnectorOpenDatePlan,
  } = require("./connector-open-date-planner.js");
  const { createOutboundApplicationJobReader } = require("./outbound-application-job-reader.js");
  const { createEventSpendPolicy } = require("./event-spend-policy.js");
  const { buildEventApplicationJob, enqueueEventApplication } = require("./outbound-event-job.js");
  return {
    createAuth: createReadOnlyLumaSessionAuth,
    createBridge: createConnectorHostBridgeClient,
    createCoverageStore: createRollingEventCoverageStore,
    createDailyDriver: (options = {}) => createCloakBrowserDailyDriver({
      connectOverCDP: options.connectOverCDP || ((endpoint) => chromium.connectOverCDP(endpoint)),
      resolveEndpoint: options.resolveEndpoint || (async () => {
        const resolved = await dns.promises.lookup("host.docker.internal", { family: 4 });
        const address = typeof resolved === "string" ? resolved : resolved.address;
        return `http://${address}:9222`;
      }),
    }),
    createEvidenceStore: createLumaEvidenceStore,
    createPack: createConnectorEventsPack,
    createReceiptReader: createVerifiedOutboundReceiptReader,
    createRefreshService: createConnectorCoverageRefreshService,
    readProfile: readConnectorProfile,
    createOpenDatePlanner: createConnectorOpenDateApplicationPlanner,
    createJobReader: createOutboundApplicationJobReader,
    createSpendPolicy: createEventSpendPolicy,
    buildApplicationJob: buildEventApplicationJob,
    enqueueApplication: enqueueEventApplication,
    readUnavailablePlanEvidence: unavailableEvidenceForConnectorOpenDatePlan,
    rebindUnavailablePlan: rebindUnavailableConnectorOpenDatePlan,
  };
}

function createConnectorCoverageRuntimeServices(env = {}, runtime = {}, overrides = {}) {
  if (typeof runtime.query !== "function" || typeof runtime.connect !== "function") unavailable();
  const tenantId = required(env, "LM_RUNTIME_TENANT_ID");
  const dataDir = path.resolve(required(env, "LM_DATA_DIR"));
  const bridgeUrl = required(env, "LM_CONNECTOR_BRIDGE_URL");
  const bridgeToken = required(env, "LM_CONNECTOR_BRIDGE_TOKEN");
  const profilePath = required(env, "LM_CONNECTOR_PROFILE_PATH");
  const apiKey = required(env, "GEMINI_API_KEY");
  const factories = { ...productionFactories(), ...overrides };
  const now = overrides.now || (() => new Date().toISOString());
  const fetchImpl = overrides.fetchImpl || globalThis.fetch;
  try {
    const bridge = factories.createBridge({
      baseUrl: bridgeUrl,
      token: bridgeToken,
      fetchImpl,
    });
    const evidenceStore = factories.createEvidenceStore({ dataDir });
    const dailyDriver = factories.createDailyDriver({
      connectOverCDP: overrides.connectOverCDP,
      resolveEndpoint: overrides.resolveEndpoint,
    });
    const auth = factories.createAuth({ dailyDriver });
    const pack = factories.createPack({ dailyDriver, auth, evidenceStore, now });
    const coverageStore = factories.createCoverageStore({ connect: runtime.connect });
    const receiptReader = factories.createReceiptReader({
      query: runtime.query,
      readExternalReceipt: evidenceStore.readExternalReceipt,
      readArtifact: evidenceStore.readArtifact,
      fetchImpl,
    });
    const profile = factories.readProfile({ path: profilePath, tenantId });
    const jobReader = factories.createJobReader({ query: runtime.query });
    const planOpenDate = factories.createOpenDatePlanner({
      rankDatePreferences: (...args) => pack.rankDatePreferences(...args),
      evaluateDateGoals: (...args) => pack.evaluateDateGoals(...args),
      gateDateCalendar: (...args) => pack.gateDateCalendar(...args),
      createSpendPolicy: factories.createSpendPolicy,
      buildSpendSequence: (...args) => pack.planDateSpend(...args),
      buildApplicationJob: factories.buildApplicationJob,
      readApplicationJob: (job) => jobReader.read(job),
      enqueueApplication: (input) => factories.enqueueApplication(input, { query: runtime.query }),
      proveCalendarUnavailable: (input) => pack.proveCalendarGateUnavailable(input),
    });
    const refreshCoverage = factories.createRefreshService({
      receiptReader,
      calendar: bridge.calendar,
      calendarId: String(env.LM_CONNECTOR_CALENDAR_ID || "primary").trim(),
      now,
      readDateInventory: ({ coverage, now: observedAt }) => (
        pack.readDateInventory(coverage, { now: observedAt })
      ),
      readBusyCalendar: ({ calendar, ...window }) => pack.readBusyCalendar(calendar, window),
      syncRegistrationCalendar: (input) => pack.syncRegistrationCalendar(input),
      buildRegistrationCoverageEvidence: (input) => pack.buildRegistrationCoverageEvidence(input),
      proveUnavailableDay: (input) => pack.proveUnavailableDay(input),
      rebuildCoverage: (input) => pack.rebuildCoverage(input),
      planOpenDate,
      readUnavailablePlanEvidence: factories.readUnavailablePlanEvidence,
      rebindUnavailablePlan: factories.rebindUnavailablePlan,
      profile,
      apiKey,
    });
    return Object.freeze({
      coverageStore,
      refreshCoverage,
      storeOptions: Object.freeze({ query: runtime.query }),
      now,
    });
  } catch { unavailable(); }
}

module.exports = { createConnectorCoverageRuntimeServices };
