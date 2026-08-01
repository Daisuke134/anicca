#!/usr/bin/env node
"use strict";

const { chromium } = require("playwright-core");
const { createCloakBrowserDailyDriver } = require("../lib/cloakbrowser-daily-driver.js");
const { createLumaDailyDriverAuth } = require("../lib/luma-daily-driver-auth.js");
const { createGogLumaCodeReader } = require("../lib/gog-luma-code-reader.js");
const { createConnectorEventsPack } = require("../lib/connector-events-pack.js");
const { buildRollingEventCoverage } = require("../lib/rolling-event-coverage.js");

function required(value) {
  return String(value == null ? "" : value).trim();
}

async function runConnectorEventsPackReadonly({ env = process.env, deps = {} } = {}) {
  const account = required(env.GOG_ACCOUNT).toLowerCase();
  const loginEmail = required(env.DAIS_EMAIL || env.LM_CONNECTOR_LUMA_EMAIL).toLowerCase();
  const name = required(env.DAIS_LEGAL_NAME_ROMAJI || env.LM_CONNECTOR_LUMA_NAME);
  if (
    !account
    || !loginEmail
    || account !== loginEmail
    || !/^[^@\s]+@[^@\s]+$/.test(account)
    || !name
  ) throw new Error("Connector events pack unavailable");

  const dailyDriver = (deps.createDailyDriver || createCloakBrowserDailyDriver)({
    connectOverCDP: deps.connectOverCDP || ((endpoint) => chromium.connectOverCDP(endpoint)),
  });
  const readLoginCode = deps.readLoginCode || createGogLumaCodeReader({ env });
  const auth = (deps.createAuth || createLumaDailyDriverAuth)({
    dailyDriver,
    email: loginEmail,
    name,
    readLoginCode,
  });
  const pack = (deps.createPack || createConnectorEventsPack)({
    dailyDriver,
    auth,
    evidenceStore: {
      async record() {
        throw new Error("Read-only Connector events pack cannot record RSVP evidence");
      },
    },
  });
  const authResult = await auth.ensureAuthenticated();
  const now = (deps.now || (() => new Date().toISOString()))();
  const coverage = buildRollingEventCoverage({
    tenantId: "dais-local",
    timeZone: "Asia/Tokyo",
    now,
    resolvedDays: [],
  });
  const inventory = await pack.readDateInventory(coverage, { now });
  if (
    !authResult
    || authResult.status !== "authenticated"
    || !inventory
    || inventory.complete !== true
    || !inventory.counts
    || inventory.counts.discovered !== inventory.counts.inspected
    || inventory.counts.dates_with_candidates + inventory.counts.dates_without_candidates !== 21
  ) throw new Error("Connector events pack unavailable");
  return Object.freeze({
    provider: "luma",
    transport: "cloakbrowser-daily-driver",
    authenticated: true,
    recovered: authResult.recovered === true,
    inventory_complete: true,
    window_start_date: inventory.window_start_date,
    window_end_date: inventory.window_end_date,
    inventory_rounds: inventory.source_inventory_rounds,
    discovered_candidate_count: inventory.counts.discovered,
    inspected_detail_count: inventory.counts.inspected,
    scheduled_in_person_in_window_count: inventory.counts.scheduled_in_person_in_window,
    excluded_detail_count: inventory.counts.excluded,
    dates_with_candidates: inventory.counts.dates_with_candidates,
    dates_without_candidates: inventory.counts.dates_without_candidates,
  });
}

async function main() {
  try {
    const result = await runConnectorEventsPackReadonly();
    writeCliResult(result);
  } catch {
    writeCliFailure();
  }
}

function writeCliResult(result, options = {}) {
  const stdout = options.stdout || process.stdout;
  const exit = options.exit || process.exit;
  stdout.write(`${JSON.stringify(result)}\n`, () => exit(0));
}

function writeCliFailure(options = {}) {
  const stderr = options.stderr || process.stderr;
  const exit = options.exit || process.exit;
  stderr.write("Connector events pack unavailable\n", () => exit(1));
}

if (require.main === module) main();

module.exports = { runConnectorEventsPackReadonly, writeCliFailure, writeCliResult };
