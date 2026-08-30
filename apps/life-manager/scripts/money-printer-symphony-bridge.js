#!/usr/bin/env node
"use strict";

const { execFileSync } = require("node:child_process");

const TENANT_RE = /^[a-z0-9][a-z0-9._-]{0,199}$/;
const HEX64_RE = /^[0-9a-f]{64}$/;
const SECRET_RE = /^[A-Za-z0-9_-]{32,256}$/;
const MONEY_RE = /^[0-9]+$/;
const COOKIE_NAMES = new Set(["lm_panel_scope", "lm_panel_session", "__Host-lm_panel_session"]);
const CLAIM_PATH = "/api/internal/money-printer/symphony/claim";
const ISSUE_PATH = "/api/internal/money-printer/symphony/issue";
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
const ISSUE_REF_RE = /^github-issue:\/\/Daisuke134\/life-manager-workrooms\/[1-9][0-9]*$/;

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
  const run = (args, errorMessage) => {
    let stdout;
    try {
      stdout = exec("gh", args, {
        encoding: "utf8",
        stdio: ["ignore", "pipe", "pipe"],
      });
    } catch {
      fail(errorMessage);
    }
    return stdout;
  };
  return {
    create(issue) {
      const stdout = run([
        "issue", "create",
        "-R", ISSUE_REPO,
        "--title", issue.title,
        "--body", issue.body,
        "--label", ISSUE_LABEL,
      ], "issue create failed");
      const url = String(stdout || "").trim();
      if (!ISSUE_URL_RE.test(url)) fail("issue create failed");
      return url;
    },
    list() {
      const stdout = run([
        "issue", "list",
        "-R", ISSUE_REPO,
        "--state", "all",
        "--limit", "100",
        "--json", "number,url,body",
      ], "issue list failed");
      let parsed;
      try { parsed = JSON.parse(String(stdout || "")); } catch { fail("issue list failed"); }
      return validateIssueRows(parsed);
    },
  };
}

function validateIssueRow(row) {
  const urlMatch = row && typeof row === "object" && typeof row.url === "string"
    ? row.url.match(ISSUE_URL_RE) : null;
  if (!exactObject(row, ["number", "url", "body"])
    || Object.getPrototypeOf(row) !== Object.prototype
    || !Number.isSafeInteger(row.number) || row.number < 1
    || !urlMatch || urlMatch[1] !== String(row.number)
    || typeof row.body !== "string") {
    fail("issue list failed");
  }
  return Object.freeze({ number: row.number, url: row.url, body: row.body });
}

function validateIssueRows(rows) {
  if (!Array.isArray(rows) || rows.length > 100) fail("issue list failed");
  return Object.freeze(rows.map(validateIssueRow));
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

function issueRefFromUrl(url) {
  const match = typeof url === "string" ? url.match(ISSUE_URL_RE) : null;
  if (!match) fail("issue list failed");
  return `github-issue://${ISSUE_REPO}/${match[1]}`;
}

function issueMarker(dispatchId) {
  return `<!-- lm-dispatch:${dispatchId} -->`;
}

function issueRowsForMarker(rows, marker) {
  const matches = [];
  for (const row of rows) {
    const lines = row.body.split(/\r\n|\n|\r/);
    for (const line of lines) {
      if (line === marker) matches.push(row);
    }
  }
  return matches;
}

function mirroredIssueReadback(body, packet, issueRef) {
  const keys = ["tenant_id", "dispatch_id", "job_id", "round", "status", "issue_ref"];
  if (!exactObject(body, keys) || Object.getPrototypeOf(body) !== Object.prototype
    || body.tenant_id !== packet.tenant_id
    || body.dispatch_id !== packet.dispatch_id
    || body.job_id !== packet.job_id
    || body.round !== packet.round
    || body.status !== "mirrored"
    || body.issue_ref !== issueRef) {
    fail("issue readback invalid");
  }
  return {
    tenant_id: body.tenant_id,
    dispatch_id: body.dispatch_id,
    job_id: body.job_id,
    round: body.round,
    status: body.status,
    issue_ref: body.issue_ref,
  };
}

async function reconcileIssueForPacket(config, packet, deps = {}) {
  const validated = validateConfig(config);
  const validPacket = validateDispatchPacket(packet);
  if (validPacket.tenant_id !== validated.tenantId) fail("issue packet tenant scope invalid");
  const issueClient = deps && deps.issueClient;
  if (!issueClient || typeof issueClient.list !== "function" || typeof issueClient.create !== "function") {
    fail("issue client unavailable");
  }
  const fetchImpl = deps.fetchImpl || globalThis.fetch;
  if (typeof fetchImpl !== "function") fail("bridge fetch unavailable");
  const signal = deps.signal || (typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function" ? AbortSignal.timeout(10_000) : undefined);

  let rows;
  try {
    rows = issueClient.list();
  } catch {
    fail("issue list failed");
  }
  try {
    rows = validateIssueRows(rows);
  } catch {
    fail("issue list failed");
  }

  const matches = issueRowsForMarker(rows, issueMarker(validPacket.dispatch_id));
  if (matches.length > 1) fail("issue reconciliation conflict");

  let issueRef;
  let created = false;
  if (matches.length === 1) {
    if (matches[0].body !== buildMoneyPrinterIssue(validPacket).body) {
      fail("issue reconciliation conflict");
    }
    issueRef = issueRefFromUrl(matches[0].url);
  } else if (rows.length < 100) {
    const result = createIssueForPacket(validPacket, { issueClient, tenantId: validated.tenantId });
    if (!result || result.status !== "created" || result.dispatch_id !== validPacket.dispatch_id
      || typeof result.issue_ref !== "string" || !ISSUE_REF_RE.test(result.issue_ref)) {
      fail("issue create failed");
    }
    issueRef = result.issue_ref;
    created = true;
  } else {
    fail("issue list uncertain");
  }

  const authHeaders = {
    accept: "application/json",
    authorization: `Bearer ${validated.secret}`,
    "content-type": "application/json",
  };
  const callback = await request(fetchImpl, `${validated.apiBaseUrl}${ISSUE_PATH}`, {
    method: "POST",
    headers: authHeaders,
    body: JSON.stringify({
      tenant_id: validated.tenantId,
      dispatch_id: validPacket.dispatch_id,
      issue_ref: issueRef,
    }),
  }, signal);
  responseStatus(callback);
  const readback = mirroredIssueReadback(await json(callback), validPacket, issueRef);
  return Object.freeze({ ...readback, created });
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
  reconcileIssueForPacket,
  main,
};
