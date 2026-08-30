#!/usr/bin/env node
"use strict";

const TENANT_RE = /^[a-z0-9][a-z0-9._-]{0,199}$/;
const HEX64_RE = /^[0-9a-f]{64}$/;
const SECRET_RE = /^[A-Za-z0-9_-]{32,256}$/;
const MONEY_RE = /^[0-9]+$/;
const COOKIE_NAMES = new Set(["lm_panel_scope", "lm_panel_session", "__Host-lm_panel_session"]);
const CLAIM_PATH = "/api/internal/money-printer/symphony/claim";
const GUEST_PATH = "/money-printer";
const WORKROOM_PATH = "/api/panel/money-printer/workroom";

function fail(message) {
  throw new Error(message);
}

function validateConfig(config) {
  if (!config || typeof config !== "object" || Array.isArray(config)) fail("bridge configuration invalid");
  const apiBaseUrl = String(config.apiBaseUrl || "").trim().replace(/\/+$/, "");
  let parsed;
  try { parsed = new URL(apiBaseUrl); } catch { fail("bridge configuration invalid"); }
  if (parsed.protocol !== "https:" || parsed.username || parsed.password || parsed.search || parsed.hash) {
    fail("bridge configuration invalid");
  }
  const secret = config.secret;
  const tenantId = config.tenantId;
  if (typeof secret !== "string" || !SECRET_RE.test(secret)
    || typeof tenantId !== "string" || !TENANT_RE.test(tenantId)) {
    fail("bridge configuration invalid");
  }
  return { apiBaseUrl, secret, tenantId };
}

function responseStatus(response) {
  if (!response || !Number.isInteger(response.status)) fail("bridge request failed");
  if (response.status !== 200) fail("bridge request failed");
}

async function request(fetchImpl, url, init, signal) {
  let response;
  try {
    response = await fetchImpl(url, { ...init, ...(signal ? { signal } : {}) });
  } catch {
    fail("bridge request failed");
  }
  return response;
}

async function json(response) {
  if (!response || typeof response.json !== "function") fail("bridge response invalid");
  try { return await response.json(); } catch { fail("bridge response invalid"); }
}

function exactObject(value, keys) {
  return Boolean(value && typeof value === "object" && !Array.isArray(value)
    && Object.keys(value).sort().join(",") === keys.slice().sort().join(","));
}

function claimedDispatch(body, config) {
  if (!exactObject(body, ["dispatch"])) fail("bridge response invalid");
  if (body.dispatch === null) return null;
  const row = body.dispatch;
  if (!row || typeof row !== "object" || Array.isArray(row)
    || row.tenant_id !== config.tenantId
    || typeof row.dispatch_id !== "string" || !HEX64_RE.test(row.dispatch_id)
    || typeof row.job_id !== "string" || !/^goal:[0-9a-f]{64}$/.test(row.job_id)
    || !Number.isSafeInteger(row.round) || row.round < 1
    || row.status !== "claimed") {
    fail("bridge dispatch scope invalid");
  }
  return {
    tenant_id: row.tenant_id,
    dispatch_id: row.dispatch_id,
    job_id: row.job_id,
    round: row.round,
    status: row.status,
  };
}

function cookieFrom(response) {
  const headers = response && response.headers;
  const values = [];
  if (headers && typeof headers.getSetCookie === "function") values.push(...headers.getSetCookie());
  if (headers && typeof headers.raw === "function") values.push(...(headers.raw()["set-cookie"] || []));
  if (!values.length && headers && typeof headers.get === "function") {
    const value = headers.get("set-cookie");
    if (value) values.push(value);
  }
  for (const raw of values) {
    const match = String(raw).match(/(?:^|,\s*)(lm_panel_scope|lm_panel_session|__Host-lm_panel_session)=([^;,\s]+)/);
    if (match && COOKIE_NAMES.has(match[1])) return `${match[1]}=${match[2]}`;
  }
  fail("bridge guest cookie missing");
}

function expectedJobRef(tenantId, jobId) {
  return `runtime-job://${encodeURIComponent(tenantId)}/${encodeURIComponent(jobId)}`;
}

function expectedOpportunityRef(tenantId, opportunityId) {
  return `opportunity://${encodeURIComponent(tenantId)}/${encodeURIComponent(opportunityId)}`;
}

function workroomPacket(row, config, dispatch) {
  const opportunityId = dispatch.job_id.slice("goal:".length);
  const jobRef = expectedJobRef(config.tenantId, dispatch.job_id);
  if (!row || typeof row !== "object" || Array.isArray(row)
    || row.opportunity_id !== opportunityId
    || typeof row.title !== "string" || !row.title.trim() || row.title.length > 300
    || typeof row.source_url !== "string"
    || typeof row.status !== "string" || !row.status.trim() || row.status.length > 64
    || row.job_ref !== jobRef
    || (row.value_minor !== null && (typeof row.value_minor !== "string" || !MONEY_RE.test(row.value_minor)))
    || (row.currency !== null && (typeof row.currency !== "string" || !/^[A-Z]{3}$/.test(row.currency)))) {
    fail("bridge workroom scope invalid");
  }
  let source;
  try { source = new URL(row.source_url); } catch { fail("bridge workroom scope invalid"); }
  if (source.protocol !== "https:" || source.username || source.password) fail("bridge workroom scope invalid");
  return Object.freeze({
    protocol: "LM_DISPATCH_V1",
    tenant_id: dispatch.tenant_id,
    dispatch_id: dispatch.dispatch_id,
    job_id: dispatch.job_id,
    round: dispatch.round,
    opportunity_ref: expectedOpportunityRef(config.tenantId, opportunityId),
    job_ref: jobRef,
    title: row.title.trim(),
    source_url: row.source_url.trim(),
    value_minor: row.value_minor,
    currency: row.currency,
    workroom_status: row.status.trim(),
    result_protocol: "LM_RESULT_V1",
  });
}

async function claimMoneyPrinterWorkPacket(config, deps = {}) {
  const validated = validateConfig(config);
  const fetchImpl = deps.fetchImpl || globalThis.fetch;
  if (typeof fetchImpl !== "function") fail("bridge fetch unavailable");
  const signal = deps.signal || (typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function" ? AbortSignal.timeout(10_000) : undefined);
  const authHeaders = {
    accept: "application/json",
    authorization: `Bearer ${validated.secret}`,
    "content-type": "application/json",
  };

  const claim = await request(fetchImpl, `${validated.apiBaseUrl}${CLAIM_PATH}`, {
    method: "POST", headers: authHeaders, body: JSON.stringify({ tenant_id: validated.tenantId }),
  }, signal);
  responseStatus(claim);
  const dispatch = claimedDispatch(await json(claim), validated);
  if (dispatch === null) return Object.freeze({ status: "idle" });

  const guest = await request(fetchImpl, `${validated.apiBaseUrl}${GUEST_PATH}`, {
    method: "GET", headers: { accept: "text/html" },
  }, signal);
  responseStatus(guest);
  const cookie = cookieFrom(guest);
  const workroomUrl = `${validated.apiBaseUrl}${WORKROOM_PATH}?opportunity_id=${dispatch.job_id.slice("goal:".length)}`;
  const workroom = await request(fetchImpl, workroomUrl, {
    method: "GET", headers: { accept: "application/json", Cookie: cookie },
  }, signal);
  responseStatus(workroom);
  return Object.freeze({ status: "claimed", packet: workroomPacket(await json(workroom), validated, dispatch) });
}

function cliConfig(env = process.env) {
  return {
    apiBaseUrl: env.LM_SYMPHONY_API_BASE_URL || "",
    secret: env.LM_SYMPHONY_BRIDGE_SECRET || "",
    tenantId: env.LM_RUNTIME_TENANT_ID || "",
  };
}

async function main(env = process.env, deps = {}) {
  return claimMoneyPrinterWorkPacket(cliConfig(env), deps);
}

if (require.main === module) {
  main().then((result) => {
    process.stdout.write(`${JSON.stringify(result)}\n`);
  }).catch(() => {
    process.stderr.write("money printer bridge failed\n");
    process.exitCode = 1;
  });
}

module.exports = { claimMoneyPrinterWorkPacket, main };

