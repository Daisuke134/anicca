"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { createConnectorCoverageRuntimeServices } = require("./connector-coverage-runtime-services.js");

test("runtime assembly keeps evidence in Docker and sends only Calendar, route, and opaque home through the host bridge", () => {
  const observed = {};
  const query = async () => ({ rows: [] });
  const connect = async () => ({ query, release() {} });
  const bridge = { calendar: { findConnectorEvents() {}, createConnectorEvent() {} }, routeMinutes() {} };
  const evidenceStore = { record() {}, readExternalReceipt() {}, readArtifact() {} };
  const dailyDriver = { withLumaPage() {} };
  const auth = { ensureAuthenticated() {} };
  const pack = {
    readDateInventory() {}, readBusyCalendar() {}, gateDateCalendar() {},
    syncRegistrationCalendar() {}, buildRegistrationCoverageEvidence() {},
    proveUnavailableDay() {}, rebuildCoverage() {},
  };
  const coverageStore = { read() {}, save() {} };
  const receiptReader = { listForCoverage() {} };
  const refreshCoverage = async () => {};
  const services = createConnectorCoverageRuntimeServices({
    LM_RUNTIME_TENANT_ID: "dais-local",
    LM_DATA_DIR: "/var/lib/life-manager/data",
    LM_CONNECTOR_BRIDGE_URL: "http://host.docker.internal:18793",
    LM_CONNECTOR_BRIDGE_TOKEN: "a".repeat(64),
  }, { query, connect }, {
    createBridge(options) { observed.bridge = options; return bridge; },
    createEvidenceStore(options) { observed.evidence = options; return evidenceStore; },
    createDailyDriver() { return dailyDriver; },
    createAuth(options) { observed.auth = options; return auth; },
    createPack(options) { observed.pack = options; return pack; },
    createCoverageStore(options) { observed.coverageStore = options; return coverageStore; },
    createReceiptReader(options) { observed.receiptReader = options; return receiptReader; },
    createRefreshService(options) { observed.refresh = options; return refreshCoverage; },
    fetchImpl: async () => {},
    now: () => "2026-08-02T01:00:00.000Z",
  });

  assert.equal(observed.bridge.baseUrl, "http://host.docker.internal:18793");
  assert.equal(observed.bridge.token, "a".repeat(64));
  assert.equal(observed.evidence.dataDir, "/var/lib/life-manager/data");
  assert.equal(observed.pack.dailyDriver, dailyDriver);
  assert.equal(observed.pack.auth, auth);
  assert.equal(observed.pack.evidenceStore, evidenceStore);
  assert.equal(observed.receiptReader.query, query);
  assert.equal(observed.receiptReader.readExternalReceipt, evidenceStore.readExternalReceipt);
  assert.equal(observed.coverageStore.connect, connect);
  assert.equal(observed.refresh.calendar, bridge.calendar);
  assert.equal(observed.refresh.routeMinutes, bridge.routeMinutes);
  assert.equal(observed.refresh.homeLocation, "home://dais-local");
  assert.equal(observed.refresh.calendarId, "primary");
  assert.equal(services.coverageStore, coverageStore);
  assert.equal(services.refreshCoverage, refreshCoverage);
  assert.deepEqual(services.storeOptions, { query });
});

test("runtime assembly fails before browser or network when its tenant, stores, or bridge config is missing", () => {
  const base = {
    LM_RUNTIME_TENANT_ID: "dais-local",
    LM_DATA_DIR: "/var/lib/life-manager/data",
    LM_CONNECTOR_BRIDGE_URL: "http://host.docker.internal:18793",
    LM_CONNECTOR_BRIDGE_TOKEN: "a".repeat(64),
  };
  const runtime = { query: async () => {}, connect: async () => {} };
  for (const name of Object.keys(base)) {
    assert.throws(() => createConnectorCoverageRuntimeServices({ ...base, [name]: "" }, runtime), /coverage runtime unavailable/i);
  }
  assert.throws(() => createConnectorCoverageRuntimeServices(base, { ...runtime, query: null }), /coverage runtime unavailable/i);
  assert.throws(() => createConnectorCoverageRuntimeServices(base, { ...runtime, connect: null }), /coverage runtime unavailable/i);
});
