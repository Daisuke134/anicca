#!/usr/bin/env node
"use strict";

const { execFileSync } = require("node:child_process");

const TENANT_RE = /^[a-z0-9][a-z0-9._-]{0,199}$/;
const HEX64_RE = /^[0-9a-f]{64}$/;
const SECRET_RE = /^[A-Za-z0-9_-]{32,256}$/;
const MONEY_RE = /^[0-9]+$/;
const COOKIE_NAMES = new Set(["lm_panel_scope", "lm_panel_session", "__Host-lm_panel_session"]);
const CLAIM_PATH = "/api/internal/money-printer/symphony/claim";
const GUEST_PATH = "/money-printer";
const WORKROOM_PATH = "/api/panel/money-printer/workroom";
const ISSUE_REPO = "Daisuke134/life-manager-workrooms";
const ISSUE_LABEL = "money-printer";
const ISSUE_URL_RE = /^https:\/\/github\.com\/Daisuke134\/life-manager-workrooms\/issues\/([1-9][0-9]*)$/;
const RESERVED_MARKER_PREFIX = "<!-- lm-dispatch:";
const DISPATCH_PACKET_KEYS = [
  "protocol", "tenant_id", "dispatch_id", "job_id", "round", "opportunity_ref", "job_ref",
  "title", "source_url", "value_minor", "currency", "workroom_status", "result_protocol",
];
const PUBLIC_TEXT_RE = /^[^\u0000-\u001f\u007f]+$/;

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

function validateDispatchPacket(packet) {
  if (!exactObject(packet, DISPATCH_PACKET_KEYS) || !Object.isFrozen(packet)
    || Object.getPrototypeOf(packet) !== Object.prototype) {
    fail("issue packet invalid");
  }
  if (packet.protocol !== "LM_DISPATCH_V1"
    || typeof packet.tenant_id !== "string" || !TENANT_RE.test(packet.tenant_id)
    || typeof packet.dispatch_id !== "string" || !HEX64_RE.test(packet.dispatch_id)
    || typeof packet.job_id !== "string" || !/^goal:[0-9a-f]{64}$/.test(packet.job_id)
    || !Number.isSafeInteger(packet.round) || packet.round < 1
    || typeof packet.title !== "string" || !PUBLIC_TEXT_RE.test(packet.title)
    || packet.title.trim() !== packet.title || packet.title.length > 300
    || typeof packet.source_url !== "string" || !PUBLIC_TEXT_RE.test(packet.source_url)
    || packet.source_url.trim() !== packet.source_url
    || (packet.value_minor !== null && (typeof packet.value_minor !== "string" || !MONEY_RE.test(packet.value_minor)))
    || (packet.currency !== null && (typeof packet.currency !== "string" || !/^[A-Z]{3}$/.test(packet.currency)))
    || typeof packet.workroom_status !== "string" || !PUBLIC_TEXT_RE.test(packet.workroom_status)
    || packet.workroom_status.trim() !== packet.workroom_status || packet.workroom_status.length > 64
    || packet.result_protocol !== "LM_RESULT_V1") {
    fail("issue packet invalid");
  }
  if (DISPATCH_PACKET_KEYS.some((key) => typeof packet[key] === "string"
    && packet[key].includes(RESERVED_MARKER_PREFIX))) {
    fail("issue packet marker invalid");
  }
  let source;
  try { source = new URL(packet.source_url); } catch { fail("issue packet invalid"); }
  if (source.protocol !== "https:" || source.username || source.password) fail("issue packet invalid");
  if (packet.opportunity_ref !== `opportunity://${encodeURIComponent(packet.tenant_id)}/${packet.job_id.slice("goal:".length)}`
    || packet.job_ref !== expectedJobRef(packet.tenant_id, packet.job_id)) {
    fail("issue packet scope invalid");
  }
  return packet;
}

function buildMoneyPrinterIssue(packet) {
  const valid = validateDispatchPacket(packet);
  const titlePrefix = "[Money Printer] ";
  const titleSuffix = ` (${valid.dispatch_id})`;
  const title = `${titlePrefix}${valid.title.slice(0, 220 - titlePrefix.length - titleSuffix.length)}${titleSuffix}`;
  const marker = `<!-- lm-dispatch:${valid.dispatch_id} -->`;
  const fields = DISPATCH_PACKET_KEYS.map((key) => `- ${key}: ${JSON.stringify(valid[key])}`).join("\n");
  const body = [
    "## Money Printer workroom",
    "",
    marker,
    "",
    "Process this one dispatch in the assigned workroom.",
    "Return exactly one comment containing an LM_RESULT_V1 result.",
    "",
    fields,
  ].join("\n");
  const markers = body.match(/<!-- lm-dispatch:[0-9a-f]{64} -->/g) || [];
  if (markers.length !== 1 || markers[0] !== marker) fail("issue packet marker invalid");
  return Object.freeze({
    title,
    body,
    labels: Object.freeze([ISSUE_LABEL]),
  });
}

function createGhIssueClient(options = {}) {
  const exec = options && options.execFileSync || execFileSync;
  return {
    create(issue) {
      let stdout;
      try {
        stdout = exec("gh", [
          "issue", "create",
          "-R", ISSUE_REPO,
          "--title", issue.title,
          "--body", issue.body,
          "--label", ISSUE_LABEL,
        ], {
          encoding: "utf8",
          stdio: ["ignore", "pipe", "pipe"],
        });
      } catch {
        fail("issue create failed");
      }
      const url = String(stdout || "").trim();
      if (!ISSUE_URL_RE.test(url)) fail("issue create failed");
      return url;
    },
  };
}

function createIssueForPacket(packet, dependencies = {}) {
  const valid = validateDispatchPacket(packet);
  const tenantId = dependencies && dependencies.tenantId;
  if (typeof tenantId !== "string" || !TENANT_RE.test(tenantId) || tenantId !== valid.tenant_id) {
    fail("issue packet tenant scope invalid");
  }
  const issue = buildMoneyPrinterIssue(valid);
  const issueClient = dependencies && dependencies.issueClient;
  if (!issueClient || typeof issueClient.create !== "function") fail("issue client unavailable");
  let created;
  try {
    created = issueClient.create(issue);
  } catch {
    fail("issue create failed");
  }
  const url = typeof created === "string" ? created : created && created.url;
  const match = typeof url === "string" ? url.match(ISSUE_URL_RE) : null;
  if (!match) fail("issue create failed");
  return Object.freeze({
    status: "created",
    dispatch_id: valid.dispatch_id,
    issue_ref: `github-issue://${ISSUE_REPO}/${match[1]}`,
  });
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

module.exports = {
  claimMoneyPrinterWorkPacket,
  buildMoneyPrinterIssue,
  createGhIssueClient,
  createIssueForPacket,
  main,
};
