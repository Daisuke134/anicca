"use strict";

const { createAuthAwareLumaDailyDriver } = require("./luma-daily-driver-auth.js");
const { discoverLumaTokyo } = require("./luma-discovery.js");
const { inspectLumaEvent } = require("./luma-event-detail.js");
const { createLumaBrowserProvider } = require("./luma-browser-provider.js");

function invalid() {
  return new Error("Connector events pack configuration unavailable");
}

function createConnectorEventsPack(options = {}) {
  const dailyDriver = options.dailyDriver;
  const auth = options.auth;
  const evidenceStore = options.evidenceStore;
  if (
    !dailyDriver
    || typeof dailyDriver.withLumaPage !== "function"
    || !auth
    || typeof auth.ensureAuthenticated !== "function"
    || !evidenceStore
    || typeof evidenceStore.record !== "function"
  ) throw invalid();

  const createAuthAwareDriver = options.createAuthAwareDriver || createAuthAwareLumaDailyDriver;
  const createProvider = options.createProvider || createLumaBrowserProvider;
  const discover = options.discover || discoverLumaTokyo;
  const inspect = options.inspect || inspectLumaEvent;
  const authAwareDriver = createAuthAwareDriver({ dailyDriver, auth });
  if (!authAwareDriver || typeof authAwareDriver.withLumaPage !== "function") throw invalid();
  const provider = createProvider({
    dailyDriver: authAwareDriver,
    evidenceStore,
    now: options.now,
  });
  if (
    !provider
    || typeof provider.inspectRegistration !== "function"
    || typeof provider.submitRegistration !== "function"
  ) throw invalid();

  return Object.freeze({
    provider,
    discoverTokyo(extra = {}) {
      return discover({ ...extra, dailyDriver: authAwareDriver });
    },
    inspectEvent(canonicalUrl, extra = {}) {
      return inspect({ ...extra, dailyDriver: authAwareDriver, canonicalUrl });
    },
  });
}

module.exports = { createConnectorEventsPack };
