"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { claimMoneyPrinterWorkPacket } = require("./money-printer-symphony-bridge.js");

const SECRET = "s".repeat(64);
const TENANT = "tenant-a";
const FOREIGN_TENANT = "tenant-b";
const OPPORTUNITY_ID = "a".repeat(64);
const FOREIGN_OPPORTUNITY_ID = "b".repeat(64);
const DISPATCH_ID = "d".repeat(64);
const JOB_ID = `goal:${OPPORTUNITY_ID}`;
const COOKIE = "__Host-lm_panel_session=session-secret";
const BASE = "https://life-call.example.test";

function response(status, body, headers = {}) {
  const values = new Map(Object.entries(headers).map(([key, value]) => [key.toLowerCase(), value]));
  return {
    status,
    ok: status >= 200 && status < 300,
    headers: {
      get(name) { return values.get(String(name).toLowerCase()) || null; },
      getSetCookie() {
        const value = values.get("set-cookie");
        return value == null ? [] : (Array.isArray(value) ? value : [value]);
      },
    },
    async json() { return body; },
  };
}

function dispatch(overrides = {}) {
  return {
    tenant_id: TENANT,
    dispatch_id: DISPATCH_ID,
    job_id: JOB_ID,
    round: 1,
    status: "claimed",
    private_payload: SECRET,
    ...overrides,
  };
}

function workroom(overrides = {}) {
  return {
    opportunity_id: OPPORTUNITY_ID,
    title: "A bounded opportunity",
    source_url: "https://example.test/opportunity",
    value_minor: "2500",
    currency: "USD",
    status: "WORKING",
    job_ref: `runtime-job://${encodeURIComponent(TENANT)}/${encodeURIComponent(JOB_ID)}`,
    activity: [{ kind: "private", secret: SECRET }],
    ...overrides,
  };
}

function fakeFetch(steps, calls = []) {
  return async (url, init = {}) => {
    calls.push({ url: String(url), init });
    const step = steps.shift();
    if (!step) throw new Error("unexpected fetch");
    return typeof step === "function" ? step(url, init) : step;
  };
}

function config(overrides = {}) {
  return { apiBaseUrl: BASE, secret: SECRET, tenantId: TENANT, ...overrides };
}

test("idle claim returns frozen idle state and makes no guest request", async () => {
  const calls = [];
  const result = await claimMoneyPrinterWorkPacket(config(), {
    fetchImpl: fakeFetch([response(200, { dispatch: null })], calls),
  });

  assert.deepEqual(result, { status: "idle" });
  assert.equal(Object.isFrozen(result), true);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, `${BASE}/api/internal/money-printer/symphony/claim`);
  assert.equal(calls[0].init.method, "POST");
  assert.deepEqual(JSON.parse(calls[0].init.body), { tenant_id: TENANT });
  assert.equal(calls[0].init.headers.authorization, `Bearer ${SECRET}`);
});

test("claimed dispatch produces one safe packet after exactly two guest/workroom GETs", async () => {
  const calls = [];
  const result = await claimMoneyPrinterWorkPacket(config(), {
    fetchImpl: fakeFetch([
      response(200, { dispatch: dispatch() }),
      response(200, "<private html>", { "set-cookie": COOKIE }),
      response(200, workroom()),
    ], calls),
  });

  const expected = {
    status: "claimed",
    packet: {
      protocol: "LM_DISPATCH_V1",
      tenant_id: TENANT,
      dispatch_id: DISPATCH_ID,
      job_id: JOB_ID,
      round: 1,
      opportunity_ref: `opportunity://${encodeURIComponent(TENANT)}/${encodeURIComponent(OPPORTUNITY_ID)}`,
      job_ref: `runtime-job://${encodeURIComponent(TENANT)}/${encodeURIComponent(JOB_ID)}`,
      title: "A bounded opportunity",
      source_url: "https://example.test/opportunity",
      value_minor: "2500",
      currency: "USD",
      workroom_status: "WORKING",
      result_protocol: "LM_RESULT_V1",
    },
  };
  assert.deepEqual(result, expected);
  assert.equal(Object.isFrozen(result), true);
  assert.equal(Object.isFrozen(result.packet), true);
  assert.equal(calls.length, 3);
  assert.equal(calls[1].url, `${BASE}/money-printer`);
  assert.equal(calls[1].init.method, "GET");
  assert.equal(calls[2].url, `${BASE}/api/panel/money-printer/workroom?opportunity_id=${OPPORTUNITY_ID}`);
  assert.equal(calls[2].init.method, "GET");
  assert.equal(calls[2].init.headers.Cookie, COOKIE);
  assert.doesNotMatch(JSON.stringify(result), /private|secret|session/);
});

test("foreign or malformed claimed dispatch stops before either guest GET", async () => {
  for (const invalidDispatch of [
    dispatch({ tenant_id: FOREIGN_TENANT }),
    dispatch({ dispatch_id: "not-a-dispatch" }),
    dispatch({ job_id: "goal:not-a-64-hex-id" }),
    dispatch({ round: 0 }),
    dispatch({ status: "mirrored" }),
  ]) {
    const calls = [];
    await assert.rejects(
      claimMoneyPrinterWorkPacket(config(), {
        fetchImpl: fakeFetch([response(200, { dispatch: invalidDispatch })], calls),
      }),
      /invalid|scope|dispatch/i,
    );
    assert.equal(calls.length, 1);
  }
});

test("missing guest cookie is a generic failure and prevents workroom access", async () => {
  const calls = [];
  await assert.rejects(
    claimMoneyPrinterWorkPacket(config(), {
      fetchImpl: fakeFetch([
        response(200, { dispatch: dispatch() }),
        response(200, "<private html>"),
      ], calls),
    }),
    /cookie|guest/i,
  );
  assert.equal(calls.length, 2);
});

test("foreign or mixed workroom is rejected after claim without returning its fields", async () => {
  for (const invalidWorkroom of [
    workroom({ opportunity_id: FOREIGN_OPPORTUNITY_ID }),
    workroom({ job_ref: `runtime-job://${encodeURIComponent(FOREIGN_TENANT)}/${encodeURIComponent(JOB_ID)}` }),
  ]) {
    const calls = [];
    await assert.rejects(
      claimMoneyPrinterWorkPacket(config(), {
        fetchImpl: fakeFetch([
          response(200, { dispatch: dispatch() }),
          response(200, "<private html>", { "set-cookie": COOKIE }),
          response(200, invalidWorkroom),
        ], calls),
      }),
      /workroom|scope|opportunity/i,
    );
    assert.equal(calls.length, 3);
  }
});

test("invalid config fails before network and exported function emits no stdout or stderr", async () => {
  const calls = [];
  let stdout = "";
  let stderr = "";
  const stdoutWrite = process.stdout.write;
  const stderrWrite = process.stderr.write;
  process.stdout.write = (chunk) => { stdout += String(chunk); return true; };
  process.stderr.write = (chunk) => { stderr += String(chunk); return true; };
  try {
    await assert.rejects(
      claimMoneyPrinterWorkPacket(config({ apiBaseUrl: "http://insecure.example.test" }), {
        fetchImpl: fakeFetch([], calls),
      }),
      /config|https/i,
    );
  } finally {
    process.stdout.write = stdoutWrite;
    process.stderr.write = stderrWrite;
  }
  assert.equal(calls.length, 0);
  assert.equal(stdout, "");
  assert.equal(stderr, "");
  assert.doesNotMatch(JSON.stringify({ result: null, stdout, stderr }), new RegExp(SECRET));
});
