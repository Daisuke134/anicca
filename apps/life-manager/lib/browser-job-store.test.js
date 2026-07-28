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
  const query = async (sql, params) => {
    calls.push({ sql, params });
    if (/INSERT INTO public\.lm_browser_jobs/i.test(sql)) return { rows: [] };
    return { rows: [existing] };
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
  }, { query });

  assert.deepEqual(result, { created: false, job: existing });
  assert.equal(calls.length, 2);
  assert.match(calls[0].sql, /ON CONFLICT \(uid, telegram_chat_id, telegram_message_id\) DO NOTHING/i);
  assert.equal(calls[0].params[0], "u-1");
  assert.match(calls[1].sql, /WHERE uid = \$1 AND telegram_chat_id = \$2 AND telegram_message_id = \$3/i);
});

test("claim uses the concurrency-safe RPC with a lease long enough for cloud discovery plus CUA", async () => {
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
  const query = async (sql, params) => {
    seen.push({ sql, params });
    return { rows: [row] };
  };
  assert.deepEqual(await claimBrowserJob({ query }), row);
  assert.match(seen[0].sql, /claim_lm_browser_job\(\$1\)/i);
  assert.deepEqual(seen[0].params, [480]);
});

test("trace append and terminal finish go through narrow RPCs", async () => {
  const calls = [];
  const query = async (sql, params) => {
    calls.push({ sql, params });
    return { rows: [{ ok: true }] };
  };
  await appendBrowserTrace("job-1", "selected", { origin: "https://example.com" }, { query });
  await finishBrowserJob("job-1", {
    status: "completed",
    selected_url: "https://example.com/event",
    provider_receipt: { confirmed: true, status: "registered", confirmation_id: "r1" },
    telegram_message_id: "99",
    evidence_message_id: "100",
    evidence_sha256: "a".repeat(64),
  }, { query });

  assert.match(calls[0].sql, /append_lm_browser_job_trace\(\$1, \$2, \$3::jsonb\)/i);
  assert.equal(calls[0].params[1], "selected");
  assert.match(calls[1].sql, /finish_lm_browser_job\(\$1, \$2, \$3::jsonb, \$4\)/i);
  assert.equal(calls[1].params[1], "completed");
  assert.equal(calls[1].params[3], 99);
  assert.match(calls[1].params[2], /evidence_sha256/);
});
