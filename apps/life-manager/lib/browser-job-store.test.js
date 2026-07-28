"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  buildBrowserJob,
  enqueueBrowserJob,
  claimBrowserJob,
  appendBrowserTrace,
  finishBrowserJob,
} = require("./browser-job-store.js");

const SUPA = Object.freeze({
  supaUrl: "https://db.example",
  supaKey: "service-key",
});

function response(status, body) {
  return {
    status,
    ok: status >= 200 && status < 300,
    async json() { return body; },
    async text() { return JSON.stringify(body); },
  };
}

test("a queued job is tenant-bound and hashes the raw prompt without persisting its secret", () => {
  const raw = "Register me. password=super-secret-token";
  const job = buildBrowserJob({
    uid: "u-1",
    chatId: "42",
    messageId: "91",
    updateId: "7001",
    rawPrompt: raw,
    classification: {
      goal: "Register the user for a free public event",
      actionKind: "registration",
      locale: "en",
      requiresLogin: false,
    },
  });
  assert.equal(job.uid, "u-1");
  assert.equal(job.telegram_chat_id, "42");
  assert.equal(job.telegram_message_id, "91");
  assert.match(job.prompt_hash, /^[a-f0-9]{64}$/);
  assert.doesNotMatch(JSON.stringify(job), /super-secret-token/);
  assert.equal(job.status, "queued");
});

test("enqueue is idempotent on tenant and Telegram message and returns the existing job", async () => {
  const calls = [];
  const existing = {
    id: "job-existing",
    uid: "u-1",
    telegram_chat_id: "42",
    telegram_message_id: "91",
    status: "queued",
  };
  const fetchImpl = async (url, init = {}) => {
    calls.push({ url: String(url), init });
    if (init.method === "POST") return response(201, []);
    return response(200, [existing]);
  };
  const result = await enqueueBrowserJob({
    uid: "u-1",
    chatId: "42",
    messageId: "91",
    updateId: "7001",
    rawPrompt: "Please register me",
    classification: {
      goal: "Register the user for a free public event",
      actionKind: "registration",
      locale: "en",
      requiresLogin: false,
    },
  }, { ...SUPA, fetchImpl });

  assert.deepEqual(result, { created: false, job: existing });
  assert.equal(calls.length, 2);
  assert.match(calls[0].url, /\/rest\/v1\/lm_browser_jobs$/);
  assert.equal(calls[0].init.headers.Prefer, "resolution=ignore-duplicates,return=representation");
  assert.match(calls[1].url, /uid=eq\.u-1/);
  assert.match(calls[1].url, /telegram_message_id=eq\.91/);
});

test("claim uses the concurrency-safe RPC and returns only one bounded job row", async () => {
  const seen = [];
  const row = {
    id: "job-1",
    uid: "u-1",
    telegram_chat_id: "42",
    goal: "register",
    locale: "en",
    action_kind: "registration",
    requires_login: false,
  };
  const fetchImpl = async (url, init) => {
    seen.push({ url: String(url), init });
    return response(200, [row]);
  };
  assert.deepEqual(await claimBrowserJob({ ...SUPA, fetchImpl, leaseSeconds: 180 }), row);
  assert.match(seen[0].url, /\/rest\/v1\/rpc\/claim_lm_browser_job$/);
  assert.deepEqual(JSON.parse(seen[0].init.body), { p_lease_seconds: 180 });
});

test("trace append and terminal finish go through narrow RPCs", async () => {
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url: String(url), body: JSON.parse(init.body) });
    return response(200, [{ ok: true }]);
  };
  await appendBrowserTrace("job-1", "selected", { origin: "https://example.com" }, { ...SUPA, fetchImpl });
  await finishBrowserJob("job-1", {
    status: "completed",
    selected_url: "https://example.com/event",
    provider_receipt: { confirmed: true, status: "registered", confirmation_id: "r1" },
    telegram_message_id: "99",
  }, { ...SUPA, fetchImpl });

  assert.match(calls[0].url, /append_lm_browser_job_trace$/);
  assert.equal(calls[0].body.p_stage, "selected");
  assert.match(calls[1].url, /finish_lm_browser_job$/);
  assert.equal(calls[1].body.p_status, "completed");
  assert.equal(calls[1].body.p_telegram_message_id, 99);
});

