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
  };
}

function createConnectorCoverageRuntimeServices(env = {}, runtime = {}, overrides = {}) {
  if (typeof runtime.query !== "function" || typeof runtime.connect !== "function") unavailable();
  const tenantId = required(env, "LM_RUNTIME_TENANT_ID");
  const dataDir = path.resolve(required(env, "LM_DATA_DIR"));
  const bridgeUrl = required(env, "LM_CONNECTOR_BRIDGE_URL");
  const bridgeToken = required(env, "LM_CONNECTOR_BRIDGE_TOKEN");
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
    const refreshCoverage = factories.createRefreshService({
      receiptReader,
      calendar: bridge.calendar,
      calendarId: String(env.LM_CONNECTOR_CALENDAR_ID || "primary").trim(),
      homeLocation: `home://${tenantId}`,
      routeMinutes: bridge.routeMinutes,
      now,
      readDateInventory: ({ coverage, now: observedAt }) => (
        pack.readDateInventory(coverage, { now: observedAt })
      ),
      readBusyCalendar: ({ calendar, ...window }) => pack.readBusyCalendar(calendar, window),
      gateDateCalendar: (input) => pack.gateDateCalendar(
        input.dateInventory,
        input.busyInventory,
        input.date,
        input.homeLocation,
        input.routeMinutes,
      ),
      syncRegistrationCalendar: (input) => pack.syncRegistrationCalendar(input),
      buildRegistrationCoverageEvidence: (input) => pack.buildRegistrationCoverageEvidence(input),
      proveUnavailableDay: (input) => pack.proveUnavailableDay(input),
      rebuildCoverage: (input) => pack.rebuildCoverage(input),
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
