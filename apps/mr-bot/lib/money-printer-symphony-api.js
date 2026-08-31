"use strict";

const { timingSafeEqual } = require("node:crypto");
const { enqueueBrowserJob } = require("./browser-job-store.js");

const MAX_BODY_BYTES = 32 * 1024;
const SECRET_RE = /^[A-Za-z0-9_-]{32,256}$/;
const TENANT_RE = /^[a-z0-9][a-z0-9._-]{0,199}$/;
const DISPATCH_RE = /^[0-9a-f]{64}$/;
const JOB_RE = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$/;
const REASON_RE = /^[A-Za-z0-9][A-Za-z0-9._:\/-]{0,199}$/;
const ANSWER_REF_RE = /^vault-answer:\/\/[a-z0-9][a-z0-9._-]{0,199}\/[A-Za-z0-9][A-Za-z0-9._~%-]{0,255}$/;
const HUMAN_BOUNDARY_REF_RE = /^human-boundary:\/\/sha256\/[0-9a-f]{64}$/;
const ISSUE_RE = /^github-issue:\/\/Daisuke134\/mr-bot-workrooms\/[1-9][0-9]*$/;
const COMMENT_RE = /^github-comment:\/\/Daisuke134\/mr-bot-workrooms\/[1-9][0-9]*\/[1-9][0-9]*$/;
const ROUTES = new Map([
  ["/api/internal/money-printer/symphony/claim", "claim"],
  ["/api/internal/money-printer/symphony/issue", "issue"],
  ["/api/internal/money-printer/symphony/result", "result"],
  ["/api/internal/money-printer/symphony/close", "close"],
]);
const EXPECTED_REPO = "Daisuke134/life-manager-workrooms";
const EXPECTED_AUTHOR = "Daisuke134";

class RequestError extends Error {
  constructor(status, error) {
    super(error);
    this.status = status;
  }
}

function invalid() { throw new RequestError(400, "invalid_request"); }
function conflict() { throw new RequestError(409, "conflict"); }

function exactObject(value, keys) {
  return Boolean(value && typeof value === "object" && !Array.isArray(value)
    && Object.keys(value).sort().join(",") === keys.slice().sort().join(","));
}

function jsonResponse(res, status, body, extra = {}) {
  if (res.headersSent || res.writableEnded) return;
  res.writeHead(status, {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
    ...extra,
  });
  res.end(JSON.stringify(body));
}

function configuredSecret(secret) {
  return typeof secret === "string" && SECRET_RE.test(secret);
}

function authorized(req, expected) {
  const headers = req && req.headers;
  const supplied = headers && (headers.authorization || headers.Authorization);
  if (typeof supplied !== "string" || !supplied.startsWith("Bearer ")) return false;
  const actual = Buffer.from(supplied.slice("Bearer ".length), "utf8");
  const wanted = Buffer.from(expected, "utf8");
  return actual.length === wanted.length && timingSafeEqual(actual, wanted);
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let length = 0;
    let settled = false;
    const noop = () => {};
    const cleanup = () => {
      req.removeListener("data", onData);
      req.removeListener("end", onEnd);
      req.removeListener("error", onError);
      req.removeListener("aborted", onAborted);
      req.on("error", noop);
    };
    const fail = (error) => {
      if (settled) return;
      settled = true;
      chunks.length = 0;
      cleanup();
      reject(error);
    };
    const onData = (chunk) => {
      if (settled) return;
      const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(String(chunk));
      length += bytes.length;
      if (length > MAX_BODY_BYTES) {
        fail(new RequestError(413, "payload_too_large"));
        return;
      }
      chunks.push(bytes);
    };
    const onEnd = () => {
      if (settled) return;
      settled = true;
      const raw = Buffer.concat(chunks);
      chunks.length = 0;
      cleanup();
      try { resolve(JSON.parse(raw.toString("utf8"))); } catch { reject(new RequestError(400, "invalid_request")); }
    };
    const onError = () => fail(new RequestError(400, "invalid_request"));
    const onAborted = () => fail(new RequestError(400, "invalid_request"));
    req.on("data", onData);
    req.on("end", onEnd);
    req.on("error", onError);
    req.on("aborted", onAborted);
  });
}

function contentType(req) {
  const headers = req && req.headers;
  const value = headers && (headers["content-type"] || headers["Content-Type"]);
  return typeof value === "string" && /^application\/json(?:\s*;|$)/i.test(value.trim());
}

function validateClaim(body) {
  if (!exactObject(body, [])) invalid();
  return {};
}

function validateIssue(body) {
  if (!exactObject(body, ["tenant_id", "dispatch_id", "issue_ref"])
    || typeof body.tenant_id !== "string" || !TENANT_RE.test(body.tenant_id)
    || typeof body.dispatch_id !== "string" || !DISPATCH_RE.test(body.dispatch_id)
    || typeof body.issue_ref !== "string" || !ISSUE_RE.test(body.issue_ref)) invalid();
  return { uid: body.tenant_id, dispatchId: body.dispatch_id, issueRef: body.issue_ref };
}

function validateResult(body) {
  if (!exactObject(body, ["tenant_id", "dispatch_id", "repo", "author", "result_ref", "result_hash", "payload"])
    || typeof body.tenant_id !== "string" || !TENANT_RE.test(body.tenant_id)
    || typeof body.dispatch_id !== "string" || !DISPATCH_RE.test(body.dispatch_id)
    || body.repo !== EXPECTED_REPO || body.author !== EXPECTED_AUTHOR
    || typeof body.result_ref !== "string" || !COMMENT_RE.test(body.result_ref)
    || typeof body.result_hash !== "string" || !DISPATCH_RE.test(body.result_hash)
    || !body.payload || typeof body.payload !== "object" || Array.isArray(body.payload)
    || typeof body.payload.status !== "string" || !["completed", "needs_human"].includes(body.payload.status)) invalid();
  return {
    uid: body.tenant_id,
    dispatchId: body.dispatch_id,
    resultRef: body.result_ref,
    resultHash: body.result_hash,
    payload: body.payload,
  };
}

function validateClose(body) {
  if (!exactObject(body, ["tenant_id", "dispatch_id", "issue_ref", "result_ref", "result_hash"])
    || typeof body.tenant_id !== "string" || !TENANT_RE.test(body.tenant_id)
    || typeof body.dispatch_id !== "string" || !DISPATCH_RE.test(body.dispatch_id)
    || typeof body.issue_ref !== "string" || !ISSUE_RE.test(body.issue_ref)
    || typeof body.result_ref !== "string" || !COMMENT_RE.test(body.result_ref)
    || typeof body.result_hash !== "string" || !DISPATCH_RE.test(body.result_hash)) invalid();
  return {
    uid: body.tenant_id,
    dispatchId: body.dispatch_id,
    issueRef: body.issue_ref,
    resultRef: body.result_ref,
    resultHash: body.result_hash,
  };
}

function safeDispatch(row, expected, statuses) {
  const allowedStatuses = Array.isArray(statuses) ? statuses : [statuses];
  if (!row || typeof row !== "object" || Array.isArray(row)
    || row.tenant_id !== expected.uid || typeof row.dispatch_id !== "string" || !DISPATCH_RE.test(row.dispatch_id)
    || row.dispatch_id !== expected.dispatchId || typeof row.job_id !== "string" || !JOB_RE.test(row.job_id)
    || !Number.isInteger(row.round) || row.round < 1 || !allowedStatuses.includes(row.status)) conflict();
  return row;
}

function safeClaim(row, uid) {
  if (row === null) return null;
  const valid = safeDispatch(row, { uid, dispatchId: row && row.dispatch_id }, [
    "claimed", "mirrored", "result_ready", "consumed",
  ]);
  if (valid.failure_code != null) conflict();
  if (valid.status === "claimed") {
    if (valid.issue_ref != null || valid.result_ref != null || valid.result_hash != null
      || valid.result_payload != null || valid.issue_closed_at != null) conflict();
  } else {
    if (typeof valid.issue_ref !== "string" || !ISSUE_RE.test(valid.issue_ref)) conflict();
    if (valid.status === "mirrored") {
      if (valid.result_ref != null || valid.result_hash != null || valid.result_payload != null
        || valid.issue_closed_at != null) conflict();
    } else if (typeof valid.result_ref !== "string" || !COMMENT_RE.test(valid.result_ref)
      || typeof valid.result_hash !== "string" || !DISPATCH_RE.test(valid.result_hash)
      || !valid.result_payload || typeof valid.result_payload !== "object"
      || Array.isArray(valid.result_payload)
      || !["completed", "needs_human"].includes(valid.result_payload.status)
      || valid.issue_closed_at != null) conflict();
  }
  const safe = {
    tenant_id: valid.tenant_id,
    dispatch_id: valid.dispatch_id,
    job_id: valid.job_id,
    round: valid.round,
    status: valid.status,
  };
  if (valid.status !== "claimed") safe.issue_ref = valid.issue_ref;
  return safe;
}

function answeredHumanBoundaries(rows, expected) {
  if (!Array.isArray(rows)) conflict();
  return Object.freeze(rows.map((row) => {
    if (!exactObject(row, ["uid", "job_id", "reason_code", "answer_ref", "human_boundary_ref", "version", "updated_at"])
      || Object.getPrototypeOf(row) !== Object.prototype || Object.getOwnPropertySymbols(row).length !== 0
      || row.uid !== expected.uid || row.job_id !== expected.jobId
      || typeof row.reason_code !== "string" || !REASON_RE.test(row.reason_code)
      || typeof row.answer_ref !== "string" || !ANSWER_REF_RE.test(row.answer_ref)
      || !row.answer_ref.startsWith(`vault-answer://${expected.uid}/`)
      || typeof row.human_boundary_ref !== "string" || !HUMAN_BOUNDARY_REF_RE.test(row.human_boundary_ref)
      || !Number.isInteger(row.version) || row.version < 1
      || !((typeof row.updated_at === "string" || row.updated_at instanceof Date)
        && Number.isFinite(Date.parse(row.updated_at)))) {
      conflict();
    }
    return Object.freeze({
      reason_code: row.reason_code,
      answer_ref: row.answer_ref,
      human_boundary_ref: row.human_boundary_ref,
    });
  }));
}

async function safeClaimWithAnswered(row, uid, store) {
  const expectedUid = uid || row && row.tenant_id;
  if (row !== null && (typeof expectedUid !== "string" || !TENANT_RE.test(expectedUid))) conflict();
  const safe = safeClaim(row, expectedUid);
  if (safe === null) return null;
  const rows = typeof store.readAnsweredForJob === "function"
    ? await store.readAnsweredForJob({ uid: safe.tenant_id, job_id: safe.job_id })
    : safe.round === 1 ? [] : null;
  const answered = answeredHumanBoundaries(rows, { uid: safe.tenant_id, jobId: safe.job_id });
  if ((safe.round === 1 && answered.length !== 0) || (safe.round > 1 && answered.length === 0)) conflict();
  if (typeof store.readOpportunity !== "function") conflict();
  const opportunityId = safe.job_id.slice("goal:".length);
  const opportunity = await store.readOpportunity({
    uid: safe.tenant_id,
    opportunity_id: opportunityId,
    goal_ref: `intent-entry://${safe.tenant_id}/${opportunityId}`,
  });
  if (!opportunity || opportunity.uid !== safe.tenant_id
    || opportunity.opportunity_id !== opportunityId
    || typeof opportunity.title !== "string" || !opportunity.title.trim() || opportunity.title.length > 300
    || typeof opportunity.source_url !== "string" || !opportunity.source_url.trim()
    || typeof opportunity.status !== "string" || !opportunity.status.trim() || opportunity.status.length > 64
    || (opportunity.value_minor !== null && (typeof opportunity.value_minor !== "string" || !/^[0-9]+$/.test(opportunity.value_minor)))
    || (opportunity.currency !== null && (typeof opportunity.currency !== "string" || !/^[A-Z]{3}$/.test(opportunity.currency)))) conflict();
  let source;
  try { source = new URL(opportunity.source_url); } catch { conflict(); }
  if (source.protocol !== "https:" || source.username || source.password) conflict();
  const workroom = Object.freeze({
    opportunity_id: opportunityId,
    title: opportunity.title.trim(),
    source_url: opportunity.source_url.trim(),
    value_minor: opportunity.value_minor,
    currency: opportunity.currency,
    status: opportunity.status.trim(),
    job_ref: `runtime-job://${encodeURIComponent(safe.tenant_id)}/${encodeURIComponent(safe.job_id)}`,
  });
  return Object.freeze({ ...safe, answered_human_boundaries: answered, workroom });
}

function safeIssue(row, input) {
  const valid = safeDispatch(row, { uid: input.uid, dispatchId: input.dispatchId }, ["mirrored"]);
  if (valid.issue_ref !== input.issueRef || valid.result_ref != null || valid.result_hash != null) conflict();
  return {
    tenant_id: valid.tenant_id,
    dispatch_id: valid.dispatch_id,
    job_id: valid.job_id,
    round: valid.round,
    status: valid.status,
    issue_ref: valid.issue_ref,
  };
}

function safeResult(row, input, statuses) {
  const valid = safeDispatch(row, { uid: input.uid, dispatchId: input.dispatchId }, Array.isArray(statuses) ? statuses : [statuses]);
  if (valid.result_ref !== input.resultRef || valid.result_hash !== input.resultHash
    || !valid.result_payload || valid.result_payload.status !== input.payload.status) conflict();
  return valid;
}

function safeClosed(row, input) {
  const valid = safeDispatch(row, { uid: input.uid, dispatchId: input.dispatchId }, ["consumed"]);
  if (valid.issue_ref !== input.issueRef || valid.result_ref !== input.resultRef
    || valid.result_hash !== input.resultHash || valid.failure_code != null
    || valid.issue_closed_at == null || !valid.result_payload
    || typeof valid.result_payload !== "object" || Array.isArray(valid.result_payload)
    || !["completed", "needs_human"].includes(valid.result_payload.status)) conflict();
  return {
    tenant_id: valid.tenant_id,
    dispatch_id: valid.dispatch_id,
    job_id: valid.job_id,
    status: "closed",
    issue_ref: valid.issue_ref,
    result_ref: valid.result_ref,
    result_hash: valid.result_hash,
  };
}

function safeTask(task, expected) {
  if (!task || typeof task !== "object" || Array.isArray(task)
    || task.uid !== expected.uid || task.job_id !== expected.jobId
    || typeof task.task_id !== "string" || !DISPATCH_RE.test(task.task_id)
    || task.status !== "open" || !Number.isInteger(task.version) || task.version < 1) conflict();
  return task;
}

function storeFor(getRuntimeStore) {
  if (typeof getRuntimeStore !== "function") throw new Error("runtime store unavailable");
  const store = getRuntimeStore();
  if (!store || typeof store !== "object") throw new Error("runtime store unavailable");
  return store;
}

async function ensureProviderInterviewBrowser(store, input, jobId) {
  if (input.payload.status !== "needs_human" || input.payload.reason_code !== "provider_interview") return;
  const opportunityId = String(jobId).slice("goal:".length);
  if (!DISPATCH_RE.test(opportunityId) || typeof store.readOpportunity !== "function") conflict();
  const opportunity = await store.readOpportunity({
    uid: input.uid,
    opportunity_id: opportunityId,
    goal_ref: `intent-entry://${input.uid}/${opportunityId}`,
  });
  let source;
  try { source = new URL(opportunity && opportunity.source_url); } catch { conflict(); }
  if (source.protocol !== "https:" || source.username || source.password) conflict();
  source.search = ""; source.hash = "";
  const enqueue = typeof store.enqueueBrowserJob === "function"
    ? store.enqueueBrowserJob.bind(store)
    : enqueueBrowserJob;
  const queued = await enqueue({
    uid: input.uid,
    chatId: "money-printer",
    messageId: input.dispatchId,
    updateId: jobId,
    rawPrompt: "Open the provider page and prepare the provider interview. Stop at the human-only step.",
    classification: {
      goal: `Open ${source.toString()} and prepare the provider interview. Stop at login, OTP, CAPTCHA, KYC, camera, microphone, or personal-experience questions.`,
      actionKind: "provider_interview_handoff",
      locale: "en",
      requiresLogin: true,
      principalKind: "user_provided",
    },
  });
  if (!queued || !queued.job || queued.job.uid !== input.uid
    || queued.job.telegram_message_id !== input.dispatchId) conflict();
}

function classify(error) {
  if (error instanceof RequestError) return error.status;
  const message = String(error && error.message || "");
  if (/readback|conflict|stale|foreign|symphony.*unavailable/i.test(message)) return 409;
  if (/invalid/i.test(message)) return 400;
  return 500;
}

async function processRequest(action, req, res, dependencies) {
  const secret = dependencies && dependencies.secret;
  if (!configuredSecret(secret)) {
    jsonResponse(res, 503, { error: "service_unavailable" });
    return;
  }
  if (!authorized(req, secret)) {
    jsonResponse(res, 401, { error: "unauthorized" });
    return;
  }
  if (req.method !== "POST") {
    jsonResponse(res, 405, { error: "method_not_allowed" }, { allow: "POST" });
    return;
  }
  if (!contentType(req)) {
    jsonResponse(res, 415, { error: "unsupported_media_type" });
    return;
  }
  try {
    const body = await readJson(req);
    const input = action === "claim" ? validateClaim(body)
      : action === "issue" ? validateIssue(body)
        : action === "result" ? validateResult(body) : validateClose(body);
    const store = storeFor(dependencies && dependencies.getRuntimeStore);
    if (action === "claim") {
      const row = await store.claimSymphonyNext(input);
      jsonResponse(res, 200, { dispatch: await safeClaimWithAnswered(row, null, store) });
      return;
    }
    if (action === "issue") {
      const row = await store.recordSymphonyIssue(input);
      jsonResponse(res, 200, safeIssue(row, input));
      return;
    }
    if (action === "close") {
      const row = await store.acknowledgeSymphonyIssueClosed(input);
      jsonResponse(res, 200, safeClosed(row, input));
      return;
    }
    const row = await store.recordSymphonyResult(input);
    const ready = safeResult(row, input, ["result_ready", "consumed"]);
    if (ready.status === "consumed") {
      await ensureProviderInterviewBrowser(store, input, ready.job_id);
      jsonResponse(res, 200, {
        tenant_id: ready.tenant_id,
        dispatch_id: ready.dispatch_id,
        job_id: ready.job_id,
        status: ready.status,
        result_ref: ready.result_ref,
        result_hash: ready.result_hash,
      });
      return;
    }
    if (input.payload.status === "completed") {
      const consumed = await store.consumeSymphonyCompleted({ uid: input.uid, dispatchId: input.dispatchId });
      const finalRow = safeResult(consumed, input, "consumed");
      jsonResponse(res, 200, {
        tenant_id: finalRow.tenant_id,
        dispatch_id: finalRow.dispatch_id,
        job_id: finalRow.job_id,
        status: finalRow.status,
        result_ref: ready.result_ref,
        result_hash: ready.result_hash,
      });
      return;
    }
    const task = safeTask(await store.consumeSymphonyHumanTask({ uid: input.uid, dispatchId: input.dispatchId }), {
      uid: input.uid, jobId: ready.job_id,
    });
    await ensureProviderInterviewBrowser(store, input, ready.job_id);
    jsonResponse(res, 200, {
      tenant_id: ready.tenant_id,
      dispatch_id: ready.dispatch_id,
      job_id: ready.job_id,
      status: "consumed",
      result_ref: ready.result_ref,
      result_hash: ready.result_hash,
      task_id: task.task_id,
      task_status: task.status,
      version: task.version,
    });
  } catch (error) {
    const status = classify(error);
    jsonResponse(res, status, {
      error: status === 400 ? "invalid_request" : status === 409 ? "conflict"
        : status === 413 ? "payload_too_large" : "internal_error",
    });
  }
}

function handleMoneyPrinterSymphonyApiRequest(req, res, dependencies = {}) {
  const path = String(req && req.url || "").split("?", 1)[0];
  const action = ROUTES.get(path);
  if (!action) return false;
  return processRequest(action, req, res, dependencies);
}

module.exports = { handleMoneyPrinterSymphonyApiRequest };
