#!/usr/bin/env node
"use strict";

const { chromium } = require("playwright-core");
const { createCloakBrowserDailyDriver } = require("../lib/cloakbrowser-daily-driver.js");
const { createLumaDailyDriverAuth } = require("../lib/luma-daily-driver-auth.js");
const { createGogLumaCodeReader } = require("../lib/gog-luma-code-reader.js");
const { createConnectorEventsPack } = require("../lib/connector-events-pack.js");

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
  const inventory = await pack.discoverTokyo();
  if (
    !authResult
    || authResult.status !== "authenticated"
    || !inventory
    || inventory.complete !== true
    || !Array.isArray(inventory.candidates)
  ) throw new Error("Connector events pack unavailable");
  return Object.freeze({
    provider: "luma",
    transport: "cloakbrowser-daily-driver",
    authenticated: true,
    recovered: authResult.recovered === true,
    inventory_complete: true,
    inventory_rounds: inventory.rounds,
    candidate_count: inventory.candidates.length,
  });
}

async function main() {
  try {
    const result = await runConnectorEventsPackReadonly();
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } catch {
    process.stderr.write("Connector events pack unavailable\n");
    process.exitCode = 1;
  }
}

if (require.main === module) main();

module.exports = { runConnectorEventsPackReadonly };
