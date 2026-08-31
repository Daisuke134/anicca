"use strict";

const assert = require("node:assert/strict");
const { EventEmitter } = require("node:events");
const test = require("node:test");

const { handleMoneyPrinterSymphonyApiRequest } = require("./money-printer-symphony-api.js");

const SECRET = "s".repeat(64);
const TENANT = "tenant-a";
const FOREIGN_TENANT = "tenant-b";
const DISPATCH_ID = "d".repeat(64);
const JOB_ID = `goal:${"a".repeat(64)}`;
const RESULT_HASH = "e".repeat(64);
const ISSUE_REF = "github-issue://Daisuke134/life-manager-workrooms/1";
const RESULT_REF = "github-comment://Daisuke134/life-manager-workrooms/1/2";

function dispatch(status = "claimed", tenantId = TENANT) {
  return {
    tenant_id: tenantId,
    dispatch_id: DISPATCH_ID,
    job_id: JOB_ID,
    round: 1,
    status,
    issue_ref: status === "claimed" ? null : ISSUE_REF,
    result_ref: status === "result_ready" || status === "consumed" ? RESULT_REF : null,
    result_hash: status === "result_ready" || status === "consumed" ? RESULT_HASH : null,
    result_payload: null,
    failure_code: null,
    created_at: "2026-08-31T00:00:00.000Z",
    updated_at: "2026-08-31T00:00:00.000Z",
  };
}

function recoveryDispatch(status = "mirrored", overrides = {}) {
  const row = dispatch(status);
  if (status === "mirrored") {
    return { ...row, issue_closed_at: null, ...overrides };
  }
  return {
    ...row,
    result_payload: payload("completed"),
    issue_closed_at: status === "consumed" ? null : null,
    ...overrides,
  };
}

function payload(status = "completed", tenantId = TENANT) {
  return status === "completed"
    ? {
      protocol: "LM_RESULT_V1", tenant_id: tenantId, dispatch_id: DISPATCH_ID,
      job_id: JOB_ID, status, execution_id: "codex-round-1", artifact_refs: [],
    }
    : {
      protocol: "LM_RESULT_V1", tenant_id: tenantId, dispatch_id: DISPATCH_ID,
      job_id: JOB_ID, status, execution_id: "codex-round-1", artifact_refs: [],
      reason_code: "provider_interview", question: "Complete the provider interview.",
      required_format: { type: "confirmation" },
    };
}

function request(path, body, options = {}) {
  const req = new EventEmitter();
  req.url = path;
  req.method = options.method || "POST";
  req.headers = {
    "content-type": "application/json",
    authorization: `Bearer ${SECRET}`,
    ...(options.headers || {}),
  };
  const bodyText = typeof body === "string" ? body : JSON.stringify(body);
  process.nextTick(() => {
    if (bodyText) req.emit("data", Buffer.from(bodyText));
    req.emit("end");
  });
  return req;
}

function requestWithoutBody(path, options = {}) {
  const req = new EventEmitter();
  req.url = path;
  req.method = options.method || "POST";
  req.headers = {
    "content-type": "application/json",
    authorization: `Bearer ${SECRET}`,
    ...(options.headers || {}),
  };
  return req;
}

function responseCapture() {
  let resolve;
  const done = new Promise((r) => { resolve = r; });
  const res = {
    headersSent: false,
    statusCode: 200,
    headers: {},
    body: "",
    writeHead(code, headers = {}) {
      this.statusCode = code;
      this.headers = { ...headers };
      this.headersSent = true;
    },
    end(body = "") {
      this.body += Buffer.isBuffer(body) ? body.toString("utf8") : String(body);
      this.writableEnded = true;
      resolve(this);
    },
  };
  return { res, done };
}

async function call(path, body, options = {}, store = {}) {
  const req = request(path, body, options);
  const capture = responseCapture();
  const handled = handleMoneyPrinterSymphonyApiRequest(req, capture.res, {
    secret: SECRET,
    getRuntimeStore: () => store,
  });
  assert.notEqual(handled, false, "exact Symphony route must be handled");
  await handled;
  await capture.done;
  return { status: capture.res.statusCode, headers: capture.res.headers, body: JSON.parse(capture.res.body) };
}

test("valid claim returns a safe dispatch and calls the tenant-scoped store once", async () => {
  const calls = [];
  const store = {
    async claimSymphony(input) { calls.push(["claim", input]); return dispatch(); },
  };

  const result = await call("/api/internal/money-printer/symphony/claim", { tenant_id: TENANT }, {}, store);

  assert.equal(result.status, 200);
  assert.deepEqual(result.body, {
    dispatch: {
      tenant_id: TENANT,
      dispatch_id: DISPATCH_ID,
      job_id: JOB_ID,
      round: 1,
      status: "claimed",
      answered_human_boundaries: [],
    },
  });
  assert.deepEqual(calls, [["claim", { uid: TENANT }]]);
  assert.equal(result.body.dispatch.result_payload, undefined);
  assert.equal(result.body.dispatch.failure_code, undefined);
});

test("round2 claim propagates same-job answered boundaries and rejects malformed or foreign references", async () => {
  const answered = {
    uid: TENANT,
    job_id: JOB_ID,
    reason_code: "provider/interview",
    answer_ref: `vault-answer://${TENANT}/approve`,
    human_boundary_ref: `human-boundary://sha256/${"a".repeat(64)}`,
    version: 1,
    updated_at: "2026-08-31T00:00:00.000Z",
  };
  const row = { ...dispatch(), round: 2 };
  const calls = [];
  const result = await call("/api/internal/money-printer/symphony/claim", { tenant_id: TENANT }, {}, {
    async claimSymphony() { return row; },
    async readAnsweredForJob(input) { calls.push(input); return [answered]; },
  });

  assert.equal(result.status, 200);
  assert.deepEqual(result.body.dispatch, {
    tenant_id: TENANT,
    dispatch_id: DISPATCH_ID,
    job_id: JOB_ID,
    round: 2,
    status: "claimed",
    answered_human_boundaries: [{
      reason_code: "provider/interview",
      answer_ref: `vault-answer://${TENANT}/approve`,
      human_boundary_ref: `human-boundary://sha256/${"a".repeat(64)}`,
    }],
  });
  assert.deepEqual(calls, [{ uid: TENANT, job_id: JOB_ID }]);
  assert.doesNotMatch(JSON.stringify(result.body), /updated_at|private|secret/i);

  for (const invalidAnswered of [
    { ...answered, uid: FOREIGN_TENANT },
    { ...answered, answer_ref: `vault-answer://${FOREIGN_TENANT}/approve` },
    { ...answered, human_boundary_ref: "human-boundary://sha256/not-a-sha" },
    { ...answered, private_answer: "must not leak" },
  ]) {
    const invalidResult = await call("/api/internal/money-printer/symphony/claim", { tenant_id: TENANT }, {}, {
      async claimSymphony() { return row; },
      async readAnsweredForJob() { return [invalidAnswered]; },
    });
    assert.equal(invalidResult.status, 409);
    assert.deepEqual(invalidResult.body, { error: "conflict" });
  }
});

test("claim rejects non-empty round1 and empty round2 answered-boundary arrays", async () => {
  const answered = {
    uid: TENANT,
    job_id: JOB_ID,
    reason_code: "provider/interview",
    answer_ref: `vault-answer://${TENANT}/approve`,
    human_boundary_ref: `human-boundary://sha256/${"a".repeat(64)}`,
    version: 1,
    updated_at: "2026-08-31T00:00:00.000Z",
  };
  for (const [round, rows] of [[1, [answered]], [2, []]]) {
    let readCalls = 0;
    const result = await call("/api/internal/money-printer/symphony/claim", { tenant_id: TENANT }, {}, {
      async claimSymphony() { return { ...dispatch(), round }; },
      async readAnsweredForJob() { readCalls += 1; return rows; },
    });
    assert.equal(result.status, 409);
    assert.deepEqual(result.body, { error: "conflict" });
    assert.equal(readCalls, 1);
  }
});

test("claim recovery projects only base identifiers and durable issue ref", async () => {
  for (const status of ["mirrored", "result_ready", "consumed"]) {
    const row = recoveryDispatch(status);
    const result = await call("/api/internal/money-printer/symphony/claim", { tenant_id: TENANT }, {}, {
      async claimSymphony() { return row; },
    });
    assert.equal(result.status, 200);
    assert.deepEqual(result.body.dispatch, {
      tenant_id: TENANT,
      dispatch_id: DISPATCH_ID,
      job_id: JOB_ID,
      round: 1,
      status,
      issue_ref: ISSUE_REF,
      answered_human_boundaries: [],
    });
    assert.equal(result.body.result_ref, undefined);
    assert.equal(result.body.result_hash, undefined);
    assert.equal(result.body.result_payload, undefined);
    assert.equal(result.body.issue_closed_at, undefined);
  }
});

test("claim recovery rejects incoherent or foreign rows without exposing private fields", async () => {
  for (const row of [
    recoveryDispatch("mirrored", { tenant_id: FOREIGN_TENANT }),
    recoveryDispatch("mirrored", { result_ref: RESULT_REF }),
    recoveryDispatch("result_ready", { result_payload: null }),
    recoveryDispatch("result_ready", { issue_closed_at: "2026-08-31T00:00:00.000Z" }),
    recoveryDispatch("consumed", { issue_closed_at: "2026-08-31T00:00:00.000Z" }),
  ]) {
    const result = await call("/api/internal/money-printer/symphony/claim", { tenant_id: TENANT }, {}, {
      async claimSymphony() { return row; },
    });
    assert.equal(result.status, 409);
    assert.deepEqual(result.body, { error: "conflict" });
    assert.doesNotMatch(JSON.stringify(result.body), /private|secret/i);
  }

  const safeExtra = await call("/api/internal/money-printer/symphony/claim", { tenant_id: TENANT }, {}, {
    async claimSymphony() { return { ...recoveryDispatch("consumed"), private_payload: SECRET }; },
  });
  assert.equal(safeExtra.status, 200);
  assert.doesNotMatch(JSON.stringify(safeExtra.body), new RegExp(SECRET));
});

test("missing or wrong bearer is rejected before runtime store acquisition", async () => {
  for (const authorization of [undefined, "Bearer wrong", "Basic ignored"]) {
    const req = request(
      "/api/internal/money-printer/symphony/claim",
      { tenant_id: TENANT },
      { headers: authorization === undefined ? { authorization: undefined } : { authorization } },
    );
    const capture = responseCapture();
    let acquired = 0;
    const handled = handleMoneyPrinterSymphonyApiRequest(req, capture.res, {
      secret: SECRET,
      getRuntimeStore: () => { acquired += 1; return { claimSymphony: async () => { throw new Error("must not be called"); } }; },
    });
    assert.notEqual(handled, false);
    await handled;
    await capture.done;
    const result = { status: capture.res.statusCode, body: JSON.parse(capture.res.body) };
    assert.equal(result.status, 401);
    assert.deepEqual(result.body, { error: "unauthorized" });
    assert.equal(acquired, 0);
  }
});

test("missing or invalid configured secret fails closed without touching the store", async () => {
  for (const secret of [undefined, "short", "x".repeat(257), "bad secret"]) {
    const req = request("/api/internal/money-printer/symphony/claim", { tenant_id: TENANT });
    const capture = responseCapture();
    let acquired = 0;
    const handled = handleMoneyPrinterSymphonyApiRequest(req, capture.res, {
      secret,
      getRuntimeStore: () => { acquired += 1; return {}; },
    });
    assert.notEqual(handled, false);
    await handled;
    await capture.done;
    assert.equal(capture.res.statusCode, 503);
    assert.deepEqual(JSON.parse(capture.res.body), { error: "service_unavailable" });
    assert.equal(acquired, 0);
  }
});

test("strict body and media validation returns bounded generic errors", async () => {
  const cases = [
    { body: { tenant_id: TENANT, extra: true }, want: 400 },
    { body: { tenant_id: 42 }, want: 400 },
    { body: "{", want: 400 },
    { body: { tenant_id: TENANT }, headers: { "content-type": "text/plain" }, want: 415 },
    { body: "x".repeat(32769), want: 413 },
  ];
  for (const item of cases) {
    const result = await call(
      "/api/internal/money-printer/symphony/claim",
      item.body,
      { headers: item.headers },
      { claimSymphony: async () => { throw new Error("must not be called"); } },
    );
    assert.equal(result.status, item.want);
    assert.ok(typeof result.body.error === "string");
  }
});

test("oversize is rejected on the first data chunk without waiting for end and detaches stream listeners", async () => {
  const req = requestWithoutBody("/api/internal/money-printer/symphony/claim");
  let endEvents = 0;
  const observeEnd = () => { endEvents += 1; };
  req.on("end", observeEnd);
  const capture = responseCapture();
  const handled = handleMoneyPrinterSymphonyApiRequest(req, capture.res, {
    secret: SECRET,
    getRuntimeStore: () => ({ claimSymphony: async () => { throw new Error("must not be called"); } }),
  });
  req.emit("data", Buffer.alloc(32 * 1024 + 1));
  for (let i = 0; i < 100; i += 1) req.emit("data", Buffer.alloc(4096));
  const settled = await Promise.race([
    handled.then(() => true),
    new Promise((resolve) => setTimeout(() => resolve(false), 50)),
  ]);
  assert.equal(settled, true, "oversize must settle without an end event");
  await capture.done;
  req.removeListener("end", observeEnd);
  assert.equal(endEvents, 0);
  assert.equal(capture.res.statusCode, 413);
  assert.deepEqual(JSON.parse(capture.res.body), { error: "payload_too_large" });
  assert.equal(req.listenerCount("data"), 0);
  assert.equal(req.listenerCount("end"), 0);
  assert.equal(req.listenerCount("aborted"), 0);
  assert.equal(req.listenerCount("error"), 1, "one harmless error shield may remain for late socket errors");
  assert.doesNotThrow(() => req.emit("error", new Error("late socket error")));
  assert.doesNotThrow(() => req.emit("aborted"));
});

test("recognized Symphony routes reject non-POST methods", async () => {
  const result = await call(
    "/api/internal/money-printer/symphony/claim",
    {},
    { method: "GET" },
    { claimSymphony: async () => { throw new Error("must not be called"); } },
  );
  assert.equal(result.status, 405);
  assert.deepEqual(result.body, { error: "method_not_allowed" });
});

test("issue accepts only the exact body and returns no private dispatch fields", async () => {
  const calls = [];
  const store = {
    async recordSymphonyIssue(input) {
      calls.push(input);
      return dispatch("mirrored");
    },
  };
  const result = await call("/api/internal/money-printer/symphony/issue", {
    tenant_id: TENANT, dispatch_id: DISPATCH_ID, issue_ref: ISSUE_REF,
  }, {}, store);
  assert.equal(result.status, 200);
  assert.deepEqual(result.body, {
    tenant_id: TENANT, dispatch_id: DISPATCH_ID, job_id: JOB_ID,
    round: 1, status: "mirrored", issue_ref: ISSUE_REF,
  });
  assert.deepEqual(calls, [{ uid: TENANT, dispatchId: DISPATCH_ID, issueRef: ISSUE_REF }]);
  assert.equal(result.body.result_payload, undefined);
});

test("close acknowledges one exact consumed dispatch and projects a closed result", async () => {
  const calls = [];
  const consumed = {
    ...recoveryDispatch("consumed"),
    issue_closed_at: "2026-08-31T00:00:00.000Z",
  };
  const result = await call("/api/internal/money-printer/symphony/close", {
    tenant_id: TENANT,
    dispatch_id: DISPATCH_ID,
    issue_ref: ISSUE_REF,
    result_ref: RESULT_REF,
    result_hash: RESULT_HASH,
  }, {}, {
    async acknowledgeSymphonyIssueClosed(input) { calls.push(input); return consumed; },
  });
  assert.equal(result.status, 200);
  assert.deepEqual(result.body, {
    tenant_id: TENANT,
    dispatch_id: DISPATCH_ID,
    job_id: JOB_ID,
    status: "closed",
    issue_ref: ISSUE_REF,
    result_ref: RESULT_REF,
    result_hash: RESULT_HASH,
  });
  assert.deepEqual(calls, [{
    uid: TENANT,
    dispatchId: DISPATCH_ID,
    issueRef: ISSUE_REF,
    resultRef: RESULT_REF,
    resultHash: RESULT_HASH,
  }]);
  assert.equal(result.body.result_payload, undefined);
  assert.equal(result.body.issue_closed_at, undefined);
});

test("close requires exact body and a consumed row with a closed timestamp", async () => {
  const validBody = {
    tenant_id: TENANT,
    dispatch_id: DISPATCH_ID,
    issue_ref: ISSUE_REF,
    result_ref: RESULT_REF,
    result_hash: RESULT_HASH,
  };
  for (const body of [
    { ...validBody, extra: SECRET },
    { ...validBody, tenant_id: "Tenant-A" },
    { ...validBody, issue_ref: "github-issue://other/repo/2" },
  ]) {
    const result = await call("/api/internal/money-printer/symphony/close", body, {}, {
      acknowledgeSymphonyIssueClosed: async () => { throw new Error("must not be called"); },
    });
    assert.equal(result.status, 400);
    assert.deepEqual(result.body, { error: "invalid_request" });
  }
  for (const row of [
    { ...recoveryDispatch("consumed"), issue_closed_at: null },
    { ...recoveryDispatch("result_ready"), issue_closed_at: "2026-08-31T00:00:00.000Z" },
    { ...recoveryDispatch("consumed"), result_ref: "github-comment://Daisuke134/life-manager-workrooms/2/3", issue_closed_at: "2026-08-31T00:00:00.000Z" },
  ]) {
    const result = await call("/api/internal/money-printer/symphony/close", validBody, {}, {
      acknowledgeSymphonyIssueClosed: async () => row,
    });
    assert.equal(result.status, 409);
    assert.deepEqual(result.body, { error: "conflict" });
    assert.doesNotMatch(JSON.stringify(result.body), /secret|private/i);
  }
});

test("result completed records then consumes exactly once and returns a qualification-safe receipt", async () => {
  const calls = [];
  const resultDispatch = { ...dispatch("result_ready"), result_payload: payload("completed") };
  const consumed = { ...resultDispatch, status: "consumed" };
  const store = {
    async recordSymphonyResult(input) { calls.push(["record", input]); return resultDispatch; },
    async consumeSymphonyCompleted(input) { calls.push(["consume", input]); return consumed; },
  };
  const result = await call("/api/internal/money-printer/symphony/result", {
    tenant_id: TENANT,
    dispatch_id: DISPATCH_ID,
    repo: "Daisuke134/life-manager-workrooms",
    author: "Daisuke134",
    result_ref: RESULT_REF,
    result_hash: RESULT_HASH,
    payload: payload("completed"),
  }, {}, store);
  assert.equal(result.status, 200);
  assert.deepEqual(result.body, {
    tenant_id: TENANT, dispatch_id: DISPATCH_ID, job_id: JOB_ID,
    status: "consumed", result_ref: RESULT_REF, result_hash: RESULT_HASH,
  });
  assert.equal(calls.length, 2);
  assert.equal(calls[0][0], "record");
  assert.deepEqual(calls[1], ["consume", { uid: TENANT, dispatchId: DISPATCH_ID }]);
  assert.equal(JSON.stringify(result.body).includes(SECRET), false);
});

test("result needs_human consumes one existing task and exposes only its safe identity", async () => {
  const task = {
    uid: TENANT, task_id: "a".repeat(64), job_id: JOB_ID, version: 1,
    status: "open", question: "private", context_refs: { hidden: true },
  };
  const resultDispatch = { ...dispatch("result_ready"), result_payload: payload("needs_human") };
  const calls = [];
  const store = {
    async recordSymphonyResult(input) { calls.push(["record", input]); return resultDispatch; },
    async consumeSymphonyHumanTask(input) { calls.push(["consume", input]); return task; },
  };
  const result = await call("/api/internal/money-printer/symphony/result", {
    tenant_id: TENANT, dispatch_id: DISPATCH_ID,
    repo: "Daisuke134/life-manager-workrooms", author: "Daisuke134",
    result_ref: RESULT_REF, result_hash: RESULT_HASH, payload: payload("needs_human"),
  }, {}, store);
  assert.equal(result.status, 200);
  assert.deepEqual(result.body, {
    tenant_id: TENANT, dispatch_id: DISPATCH_ID, job_id: JOB_ID,
    status: "consumed", result_ref: RESULT_REF, result_hash: RESULT_HASH,
    task_id: task.task_id, task_status: "open", version: 1,
  });
  assert.equal(calls.length, 2);
});

test("result rejects wrong repository, author, tenant and stale store readback without consuming", async () => {
  const base = {
    tenant_id: TENANT, dispatch_id: DISPATCH_ID,
    repo: "Daisuke134/life-manager-workrooms", author: "Daisuke134",
    result_ref: RESULT_REF, result_hash: RESULT_HASH, payload: payload("completed"),
  };
  for (const body of [
    { ...base, repo: "someone/else" },
    { ...base, author: "SomeoneElse" },
    { ...base, tenant_id: FOREIGN_TENANT, payload: payload("completed", FOREIGN_TENANT) },
  ]) {
    let consumed = 0;
    const result = await call("/api/internal/money-printer/symphony/result", body, {}, {
      async recordSymphonyResult() { throw new Error("symphony result conflict"); },
      async consumeSymphonyCompleted() { consumed += 1; return {}; },
    });
    assert.equal(result.status, body.repo !== base.repo || body.author !== base.author ? 400 : 409);
    assert.equal(consumed, 0);
    assert.doesNotMatch(JSON.stringify(result.body), /SomeoneElse|someone\/else|private|secret/i);
  }
});

test("unexpected store failures return a generic 500 without reflecting the raw error", async () => {
  const result = await call("/api/internal/money-printer/symphony/claim", { tenant_id: TENANT }, {}, {
    async claimSymphony() { throw new Error("database password and raw connection failure"); },
  });
  assert.equal(result.status, 500);
  assert.deepEqual(result.body, { error: "internal_error" });
  assert.doesNotMatch(JSON.stringify(result.body), /database|password|connection/i);
});

test("duplicate completed callback reconciles an already-consumed row without consuming again", async () => {
  let consumeCalls = 0;
  let recordCalls = 0;
  const resultDispatch = { ...dispatch("result_ready"), result_payload: payload("completed") };
  const consumedDispatch = { ...resultDispatch, status: "consumed" };
  const store = {
    async recordSymphonyResult() {
      recordCalls += 1;
      return recordCalls === 1 ? resultDispatch : consumedDispatch;
    },
    async consumeSymphonyCompleted() {
      consumeCalls += 1;
      return consumedDispatch;
    },
  };
  const body = {
    tenant_id: TENANT, dispatch_id: DISPATCH_ID,
    repo: "Daisuke134/life-manager-workrooms", author: "Daisuke134",
    result_ref: RESULT_REF, result_hash: RESULT_HASH, payload: payload("completed"),
  };
  const first = await call("/api/internal/money-printer/symphony/result", body, {}, store);
  const second = await call("/api/internal/money-printer/symphony/result", body, {}, store);
  assert.equal(first.status, 200);
  assert.equal(second.status, 200);
  assert.deepEqual(second.body, {
    tenant_id: TENANT, dispatch_id: DISPATCH_ID, job_id: JOB_ID,
    status: "consumed", result_ref: RESULT_REF, result_hash: RESULT_HASH,
  });
  assert.equal(consumeCalls, 1);
});

test("duplicate needs_human callback reconciles safely without a second HumanTask query", async () => {
  let recordCalls = 0;
  let humanConsumeCalls = 0;
  const resultDispatch = { ...dispatch("result_ready"), result_payload: payload("needs_human") };
  const consumedDispatch = { ...resultDispatch, status: "consumed" };
  const task = { uid: TENANT, task_id: "a".repeat(64), job_id: JOB_ID, status: "open", version: 1 };
  const store = {
    async recordSymphonyResult() {
      recordCalls += 1;
      return recordCalls === 1 ? resultDispatch : consumedDispatch;
    },
    async consumeSymphonyHumanTask() {
      humanConsumeCalls += 1;
      return task;
    },
  };
  const body = {
    tenant_id: TENANT, dispatch_id: DISPATCH_ID,
    repo: "Daisuke134/life-manager-workrooms", author: "Daisuke134",
    result_ref: RESULT_REF, result_hash: RESULT_HASH, payload: payload("needs_human"),
  };
  const first = await call("/api/internal/money-printer/symphony/result", body, {}, store);
  const second = await call("/api/internal/money-printer/symphony/result", body, {}, store);
  assert.equal(first.status, 200);
  assert.equal(second.status, 200);
  assert.deepEqual(second.body, {
    tenant_id: TENANT, dispatch_id: DISPATCH_ID, job_id: JOB_ID,
    status: "consumed", result_ref: RESULT_REF, result_hash: RESULT_HASH,
  });
  assert.equal(humanConsumeCalls, 1);
});

test("exact Symphony paths are handled while nearby paths are left for the caller", async () => {
  const req = request("/api/internal/money-printer/symphony/unknown", {});
  const capture = responseCapture();
  assert.equal(handleMoneyPrinterSymphonyApiRequest(req, capture.res, { secret: SECRET, getRuntimeStore: () => ({}) }), false);
});
