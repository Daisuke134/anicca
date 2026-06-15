// notify-handler.test.js — integration tests for life-notify Netlify handler.
//
// Covers:
//   1. 405 for non-POST
//   2. 500 when env vars missing
//   3. Scan mode: returns 200 with scanned/lateRisks/alerted when no late risks
//   4. Scan mode: detects a late-risk event, saves draft, sends approval email
//   5. Webhook mode: missing fields → 400
//   6. Webhook mode: reply NOT approved → {ok, approved: false, sent: 0}
//   7. Webhook mode: reply "OK" → fetches draft → sends to attendees
//   8. Webhook mode: bad JSON → 400
//   9. GCal auth failure → 500
//  10. GCal list error → 502
//
// Pattern mirrors travel-handler.test.js (proven template).
// node --test netlify/functions/_lib/__tests__/notify-handler.test.js

const { test, beforeEach, afterEach } = require("node:test");
const assert = require("node:assert");
const path = require("path");

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeGcalEvent(id, summary, dateTimeIso, attendees = []) {
  return {
    id,
    summary,
    start: { dateTime: dateTimeIso },
    end: { dateTime: new Date(new Date(dateTimeIso).getTime() + 3_600_000).toISOString() },
    attendees,
  };
}

function gcalListResponse(events) {
  return JSON.stringify({ items: events });
}

function agentMailDraftResponse(id) {
  return JSON.stringify({ id, to: "attendee@example.com", subject: "Late notice", body: "Running late." });
}

function agentMailSendResponse() {
  return JSON.stringify({ id: `msg-${Date.now()}` });
}

// ── Per-test env + fetch isolation ───────────────────────────────────────────

let originalFetch;
let originalEnv;

beforeEach(() => {
  originalFetch = global.fetch;
  originalEnv = { ...process.env };

  // Set required env vars
  process.env.AGENTMAIL_INBOX_ID     = "inbox-test-123";
  process.env.AGENTMAIL_API_KEY      = "agentmail-key-test";
  process.env.OWNER_EMAIL            = "owner@example.com";
  process.env.GCAL_ID                = "primary";
  process.env.GOOGLE_CALENDAR_TOKEN  = "gcal-token-test";
});

afterEach(() => {
  global.fetch = originalFetch;
  // Restore env
  for (const key of Object.keys(process.env)) {
    if (!(key in originalEnv)) delete process.env[key];
  }
  Object.assign(process.env, originalEnv);

  // Bust module cache so handler re-reads env per test
  const handlerPath = path.resolve(
    __dirname, "../../life-notify.js"
  );
  delete require.cache[require.resolve(handlerPath)];

  const gcalTokenPath = path.resolve(__dirname, "../gcal-token.js");
  delete require.cache[require.resolve(gcalTokenPath)];
});

function makeEvent(httpMethod, body = null, headers = {}) {
  return {
    httpMethod,
    body: body !== null ? JSON.stringify(body) : null,
    headers,
  };
}

function requireHandler() {
  return require(path.resolve(__dirname, "../../life-notify.js"));
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test("405 for GET", async () => {
  const { handler } = requireHandler();
  const r = await handler({ httpMethod: "GET", body: null, headers: {} });
  assert.strictEqual(r.statusCode, 405);
});

test("500 when AGENTMAIL_INBOX_ID missing", async () => {
  delete process.env.AGENTMAIL_INBOX_ID;
  const { handler } = requireHandler();
  const r = await handler({ httpMethod: "POST", body: null, headers: {} });
  assert.strictEqual(r.statusCode, 500);
  assert.ok(r.body.includes("missing_env"));
});

test("500 when OWNER_EMAIL missing", async () => {
  delete process.env.OWNER_EMAIL;
  const { handler } = requireHandler();
  const r = await handler({ httpMethod: "POST", body: null, headers: {} });
  assert.strictEqual(r.statusCode, 500);
});

test("500 when GCal auth fails", async () => {
  delete process.env.GOOGLE_CALENDAR_TOKEN;
  delete process.env.GOOGLE_REFRESH_TOKEN;

  const { handler } = requireHandler();
  const r = await handler({ httpMethod: "POST", body: null, headers: {} });
  assert.strictEqual(r.statusCode, 500);
  assert.ok(r.body.includes("auth_error"));
});

test("502 when GCal list returns error", async () => {
  global.fetch = async (url) => {
    if (url.includes("googleapis.com/calendar")) {
      return { ok: false, status: 503, text: async () => "Service Unavailable" };
    }
    throw new Error(`Unexpected fetch: ${url}`);
  };

  const { handler } = requireHandler();
  const r = await handler({ httpMethod: "POST", body: null, headers: {} });
  assert.strictEqual(r.statusCode, 502);
  assert.ok(r.body.includes("gcal_list_error"));
});

test("scan mode: 200 with zero late risks when no events", async () => {
  global.fetch = async (url) => {
    if (url.includes("googleapis.com/calendar")) {
      return { ok: true, json: async () => ({ items: [] }) };
    }
    throw new Error(`Unexpected fetch: ${url}`);
  };

  const { handler } = requireHandler();
  const r = await handler({ httpMethod: "POST", body: null, headers: {} });
  assert.strictEqual(r.statusCode, 200);
  const body = JSON.parse(r.body);
  assert.strictEqual(body.ok, true);
  assert.strictEqual(body.scanned, 0);
  assert.strictEqual(body.lateRisks, 0);
});

test("scan mode: detects late-risk, saves draft, sends approval email", async () => {
  const nowMs = Date.now();
  const travelStartIso = new Date(nowMs - 600_000).toISOString(); // 10 min ago
  const eventStartIso  = new Date(nowMs + 600_000).toISOString(); // 10 min from now

  const events = [
    makeGcalEvent("t1", "[Travel] Team Sync", travelStartIso),
    makeGcalEvent("e1", "Team Sync", eventStartIso, [{ email: "boss@example.com" }]),
  ];

  const fetchCalls = [];
  global.fetch = async (url, opts) => {
    fetchCalls.push({ url, method: opts?.method });

    if (url.includes("googleapis.com/calendar")) {
      return { ok: true, json: async () => ({ items: events }) };
    }
    if (url.includes("agentmail.to") && url.includes("/drafts") && opts?.method === "POST") {
      return { ok: true, json: async () => ({ id: "draft-abc", to: "boss@example.com" }) };
    }
    if (url.includes("agentmail.to") && url.includes("/messages") && opts?.method === "POST") {
      return { ok: true, json: async () => ({ id: "msg-xyz" }) };
    }
    throw new Error(`Unexpected fetch: ${url}`);
  };

  const { handler } = requireHandler();
  const r = await handler({ httpMethod: "POST", body: null, headers: {} });
  assert.strictEqual(r.statusCode, 200);

  const body = JSON.parse(r.body);
  assert.strictEqual(body.ok, true);
  assert.strictEqual(body.lateRisks, 1);
  assert.ok(body.alerted.length >= 1);

  // Verify draft was saved to AgentMail
  const draftCall = fetchCalls.find((c) => c.url.includes("/drafts") && c.method === "POST");
  assert.ok(draftCall, "should have POSTed to AgentMail drafts");

  // Verify approval email was sent
  const msgCall = fetchCalls.find((c) => c.url.includes("/messages") && c.method === "POST");
  assert.ok(msgCall, "should have sent approval email via AgentMail");
});

test("scan mode: no alert when travel block has not started yet", async () => {
  const nowMs = Date.now();
  const travelStartIso = new Date(nowMs + 900_000).toISOString(); // 15 min from now
  const eventStartIso  = new Date(nowMs + 1_800_000).toISOString();

  const events = [
    makeGcalEvent("t2", "[Travel] Lunch", travelStartIso),
    makeGcalEvent("e2", "Lunch", eventStartIso, []),
  ];

  const fetchCalls = [];
  global.fetch = async (url, opts) => {
    fetchCalls.push({ url });
    if (url.includes("googleapis.com/calendar")) {
      return { ok: true, json: async () => ({ items: events }) };
    }
    throw new Error(`Unexpected fetch: ${url}`);
  };

  const { handler } = requireHandler();
  const r = await handler({ httpMethod: "POST", body: null, headers: {} });
  assert.strictEqual(r.statusCode, 200);
  const body = JSON.parse(r.body);
  assert.strictEqual(body.lateRisks, 0);
  assert.strictEqual(body.alerted.length, 0);

  // No AgentMail calls expected
  const agentCalls = fetchCalls.filter((c) => c.url.includes("agentmail.to"));
  assert.strictEqual(agentCalls.length, 0);
});

// ── Webhook mode tests ────────────────────────────────────────────────────────

test("webhook mode: bad JSON → 400", async () => {
  const { handler } = requireHandler();
  const r = await handler({
    httpMethod: "POST",
    body: "not-json",
    headers: { "x-anicca-event": "message.received" },
  });
  assert.strictEqual(r.statusCode, 400);
  assert.ok(r.body.includes("bad_json"));
});

test("webhook mode: missing draftId → 400", async () => {
  const { handler } = requireHandler();
  const r = await handler({
    httpMethod: "POST",
    body: JSON.stringify({ replyBody: "OK" }),
    headers: { "x-anicca-event": "message.received" },
  });
  assert.strictEqual(r.statusCode, 400);
  assert.ok(r.body.includes("missing_fields"));
});

test("webhook mode: reply not approved → {ok, approved: false, sent: 0}", async () => {
  const { handler } = requireHandler();
  const r = await handler({
    httpMethod: "POST",
    body: JSON.stringify({ draftId: "draft-111", replyBody: "no thanks" }),
    headers: { "x-anicca-event": "message.received" },
  });
  assert.strictEqual(r.statusCode, 200);
  const body = JSON.parse(r.body);
  assert.strictEqual(body.approved, false);
  assert.strictEqual(body.sent, 0);
});

test("webhook mode: reply OK → fetches draft, sends to attendees", async () => {
  const fetchCalls = [];
  global.fetch = async (url, opts) => {
    fetchCalls.push({ url, method: opts?.method });
    if (url.includes("/drafts/draft-222")) {
      return {
        ok: true,
        json: async () => ({
          id: "draft-222",
          to: "attendee@example.com",
          subject: "Late notice for Team Sync",
          body: "I'll be 10 minutes late.",
        }),
      };
    }
    if (url.includes("/messages") && opts?.method === "POST") {
      return { ok: true, json: async () => ({ id: "msg-sent-1" }) };
    }
    throw new Error(`Unexpected fetch: ${url}`);
  };

  const { handler } = requireHandler();
  const r = await handler({
    httpMethod: "POST",
    body: JSON.stringify({ draftId: "draft-222", replyBody: "OK" }),
    headers: { "x-anicca-event": "message.received" },
  });
  assert.strictEqual(r.statusCode, 200);
  const body = JSON.parse(r.body);
  assert.strictEqual(body.approved, true);
  assert.strictEqual(body.sent, 1);

  // Verify draft was fetched
  const draftGet = fetchCalls.find((c) => c.url.includes("/drafts/draft-222") && !c.method);
  assert.ok(draftGet, "should have GETted the draft");

  // Verify message was sent
  const msgSend = fetchCalls.find((c) => c.url.includes("/messages") && c.method === "POST");
  assert.ok(msgSend, "should have POSTed the message");
});
