"use strict";

const { createAuthAwareLumaDailyDriver } = require("./luma-daily-driver-auth.js");
const { discoverLumaTokyo } = require("./luma-discovery.js");
const { inspectLumaEvent } = require("./luma-event-detail.js");
const { inspectLumaDateInventory } = require("./luma-date-inventory.js");
const { createLumaBrowserProvider } = require("./luma-browser-provider.js");
const { inferEventPreferenceRanking } = require("./event-preference-ranking.js");

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
  const inspectDateInventory = options.inspectDateInventory || inspectLumaDateInventory;
  const rankPreferences = options.rankPreferences || inferEventPreferenceRanking;
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
    readDateInventory(coverage, extra = {}) {
      return inspectDateInventory({
        coverage,
        now: extra.now,
        discoverTokyo: () => discover({
          dailyDriver: authAwareDriver,
          maxRounds: extra.maxRounds,
          stableEndRounds: extra.stableEndRounds,
        }),
        inspectEvent: (canonicalUrl) => inspect({
          dailyDriver: authAwareDriver,
          canonicalUrl,
        }),
      });
    },
    rankDatePreferences(dateInventory, date, preferences, extra = {}) {
      return rankPreferences({ dateInventory, date, preferences }, extra);
    },
  });
}

module.exports = { createConnectorEventsPack };
