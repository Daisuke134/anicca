"use strict";

const INTERVAL_MS = 15 * 60 * 1000;

async function runConfiguredFunderReflection(env = process.env, dependencies = {}) {
  const connectionString = String(env.DATABASE_URL || env.LM_RUNTIME_DATABASE_URL || "").trim();
  const tenantId = String(env.LM_FUNDRAISING_TENANT_ID || "").trim();
  if (!connectionString || !tenantId) return { status: "disabled" };
  const Client = dependencies.Client || require("pg").Client;
  const client = new Client({ connectionString });
  await client.connect();
  try {
    const reflectedAt = new Date((dependencies.now || Date.now)()).toISOString();
    const latest = await client.query(`
      SELECT week_key::text FROM public.lm_funder_weekly_reflection_ledger
      WHERE tenant_id=$1 ORDER BY week_key DESC LIMIT 1
    `, [tenantId]);
    const { runFunderWeeklyReflection, requestGeminiFunderReflection } = require("./funder-weekly-reflection-runtime.js");
    const { collectFunderWeeklyReflectionSnapshot } = require("./funder-weekly-reflection-snapshot.js");
    const { appendFunderWeeklyReflection } = require("./funder-weekly-reflection-store.js");
    return runFunderWeeklyReflection({
      tenantId,
      reflectedAt,
      latestWeekKey: latest.rows[0] ? latest.rows[0].week_key : null,
    }, {
      collectSnapshot: (request) => collectFunderWeeklyReflectionSnapshot(request, {
        query: client.query.bind(client),
      }),
      judge: (snapshot) => requestGeminiFunderReflection(snapshot, {
        apiKey: env.GEMINI_API_KEY,
        fetchImpl: dependencies.fetchImpl,
      }),
      append: (value) => appendFunderWeeklyReflection(value, {
        query: client.query.bind(client),
      }),
    });
  } finally {
    await client.end();
  }
}

function startFunderWeeklyReflectionLoop(options = {}) {
  const env = options.env || process.env;
  const logger = options.logger || console;
  if (!String(env.DATABASE_URL || env.LM_RUNTIME_DATABASE_URL || "").trim()
    || !String(env.LM_FUNDRAISING_TENANT_ID || "").trim()) {
    return Object.freeze({ enabled: false, reason: "fundraising database or tenant not configured" });
  }
  const runOnce = options.runOnce || (() => runConfiguredFunderReflection(env, options));
  let active = false;
  const run = async () => {
    if (active) return;
    active = true;
    try {
      const result = await runOnce();
      logger.log(`[funding-reflection] ${result.status}${result.reason ? ` ${result.reason}` : ""}`);
    } catch (error) {
      logger.error(`[funding-reflection] tick failed: ${error && error.message}`);
    } finally {
      active = false;
    }
  };
  run();
  const timer = (options.setIntervalImpl || setInterval)(run, INTERVAL_MS);
  if (timer && typeof timer.unref === "function") timer.unref();
  return Object.freeze({ enabled: true, interval_ms: INTERVAL_MS, timer });
}

module.exports = { INTERVAL_MS, runConfiguredFunderReflection, startFunderWeeklyReflectionLoop };
