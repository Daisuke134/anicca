#!/usr/bin/env node
"use strict";

const { execFileSync } = require("node:child_process");
const { createHash } = require("node:crypto");

const TENANT_RE = /^[a-z0-9][a-z0-9._-]{0,199}$/;
const HEX64_RE = /^[0-9a-f]{64}$/;
const SECRET_RE = /^[A-Za-z0-9_-]{32,256}$/;
const MONEY_RE = /^[0-9]+$/;
const CLAIM_PATH = "/api/internal/money-printer/symphony/claim";
const ISSUE_PATH = "/api/internal/money-printer/symphony/issue";
const RESULT_PATH = "/api/internal/money-printer/symphony/result";
const CLOSE_PATH = "/api/internal/money-printer/symphony/close";
const ISSUE_REPO = "Daisuke134/life-manager-workrooms";
const ISSUE_LABEL = "money-printer";
const ISSUE_URL_RE = /^https:\/\/github\.com\/Daisuke134\/life-manager-workrooms\/issues\/([1-9][0-9]*)$/;
const RESERVED_MARKER_PREFIX = "<!-- lm-dispatch:";
const RESULT_PREFIX = "LM_RESULT_V1\n";
const EXPECTED_RESULT_AUTHOR = "Daisuke134";
const MAX_COMMENT_AUTHOR_LENGTH = 100;
const JOB_ID_RE = /^[A-Za-z0-9][A-Za-z0-9._:\/-]{0,199}$/;
const EXECUTION_ID_RE = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$/;
const MACHINE_ID_RE = /^[A-Za-z0-9][A-Za-z0-9._:\/-]{0,199}$/;
const ANSWER_REF_RE = /^vault-answer:\/\/[a-z0-9][a-z0-9._-]{0,199}\/[A-Za-z0-9][A-Za-z0-9._~%-]{0,255}$/;
const HUMAN_BOUNDARY_REF_RE = /^human-boundary:\/\/sha256\/[0-9a-f]{64}$/;
const URI_REF_RE = /^[a-z][a-z0-9+.-]{1,31}:\/\/[A-Za-z0-9][A-Za-z0-9._~:/?#@!$&'()*+,;=%-]{0,999}$/;
const MAX_COMMENT_ROWS = 500;
const MAX_COMMENT_BODY_BYTES = 32 * 1024;
const MAX_REQUIRED_FORMAT_BYTES = 4096;
const MAX_RESULT_PAYLOAD_BYTES = 12 * 1024;
const DISPATCH_PACKET_KEYS = [
  "protocol", "tenant_id", "dispatch_id", "job_id", "round", "opportunity_ref", "job_ref",
  "title", "source_url", "value_minor", "currency", "workroom_status", "result_protocol", "answered_human_boundaries",
];
const ISSUE_STATE_KEYS = ["number", "url", "state"];
const RESULT_READBACK_KEYS = ["tenant_id", "dispatch_id", "job_id", "status", "result_ref", "result_hash"];
const HUMAN_RESULT_READBACK_KEYS = [...RESULT_READBACK_KEYS, "task_id", "task_status", "version"];
const PUBLIC_TEXT_RE = /^[^\u0000-\u001f\u007f]+$/;
const ISSUE_REF_RE = /^github-issue:\/\/Daisuke134\/life-manager-workrooms\/[1-9][0-9]*$/;
const CLAIM_BASE_KEYS = ["tenant_id", "dispatch_id", "job_id", "round", "status", "answered_human_boundaries", "workroom"];
const CLAIM_RECOVERY_KEYS = [...CLAIM_BASE_KEYS, "issue_ref"];
const CLOSE_READBACK_KEYS = ["tenant_id", "dispatch_id", "job_id", "status", "issue_ref", "result_ref", "result_hash"];
const RECOVERY_STATUSES = new Set(["mirrored", "result_ready", "consumed"]);

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
  if (typeof secret !== "string" || !SECRET_RE.test(secret)) {
    fail("bridge configuration invalid");
  }
  return { apiBaseUrl, secret };
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
    && Object.getPrototypeOf(value) === Object.prototype
    && Object.getOwnPropertySymbols(value).length === 0
    && Object.getOwnPropertyNames(value).sort().join(",") === keys.slice().sort().join(","));
}

function validateAnsweredHumanBoundaries(value, tenantId) {
  if (!Array.isArray(value) || Object.getPrototypeOf(value) !== Array.prototype
    || Object.getOwnPropertySymbols(value).length !== 0
    || Object.keys(value).length !== value.length || value.length > 100) {
    fail("answered human boundaries invalid");
  }
  return Object.freeze(value.map((row) => {
    if (!exactObject(row, ["reason_code", "answer_ref", "human_boundary_ref"])
      || typeof row.reason_code !== "string" || !MACHINE_ID_RE.test(row.reason_code)
      || typeof row.answer_ref !== "string" || !ANSWER_REF_RE.test(row.answer_ref)
      || !row.answer_ref.startsWith(`vault-answer://${tenantId}/`)
      || typeof row.human_boundary_ref !== "string" || !HUMAN_BOUNDARY_REF_RE.test(row.human_boundary_ref)) {
      fail("answered human boundaries invalid");
    }
    return Object.freeze({
      reason_code: row.reason_code,
      answer_ref: row.answer_ref,
      human_boundary_ref: row.human_boundary_ref,
    });
  }));
}

function validateBoundaryCardinality(round, boundaries) {
  if ((round === 1 && boundaries.length !== 0) || (round > 1 && boundaries.length === 0)) {
    fail("answered human boundaries round invalid");
  }
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
  const boundaries = validateAnsweredHumanBoundaries(packet.answered_human_boundaries, packet.tenant_id);
  validateBoundaryCardinality(packet.round, boundaries);
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
    comments(issueRef) {
      let issueNumber;
      const match = typeof issueRef === "string" ? issueRef.match(ISSUE_REF_RE) : null;
      if (!match) fail("issue comments failed");
      issueNumber = match[0].slice(`github-issue://${ISSUE_REPO}/`.length);
      const stdout = run([
        "api",
        `repos/${ISSUE_REPO}/issues/${issueNumber}/comments?per_page=100`,
      ], "issue comments failed");
      let parsed;
      try { parsed = JSON.parse(String(stdout || "")); } catch { fail("issue comments failed"); }
      return projectCommentRows(parsed, issueRef);
    },
    state(issueRef) {
      let issueNumber;
      const match = typeof issueRef === "string" ? issueRef.match(ISSUE_REF_RE) : null;
      if (!match) fail("issue state failed");
      issueNumber = match[0].slice(`github-issue://${ISSUE_REPO}/`.length);
      const stdout = run([
        "issue", "view", issueNumber,
        "-R", ISSUE_REPO,
        "--json", "number,url,state",
      ], "issue state failed");
      let parsed;
      try { parsed = JSON.parse(String(stdout || "")); } catch { fail("issue state failed"); }
      try { return validateIssueState(parsed, issueRef); } catch { fail("issue state failed"); }
    },
    close(issueRef) {
      const match = typeof issueRef === "string" ? issueRef.match(ISSUE_REF_RE) : null;
      if (!match) fail("issue close failed");
      const issueNumber = match[0].slice(`github-issue://${ISSUE_REPO}/`.length);
      run([
        "issue", "close", issueNumber,
        "-R", ISSUE_REPO,
        "--reason", "completed",
      ], "issue close failed");
    },
  };
}

function validateIssueState(value, issueRef) {
  const match = typeof issueRef === "string" ? issueRef.match(ISSUE_REF_RE) : null;
  if (!match) fail("issue state invalid");
  const issueNumber = match[0].slice(`github-issue://${ISSUE_REPO}/`.length);
  if (!exactObject(value, ISSUE_STATE_KEYS)
    || !Number.isSafeInteger(value.number) || value.number < 1
    || String(value.number) !== issueNumber
    || typeof value.url !== "string"
    || value.url !== `https://github.com/${ISSUE_REPO}/issues/${issueNumber}`
    || !["OPEN", "CLOSED"].includes(value.state)) {
    fail("issue state invalid");
  }
  return Object.freeze({ number: value.number, url: value.url, state: value.state });
}

function issueNumberFromRef(issueRef) {
  const match = typeof issueRef === "string" ? issueRef.match(ISSUE_REF_RE) : null;
  if (!match) fail("result comment scope invalid");
  return match[0].slice(`github-issue://${ISSUE_REPO}/`.length);
}

function commentUrlFor(issueNumber, id) {
  return `https://github.com/${ISSUE_REPO}/issues/${issueNumber}#issuecomment-${id}`;
}

function safeCommentBody(value) {
  return typeof value === "string"
    && Buffer.byteLength(value, "utf8") <= MAX_COMMENT_BODY_BYTES
    && !/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f\u0080-\u009f]/.test(value);
}

function validateCommentRow(row, issueRef) {
  const issueNumber = issueNumberFromRef(issueRef);
  const author = typeof row?.author === "string" ? row.author : "";
  if (!exactObject(row, ["id", "author", "body", "url"])
    || !Number.isSafeInteger(row.id) || row.id < 1
    || author.length > MAX_COMMENT_AUTHOR_LENGTH
    || typeof row.body !== "string"
    || row.url !== commentUrlFor(issueNumber, row.id)) {
    fail("issue comments failed");
  }
  if (author === EXPECTED_RESULT_AUTHOR && !safeCommentBody(row.body)) {
    fail("issue comments failed");
  }
  return Object.freeze({
    id: row.id,
    author: author === EXPECTED_RESULT_AUTHOR ? author : "",
    body: author === EXPECTED_RESULT_AUTHOR ? row.body : "",
    url: row.url,
  });
}

function flattenProjectedComments(value) {
  if (!Array.isArray(value)) fail("issue comments failed");
  if (value.some((entry) => Array.isArray(entry))) {
    if (value.length > MAX_COMMENT_ROWS || value.some((entry) => !Array.isArray(entry))) fail("issue comments failed");
    const flattened = [];
    for (const page of value) {
      if (page.length > MAX_COMMENT_ROWS || flattened.length + page.length > MAX_COMMENT_ROWS) {
        fail("issue comments failed");
      }
      flattened.push(...page);
    }
    return flattened;
  }
  if (value.length > MAX_COMMENT_ROWS) fail("issue comments failed");
  return value;
}

function projectCommentRows(rawRows, issueRef) {
  const rows = flattenProjectedComments(rawRows);
  return Object.freeze(rows.map((row) => {
    if (!row || typeof row !== "object" || Array.isArray(row)
      || Object.getPrototypeOf(row) !== Object.prototype
      || Object.getOwnPropertySymbols(row).length !== 0) {
      fail("issue comments failed");
    }
    const user = row.user;
    const author = user && typeof user === "object" && !Array.isArray(user)
      && Object.getPrototypeOf(user) === Object.prototype
      && Object.getOwnPropertySymbols(user).length === 0
      && typeof user.login === "string" ? user.login : "";
    return validateCommentRow({
      id: row.id,
      author,
      body: row.body,
      url: row.html_url,
    }, issueRef);
  }));
}

function validateCommentRows(rows, issueRef) {
  issueNumberFromRef(issueRef);
  return Object.freeze(flattenProjectedComments(rows).map((row) => validateCommentRow(row, issueRef)));
}

function safeJsonText(value) {
  return typeof value === "string" && !/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f\u0080-\u009f]/.test(value);
}

function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function canonicalValue(value) {
  if (Array.isArray(value)) {
    if (Object.getPrototypeOf(value) !== Array.prototype || Object.getOwnPropertySymbols(value).length !== 0
      || Object.keys(value).length !== value.length
      || Object.keys(value).some((key) => !/^(0|[1-9][0-9]*)$/.test(key) || Number(key) >= value.length)) {
      fail("result comment invalid");
    }
    return value.map(canonicalValue);
  }
  if (value && typeof value === "object") {
    if (Object.getPrototypeOf(value) !== Object.prototype || Object.getOwnPropertySymbols(value).length !== 0) {
      fail("result comment invalid");
    }
    const output = {};
    if (Object.getOwnPropertyNames(value).length !== Object.keys(value).length) fail("result comment invalid");
    for (const key of Object.keys(value).sort()) {
      Object.defineProperty(output, key, {
        configurable: true,
        enumerable: true,
        value: canonicalValue(value[key]),
        writable: true,
      });
    }
    return output;
  }
  return value;
}

function deepFreeze(value) {
  if (!value || typeof value !== "object" || Object.isFrozen(value)) return value;
  for (const child of Object.values(value)) deepFreeze(child);
  return Object.freeze(value);
}

function validateRequiredFormat(value) {
  if (typeof value === "string") {
    if (!safeJsonText(value)) fail("result comment invalid");
  } else if (Array.isArray(value)) {
    if (Object.getPrototypeOf(value) !== Array.prototype || Object.getOwnPropertySymbols(value).length !== 0
      || Object.keys(value).length !== value.length
      || Object.keys(value).some((key) => !/^(0|[1-9][0-9]*)$/.test(key) || Number(key) >= value.length)) {
      fail("result comment invalid");
    }
    for (const child of value) validateRequiredFormat(child);
  } else if (value && typeof value === "object") {
    if (Object.getPrototypeOf(value) !== Object.prototype || Object.getOwnPropertySymbols(value).length !== 0) {
      fail("result comment invalid");
    }
    if (Object.getOwnPropertyNames(value).length !== Object.keys(value).length) fail("result comment invalid");
    for (const [key, child] of Object.entries(value)) {
      if (!safeJsonText(key)) fail("result comment invalid");
      validateRequiredFormat(child);
    }
  } else if (typeof value === "number") {
    if (!Number.isFinite(value)) fail("result comment invalid");
  } else if (typeof value !== "boolean" && value !== null) {
    fail("result comment invalid");
  }
  let serialized;
  try { serialized = canonicalJson(value); } catch { fail("result comment invalid"); }
  if (Buffer.byteLength(serialized, "utf8") > MAX_REQUIRED_FORMAT_BYTES) fail("result comment invalid");
}

function validateResultPayload(payload, packet) {
  if (!payload || !exactObject(payload, [
    "protocol", "tenant_id", "dispatch_id", "job_id", "status", "execution_id", "artifact_refs",
  ]) && !exactObject(payload, [
    "protocol", "tenant_id", "dispatch_id", "job_id", "status", "execution_id", "artifact_refs",
    "reason_code", "question", "required_format",
  ])) {
    fail("result comment invalid");
  }
  const isHuman = payload.status === "needs_human";
  const expectedKeys = isHuman
    ? ["artifact_refs", "dispatch_id", "execution_id", "job_id", "protocol", "question", "reason_code", "required_format", "status", "tenant_id"]
    : ["artifact_refs", "dispatch_id", "execution_id", "job_id", "protocol", "status", "tenant_id"];
  if (Object.keys(payload).sort().join(",") !== expectedKeys.join(",")
    || payload.protocol !== "LM_RESULT_V1"
    || typeof payload.tenant_id !== "string" || !TENANT_RE.test(payload.tenant_id)
    || typeof payload.dispatch_id !== "string" || !HEX64_RE.test(payload.dispatch_id)
    || typeof payload.job_id !== "string" || !JOB_ID_RE.test(payload.job_id)
    || !["completed", "needs_human"].includes(payload.status)
    || typeof payload.execution_id !== "string" || !EXECUTION_ID_RE.test(payload.execution_id)
    || !Array.isArray(payload.artifact_refs) || payload.artifact_refs.length > 100
    || payload.artifact_refs.some((ref) => typeof ref !== "string" || Buffer.byteLength(ref, "utf8") > 1000 || !URI_REF_RE.test(ref))) {
    fail("result comment invalid");
  }
  if (packet && (payload.tenant_id !== packet.tenant_id
    || payload.dispatch_id !== packet.dispatch_id || payload.job_id !== packet.job_id)) {
    fail("result comment scope invalid");
  }
  if (isHuman) {
    if (typeof payload.reason_code !== "string" || !JOB_ID_RE.test(payload.reason_code)
      || typeof payload.question !== "string" || !payload.question.trim()
      || payload.question.length < 1 || payload.question.length > 2000 || !safeJsonText(payload.question)
      || (!Array.isArray(payload.required_format) && typeof payload.required_format !== "object"
        && typeof payload.required_format !== "string")
      || payload.required_format === null) {
      fail("result comment invalid");
    }
    validateRequiredFormat(payload.required_format);
    let requiredFormatJson;
    try { requiredFormatJson = canonicalJson(payload.required_format); } catch { fail("result comment invalid"); }
    if (Buffer.byteLength(requiredFormatJson, "utf8") > MAX_REQUIRED_FORMAT_BYTES) {
      fail("result comment invalid");
    }
  }
  return payload;
}

function canonicalResultPayload(payload) {
  const canonical = canonicalValue(payload);
  const serialized = canonicalJson(canonical);
  if (Buffer.byteLength(serialized, "utf8") > MAX_RESULT_PAYLOAD_BYTES) {
    fail("result comment invalid");
  }
  return { canonical, serialized };
}

function formatResultComment(payload) {
  const validated = validateResultPayload(payload);
  const { serialized } = canonicalResultPayload(validated);
  return `${RESULT_PREFIX}${serialized}`;
}

function parseResultBody(body, packet) {
  if (typeof body !== "string" || !body.startsWith("LM_RESULT_V1")) return null;
  if (!body.startsWith(RESULT_PREFIX)) fail("result comment conflict");
  const serialized = body.slice(RESULT_PREFIX.length);
  if (!serialized || serialized.trim() !== serialized || serialized[0] !== "{") {
    fail("result comment conflict");
  }
  let payload;
  try { payload = JSON.parse(serialized); } catch { fail("result comment conflict"); }
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) fail("result comment conflict");
  try {
    validateResultPayload(payload, packet);
    return canonicalResultPayload(payload).canonical;
  } catch {
    fail("result comment conflict");
  }
}

function parseResultComments(packet, issueRef, comments) {
  const validPacket = validateDispatchPacket(packet);
  const issueNumber = issueNumberFromRef(issueRef);
  const rows = validateCommentRows(comments, issueRef);
  const validResults = [];
  for (const row of rows) {
    if (row.author !== EXPECTED_RESULT_AUTHOR) continue;
    const payload = parseResultBody(row.body, validPacket);
    if (payload === null) continue;
    validResults.push({ row, payload });
  }
  if (validResults.length === 0) return Object.freeze({ status: "pending" });
  if (validResults.length !== 1) fail("result comment conflict");
  const [{ row, payload }] = validResults;
  const canonical = canonicalValue(payload);
  const serialized = canonicalJson(canonical);
  const resultHash = createHash("sha256").update(serialized, "utf8").digest("hex");
  return deepFreeze({
    status: "ready",
    result_ref: `github-comment://${ISSUE_REPO}/${issueNumber}/${row.id}`,
    result_hash: resultHash,
    payload: canonical,
  });
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
    const result = createIssueForPacket(validPacket, { issueClient, tenantId: validPacket.tenant_id });
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
      tenant_id: validPacket.tenant_id,
      dispatch_id: validPacket.dispatch_id,
      issue_ref: issueRef,
    }),
  }, signal);
  responseStatus(callback);
  const readback = mirroredIssueReadback(await json(callback), validPacket, issueRef);
  return Object.freeze({ ...readback, created });
}

function resultReadback(value, packet, ready) {
  const isHuman = ready.payload.status === "needs_human";
  const hasBaseShape = exactObject(value, RESULT_READBACK_KEYS);
  const hasHumanShape = isHuman && exactObject(value, HUMAN_RESULT_READBACK_KEYS);
  if (!hasBaseShape && !hasHumanShape) fail("result readback invalid");
  if (value.tenant_id !== packet.tenant_id
    || value.dispatch_id !== packet.dispatch_id
    || value.job_id !== packet.job_id
    || value.status !== "consumed"
    || value.result_ref !== ready.result_ref
    || value.result_hash !== ready.result_hash) {
    fail("result readback invalid");
  }
  if (hasHumanShape && (
    typeof value.task_id !== "string" || !HEX64_RE.test(value.task_id)
    || value.task_status !== "open"
    || !Number.isSafeInteger(value.version) || value.version < 1
  )) {
    fail("result readback invalid");
  }
  const safe = {
    tenant_id: value.tenant_id,
    dispatch_id: value.dispatch_id,
    job_id: value.job_id,
    result_ref: value.result_ref,
    result_hash: value.result_hash,
  };
  if (hasHumanShape) {
    safe.task_id = value.task_id;
    safe.task_status = value.task_status;
    safe.version = value.version;
  }
  return Object.freeze(safe);
}

function closedResult(packet, readback) {
  const result = {
    status: "closed",
    tenant_id: packet.tenant_id,
    dispatch_id: packet.dispatch_id,
    job_id: packet.job_id,
    result_ref: readback.result_ref,
    result_hash: readback.result_hash,
  };
  if (Object.prototype.hasOwnProperty.call(readback, "task_id")) {
    result.task_id = readback.task_id;
    result.task_status = readback.task_status;
    result.version = readback.version;
  }
  return Object.freeze(result);
}

function closeReadback(value, packet, issueRef, result) {
  if (!exactObject(value, CLOSE_READBACK_KEYS)
    || value.tenant_id !== packet.tenant_id
    || value.dispatch_id !== packet.dispatch_id
    || value.job_id !== packet.job_id
    || value.status !== "closed"
    || value.issue_ref !== issueRef
    || value.result_ref !== result.result_ref
    || value.result_hash !== result.result_hash) {
    fail("issue close ack invalid");
  }
  return Object.freeze({
    tenant_id: value.tenant_id,
    dispatch_id: value.dispatch_id,
    job_id: value.job_id,
    status: value.status,
    issue_ref: value.issue_ref,
    result_ref: value.result_ref,
    result_hash: value.result_hash,
  });
}

async function reconcileResultForIssue(config, packet, issueRef, deps = {}) {
  const validated = validateConfig(config);
  const validPacket = validateDispatchPacket(packet);
  const issueMatch = typeof issueRef === "string" ? issueRef.match(ISSUE_REF_RE) : null;
  if (!issueMatch) fail("issue result scope invalid");
  const issueClient = deps && deps.issueClient;
  if (!issueClient || typeof issueClient.comments !== "function"
    || typeof issueClient.state !== "function" || typeof issueClient.close !== "function") {
    fail("issue client unavailable");
  }

  let comments;
  try {
    comments = await issueClient.comments(issueRef);
  } catch {
    fail("issue comments failed");
  }
  let parsed;
  try {
    parsed = parseResultComments(validPacket, issueRef, comments);
  } catch {
    fail("result comment conflict");
  }
  if (parsed.status === "pending") {
    return Object.freeze({ status: "pending" });
  }
  if (!parsed || parsed.status !== "ready") fail("result comment conflict");

  const fetchImpl = deps.fetchImpl || globalThis.fetch;
  if (typeof fetchImpl !== "function") fail("bridge fetch unavailable");
  const signal = deps.signal || (typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function" ? AbortSignal.timeout(10_000) : undefined);
  const callback = await request(fetchImpl, `${validated.apiBaseUrl}${RESULT_PATH}`, {
    method: "POST",
    headers: {
      accept: "application/json",
      authorization: `Bearer ${validated.secret}`,
      "content-type": "application/json",
    },
    body: JSON.stringify({
      tenant_id: validPacket.tenant_id,
      dispatch_id: validPacket.dispatch_id,
      repo: ISSUE_REPO,
      author: EXPECTED_RESULT_AUTHOR,
      result_ref: parsed.result_ref,
      result_hash: parsed.result_hash,
      payload: parsed.payload,
    }),
  }, signal);
  responseStatus(callback);
  let readback;
  try {
    readback = resultReadback(await json(callback), validPacket, parsed);
  } catch {
    fail("result readback invalid");
  }

  let current;
  try {
    current = validateIssueState(await issueClient.state(issueRef), issueRef);
  } catch {
    fail("issue state failed");
  }
  if (current.state === "OPEN") {
    try {
      await issueClient.close(issueRef);
    } catch {
      fail("issue close failed");
    }
    try {
      current = validateIssueState(await issueClient.state(issueRef), issueRef);
    } catch {
      fail("issue state failed");
    }
    if (current.state !== "CLOSED") fail("issue close readback failed");
  } else if (current.state !== "CLOSED") {
    fail("issue state failed");
  }

  const closed = await request(fetchImpl, `${validated.apiBaseUrl}${CLOSE_PATH}`, {
    method: "POST",
    headers: {
      accept: "application/json",
      authorization: `Bearer ${validated.secret}`,
      "content-type": "application/json",
    },
    body: JSON.stringify({
      tenant_id: validPacket.tenant_id,
      dispatch_id: validPacket.dispatch_id,
      issue_ref: issueRef,
      result_ref: readback.result_ref,
      result_hash: readback.result_hash,
    }),
  }, signal);
  responseStatus(closed);
  try {
    closeReadback(await json(closed), validPacket, issueRef, readback);
  } catch {
    fail("issue close ack invalid");
  }
  return closedResult(validPacket, readback);
}

function claimedDispatch(body, config) {
  if (!exactObject(body, ["dispatch"])) fail("bridge response invalid");
  if (body.dispatch === null) return null;
  const row = body.dispatch;
  const status = row && typeof row === "object" && !Array.isArray(row) ? row.status : null;
  if (status !== "claimed" && !RECOVERY_STATUSES.has(status)) {
    fail("bridge dispatch scope invalid");
  }
  if (!exactObject(row, status === "claimed" ? CLAIM_BASE_KEYS : CLAIM_RECOVERY_KEYS)) {
    fail("bridge dispatch scope invalid");
  }
  if (!row || typeof row !== "object" || Array.isArray(row)
    || typeof row.tenant_id !== "string" || !TENANT_RE.test(row.tenant_id)
    || typeof row.dispatch_id !== "string" || !HEX64_RE.test(row.dispatch_id)
    || typeof row.job_id !== "string" || !/^goal:[0-9a-f]{64}$/.test(row.job_id)
    || !Number.isSafeInteger(row.round) || row.round < 1
    || (status !== "claimed" && (typeof row.issue_ref !== "string" || !ISSUE_REF_RE.test(row.issue_ref)))) {
    fail("bridge dispatch scope invalid");
  }
  const answeredHumanBoundaries = validateAnsweredHumanBoundaries(
    row.answered_human_boundaries,
    row.tenant_id,
  );
  validateBoundaryCardinality(row.round, answeredHumanBoundaries);
  const dispatch = {
    tenant_id: row.tenant_id,
    dispatch_id: row.dispatch_id,
    job_id: row.job_id,
    round: row.round,
    status: row.status,
    answered_human_boundaries: answeredHumanBoundaries,
    workroom: row.workroom,
  };
  if (status !== "claimed") dispatch.issue_ref = row.issue_ref;
  return dispatch;
}

function expectedJobRef(tenantId, jobId) {
  return `runtime-job://${encodeURIComponent(tenantId)}/${encodeURIComponent(jobId)}`;
}

function expectedOpportunityRef(tenantId, opportunityId) {
  return `opportunity://${encodeURIComponent(tenantId)}/${encodeURIComponent(opportunityId)}`;
}

function workroomPacket(row, config, dispatch) {
  const opportunityId = dispatch.job_id.slice("goal:".length);
  const jobRef = expectedJobRef(dispatch.tenant_id, dispatch.job_id);
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
    opportunity_ref: expectedOpportunityRef(dispatch.tenant_id, opportunityId),
    job_ref: jobRef,
    answered_human_boundaries: dispatch.answered_human_boundaries,
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
    method: "POST", headers: authHeaders, body: JSON.stringify({}),
  }, signal);
  responseStatus(claim);
  const dispatch = claimedDispatch(await json(claim), validated);
  if (dispatch === null) return Object.freeze({ status: "idle" });

  const result = {
    status: dispatch.status,
    packet: workroomPacket(dispatch.workroom, validated, dispatch),
  };
  if (dispatch.status !== "claimed") result.issue_ref = dispatch.issue_ref;
  return Object.freeze(result);
}

function cliConfig(env = process.env) {
  return {
    apiBaseUrl: env.LM_SYMPHONY_API_BASE_URL || "",
    secret: env.LM_SYMPHONY_BRIDGE_SECRET || "",
  };
}

async function main(env = process.env, deps = {}) {
  const config = cliConfig(env);
  const claimed = await claimMoneyPrinterWorkPacket(config, deps);
  if (!claimed || typeof claimed !== "object") fail("bridge dispatch invalid");
  if (claimed.status === "idle") return claimed;
  if (!claimed.packet || (claimed.status !== "claimed" && !RECOVERY_STATUSES.has(claimed.status))) {
    fail("bridge dispatch invalid");
  }
  const issueClient = deps.issueClient || createGhIssueClient();
  const issueDeps = { ...deps, issueClient };
  let issueRef;
  if (claimed.status === "claimed") {
    const issue = await reconcileIssueForPacket(config, claimed.packet, issueDeps);
    issueRef = issue.issue_ref;
  } else if (RECOVERY_STATUSES.has(claimed.status)
    && typeof claimed.issue_ref === "string" && ISSUE_REF_RE.test(claimed.issue_ref)) {
    issueRef = claimed.issue_ref;
  } else {
    fail("bridge dispatch invalid");
  }
  return reconcileResultForIssue(config, claimed.packet, issueRef, issueDeps);
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
  reconcileResultForIssue,
  formatResultComment,
  parseResultComments,
  main,
};
